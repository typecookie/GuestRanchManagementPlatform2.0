from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from apps.employees.models import Employee, PositionHistory, Interview, StaffSchedule, Department, Position, SeasonPositionTarget
from apps.employees.forms import InterviewForm, EmployeeForm, StaffScheduleForm, DepartmentForm, PositionForm, SeasonPositionTargetForm
from apps.employees.utils import (
    ensure_default_departments_and_positions,
    sync_season_targets_from_schedule,
    auto_fill_schedule_from_season_targets,
    get_unique_positions
)
from apps.reservations.models import OperatingSeason

User = get_user_model()


class EmployeeInterviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="adminuser",
            password="password123",
            email="admin@example.com"
        )
        self.client = Client()
        self.client.force_login(self.user)

        # Create an existing employee
        self.employee = Employee.objects.create(
            first_name="John",
            last_name="Wrangler",
            current_position="Lead Wrangler",
            status=Employee.Status.ACTIVE
        )

        # Create an interview attached to the employee
        self.emp_interview = Interview.objects.create(
            employee=self.employee,
            date=date(2026, 8, 10),
            status=Interview.Status.PROMOTION_RECOMMENDED,
            notes="Ready for senior wrangler duties."
        )

        # Create an interview for a candidate not yet hired
        self.candidate_interview = Interview.objects.create(
            candidate_name="Sarah Connor",
            candidate_email="sarah@example.com",
            candidate_phone="555-0199",
            date=date(2026, 8, 15),
            status=Interview.Status.JOB_OFFERED,
            offered_position="Trail Guide",
            notes="Great experience with horses and trail guiding."
        )

    def test_model_properties_and_str(self):
        # Candidate interview
        self.assertIsNone(self.candidate_interview.employee)
        self.assertEqual(self.candidate_interview.interviewee_name, "Sarah Connor")
        self.assertIn("Sarah Connor", str(self.candidate_interview))
        self.assertIn("Job Offered", str(self.candidate_interview))

        # Employee interview
        self.assertEqual(self.emp_interview.interviewee_name, "John Wrangler")
        self.assertIn("John Wrangler", str(self.emp_interview))
        self.assertIn("Recommended for Promotion", str(self.emp_interview))

    def test_interview_form_validation(self):
        # 1. Valid with candidate name
        form1 = InterviewForm(data={
            'candidate_name': 'Alex Smith',
            'candidate_email': 'alex@example.com',
            'date': '2026-08-20',
            'status': 'follow_up',
            'follow_up_reason': 'Check references',
        })
        self.assertTrue(form1.is_valid(), form1.errors)

        # 2. Valid with employee
        form2 = InterviewForm(data={
            'employee': self.employee.pk,
            'date': '2026-08-21',
            'status': 'promotion_recommended',
        })
        self.assertTrue(form2.is_valid(), form2.errors)

        # 3. Invalid when neither employee nor candidate_name is provided
        form3 = InterviewForm(data={
            'date': '2026-08-22',
            'status': 'not_recommended',
        })
        self.assertFalse(form3.is_valid())
        self.assertIn("Please select an existing employee or enter a candidate name.", str(form3.errors))

    def test_interview_list_view(self):
        url = reverse('employees:interview_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sarah Connor")
        self.assertContains(resp, "John Wrangler")
        self.assertContains(resp, "Candidate")
        self.assertContains(resp, "Employee")

        # Filter by candidate type
        resp_cand = self.client.get(url, {'type': 'candidate'})
        self.assertEqual(resp_cand.status_code, 200)
        self.assertContains(resp_cand, "Sarah Connor")
        self.assertNotContains(resp_cand, "John Wrangler")

        # Filter by employee type
        resp_emp = self.client.get(url, {'type': 'employee'})
        self.assertEqual(resp_emp.status_code, 200)
        self.assertNotContains(resp_emp, "Sarah Connor")
        self.assertContains(resp_emp, "John Wrangler")

        # Filter by status
        resp_stat = self.client.get(url, {'status': 'job_offered'})
        self.assertContains(resp_stat, "Sarah Connor")
        self.assertNotContains(resp_stat, "John Wrangler")

        # Search query
        resp_search = self.client.get(url, {'q': 'Trail Guide'})
        self.assertContains(resp_search, "Sarah Connor")
        self.assertNotContains(resp_search, "John Wrangler")

    def test_create_candidate_interview(self):
        url = reverse('employees:interview_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        post_data = {
            'candidate_name': 'Mark Taylor',
            'candidate_email': 'mark@example.com',
            'candidate_phone': '555-8888',
            'date': '2026-08-25',
            'status': 'job_offered',
            'offered_position': 'Wrangler',
            'notes': 'Experienced rider.',
        }
        resp = self.client.post(url, data=post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('employees:interview_list'))

        interview = Interview.objects.get(candidate_name='Mark Taylor')
        self.assertIsNone(interview.employee)
        self.assertEqual(interview.offered_position, 'Wrangler')
        self.assertEqual(interview.candidate_email, 'mark@example.com')

    def test_create_employee_interview(self):
        url = reverse('employees:interview_create')
        post_data = {
            'employee': self.employee.pk,
            'date': '2026-08-26',
            'status': 'promotion_recommended',
            'notes': 'Ready for head wrangler.',
        }
        resp = self.client.post(url, data=post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('employees:employee_detail', kwargs={'pk': self.employee.pk}))

        interview = Interview.objects.filter(employee=self.employee, notes='Ready for head wrangler.').first()
        self.assertIsNotNone(interview)

    def test_hire_candidate_view(self):
        interview = self.candidate_interview
        url = reverse('employees:hire_candidate', kwargs={'pk': interview.pk})

        # GET request loads candidate data into form
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Hire Candidate: Sarah Connor")
        self.assertContains(resp, "Trail Guide")

        # POST request creates employee, links interview, creates position history
        post_data = {
            'first_name': 'Sarah',
            'last_name': 'Connor',
            'current_position': 'Trail Guide',
            'status': 'active',
            'performance_notes': 'Hired from candidate interview.',
        }
        resp = self.client.post(url, data=post_data)
        self.assertEqual(resp.status_code, 302)

        # Check that employee is created
        employee = Employee.objects.get(first_name='Sarah', last_name='Connor')
        self.assertEqual(employee.current_position, 'Trail Guide')
        self.assertEqual(employee.status, 'active')
        self.assertEqual(resp.url, reverse('employees:employee_detail', kwargs={'pk': employee.pk}))

        # Check interview is now attached to the employee
        interview.refresh_from_db()
        self.assertEqual(interview.employee, employee)

        # Check position history created
        history = PositionHistory.objects.filter(employee=employee, position='Trail Guide').first()
        self.assertIsNotNone(history)
        self.assertEqual(history.start_date, interview.date)

        # Visiting hire_candidate on already hired candidate redirects to employee profile
        resp_again = self.client.get(url)
        self.assertEqual(resp_again.status_code, 302)
        self.assertEqual(resp_again.url, reverse('employees:employee_detail', kwargs={'pk': employee.pk}))

    def test_interview_update(self):
        url = reverse('employees:interview_update', kwargs={'pk': self.candidate_interview.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Update notes and status
        resp = self.client.post(url, data={
            'candidate_name': 'Sarah Connor',
            'candidate_email': 'sarah_new@example.com',
            'date': '2026-08-15',
            'status': 'not_recommended',
            'notes': 'Decided to decline.',
        })
        self.assertEqual(resp.status_code, 302)

        self.candidate_interview.refresh_from_db()
        self.assertEqual(self.candidate_interview.status, 'not_recommended')
        self.assertEqual(self.candidate_interview.candidate_email, 'sarah_new@example.com')
        self.assertEqual(self.candidate_interview.notes, 'Decided to decline.')

    def test_delete_candidate_interview(self):
        interview_pk = self.candidate_interview.pk
        url = reverse('employees:interview_delete', kwargs={'pk': interview_pk})

        # GET request renders confirmation page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Confirm Interview Deletion")
        self.assertContains(resp, "Sarah Connor")

        # POST request deletes interview and redirects to interview list
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('employees:interview_list'))

        self.assertFalse(Interview.objects.filter(pk=interview_pk).exists())

    def test_delete_employee_interview(self):
        interview_pk = self.emp_interview.pk
        employee_pk = self.employee.pk
        url = reverse('employees:interview_delete', kwargs={'pk': interview_pk})

        # GET request renders confirmation page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Confirm Interview Deletion")
        self.assertContains(resp, "John Wrangler")

        # POST request deletes interview and redirects to employee detail
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('employees:employee_detail', kwargs={'pk': employee_pk}))

        self.assertFalse(Interview.objects.filter(pk=interview_pk).exists())
        self.assertTrue(Employee.objects.filter(pk=employee_pk).exists())

    def test_delete_interview_permissions(self):
        # Create unprivileged user
        regular_user = User.objects.create_user(
            username="regularuser",
            password="password123",
            email="regular@example.com"
        )
        unauth_client = Client()
        unauth_client.force_login(regular_user)

        url = reverse('employees:interview_delete', kwargs={'pk': self.candidate_interview.pk})

        # Regular user without delete permission gets 403 Forbidden
        resp = unauth_client.get(url)
        self.assertEqual(resp.status_code, 403)

        resp = unauth_client.post(url)
        self.assertEqual(resp.status_code, 403)

        # Anonymous user gets redirected to login
        anon_client = Client()
        resp_anon = anon_client.get(url)
        self.assertEqual(resp_anon.status_code, 302)
        self.assertIn('/accounts/login/', resp_anon.url)


class StaffScheduleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="ranchmanager",
            password="password123",
            email="manager@example.com"
        )
        self.client = Client()
        self.client.force_login(self.admin)

        # Create Operating Season: June 1, 2026 to September 30, 2026
        self.season = OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True
        )

        # Create Employees
        self.emp_wrangler = Employee.objects.create(
            first_name="Jake",
            last_name="Dunne",
            current_position="Lead Wrangler",
            status=Employee.Status.ACTIVE
        )
        self.emp_chef = Employee.objects.create(
            first_name="Elena",
            last_name="Rostova",
            current_position="Executive Chef",
            status=Employee.Status.ACTIVE
        )

        # Create Confirmed Staff Schedule (starts 1 week before opening, ends with closing)
        self.schedule_confirmed = StaffSchedule.objects.create(
            season=self.season,
            position="Lead Wrangler",
            employee=self.emp_wrangler,
            status=StaffSchedule.Status.CONFIRMED,
            is_placeholder=False,
            start_date=date(2026, 5, 25),
            end_date=date(2026, 9, 30),
            notes="Assigned lead wrangler for the entire season."
        )

        # Create Placeholder Unconfirmed Staff Schedule
        self.schedule_placeholder = StaffSchedule.objects.create(
            season=self.season,
            position="Assistant Cook",
            employee=None,
            placeholder_name="Line Cook Placeholder #1",
            status=StaffSchedule.Status.UNCONFIRMED,
            is_placeholder=True,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 31),
            notes="Pending candidate interview."
        )

    def test_model_properties_and_validation(self):
        self.assertEqual(self.schedule_confirmed.staff_name, "Jake Dunne")
        self.assertFalse(self.schedule_confirmed.is_unconfirmed_entry)
        self.assertEqual(self.schedule_confirmed.duration_days, 129)

        self.assertEqual(self.schedule_placeholder.staff_name, "Line Cook Placeholder #1")
        self.assertTrue(self.schedule_placeholder.is_unconfirmed_entry)
        self.assertEqual(self.schedule_placeholder.duration_days, 78)

        # Validation error when end_date < start_date
        invalid_schedule = StaffSchedule(
            season=self.season,
            position="Test",
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 5)
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            invalid_schedule.clean()

    def test_staffing_schedule_view_timeline_bounds(self):
        url = reverse('employees:staffing_schedule') + f"?season={self.season.pk}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # 2 weeks before opening date (June 1 - 14 days = May 18, 2026)
        expected_start = self.season.start_date - timedelta(days=14)
        self.assertEqual(expected_start, date(2026, 5, 18))
        self.assertEqual(resp.context['timeline_start'], expected_start)

        # 2 weeks after closing date (September 30 + 14 days = October 14, 2026)
        expected_end = self.season.end_date + timedelta(days=14)
        self.assertEqual(expected_end, date(2026, 10, 14))
        self.assertEqual(resp.context['timeline_end'], expected_end)

        # Check total days
        self.assertEqual(resp.context['total_days'], (expected_end - expected_start).days + 1)

        # Check season dates in context
        self.assertEqual(resp.context['season_start'], self.season.start_date)
        self.assertEqual(resp.context['season_end'], self.season.end_date)

        # Verify page contents
        self.assertContains(resp, "Jake Dunne")
        self.assertContains(resp, "Lead Wrangler")
        self.assertContains(resp, "Confirmed Employee")
        self.assertContains(resp, "Line Cook Placeholder #1")
        self.assertContains(resp, "Placeholder / Unconfirmed")

    def test_staffing_schedule_filters(self):
        url = reverse('employees:staffing_schedule')

        # Filter by position
        resp = self.client.get(url, {'season': self.season.pk, 'position': 'Lead Wrangler'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['schedule_rows']), 1)
        self.assertEqual(resp.context['schedule_rows'][0]['staff_name'], 'Jake Dunne')

        # Filter by status: confirmed
        resp = self.client.get(url, {'season': self.season.pk, 'status': 'confirmed'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['schedule_rows']), 1)
        self.assertEqual(resp.context['schedule_rows'][0]['staff_name'], 'Jake Dunne')

        # Filter by status: placeholder
        resp = self.client.get(url, {'season': self.season.pk, 'status': 'placeholder'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['schedule_rows']), 1)
        self.assertEqual(resp.context['schedule_rows'][0]['staff_name'], 'Line Cook Placeholder #1')

        # Search query
        resp = self.client.get(url, {'season': self.season.pk, 'q': 'Dunne'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['schedule_rows']), 1)
        self.assertEqual(resp.context['schedule_rows'][0]['staff_name'], 'Jake Dunne')

    def test_staff_schedule_create_confirmed(self):
        url = reverse('employees:staff_schedule_create')
        data = {
            'season': self.season.pk,
            'position': 'Executive Chef',
            'employee': self.emp_chef.pk,
            'placeholder_name': '',
            'is_placeholder': False,
            'status': 'confirmed',
            'start_date': '2026-05-18',
            'end_date': '2026-10-14',
            'notes': 'Head chef full span.'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        
        created = StaffSchedule.objects.filter(employee=self.emp_chef).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.position, 'Executive Chef')
        self.assertEqual(created.start_date, date(2026, 5, 18))
        self.assertEqual(created.end_date, date(2026, 10, 14))
        self.assertFalse(created.is_placeholder)

    def test_staff_schedule_create_placeholder(self):
        url = reverse('employees:staff_schedule_create')
        data = {
            'season': self.season.pk,
            'position': 'Housekeeper',
            'employee': '',
            'placeholder_name': 'Candidate Mary',
            'is_placeholder': True,
            'status': 'unconfirmed',
            'start_date': '2026-06-01',
            'end_date': '2026-09-01',
            'notes': 'Interview pending.'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)

        created = StaffSchedule.objects.filter(placeholder_name='Candidate Mary').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.position, 'Housekeeper')
        self.assertIsNone(created.employee)
        self.assertTrue(created.is_placeholder)

    def test_staff_schedule_unmark_placeholder_on_save(self):
        # Update existing placeholder schedule to unmark placeholder checkbox
        url = reverse('employees:staff_schedule_update', kwargs={'pk': self.schedule_placeholder.pk})
        data = {
            'season': self.season.pk,
            'position': 'Assistant Cook',
            'employee': '',
            'placeholder_name': 'Confirmed Non-profile Cook',
            'status': 'confirmed',
            'start_date': '2026-06-15',
            'end_date': '2026-08-31',
            'notes': 'Candidate confirmed but profile not created yet.'
            # Note: is_placeholder is omitted/unchecked
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)

        self.schedule_placeholder.refresh_from_db()
        self.assertFalse(self.schedule_placeholder.is_placeholder)
        self.assertEqual(self.schedule_placeholder.status, 'confirmed')
        self.assertEqual(self.schedule_placeholder.staff_name, 'Confirmed Non-profile Cook')
        self.assertFalse(self.schedule_placeholder.is_unconfirmed_entry)

    def test_staff_schedule_create_unmarked_placeholder(self):
        url = reverse('employees:staff_schedule_create')
        data = {
            'season': self.season.pk,
            'position': 'Dishwasher',
            'employee': '',
            'placeholder_name': 'Sam Smith',
            'status': 'confirmed',
            'start_date': '2026-06-01',
            'end_date': '2026-09-01',
            'notes': 'Confirmed seasonal worker.'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)

        created = StaffSchedule.objects.filter(placeholder_name='Sam Smith').first()
        self.assertIsNotNone(created)
        self.assertFalse(created.is_placeholder)
        self.assertEqual(created.status, 'confirmed')
        self.assertFalse(created.is_unconfirmed_entry)

        # Verify staffing schedule view renders properly without NoReverseMatch error
        view_url = reverse('employees:staffing_schedule')
        resp = self.client.get(view_url, {'season': self.season.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sam Smith")
        self.assertContains(resp, "Confirmed Staff")
        self.assertContains(resp, "Jake Dunne")

    def test_staff_schedule_link_employee(self):
        placeholder_pk = self.schedule_placeholder.pk
        url = reverse('employees:staff_schedule_link_employee', kwargs={'pk': placeholder_pk})

        # GET form
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Line Cook Placeholder #1")

        # POST link to employee
        resp = self.client.post(url, {
            'employee': self.emp_chef.pk,
            'status': 'confirmed',
            'notes': 'Hired and confirmed on schedule.'
        })
        self.assertEqual(resp.status_code, 302)

        self.schedule_placeholder.refresh_from_db()
        self.assertEqual(self.schedule_placeholder.employee, self.emp_chef)
        self.assertFalse(self.schedule_placeholder.is_placeholder)
        self.assertEqual(self.schedule_placeholder.status, 'confirmed')
        self.assertEqual(self.schedule_placeholder.staff_name, 'Elena Rostova')

    def test_staff_schedule_delete(self):
        schedule_pk = self.schedule_placeholder.pk
        url = reverse('employees:staff_schedule_delete', kwargs={'pk': schedule_pk})

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Confirm Staff Assignment Deletion")

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(StaffSchedule.objects.filter(pk=schedule_pk).exists())

    def test_staff_schedule_tentative_assignment(self):
        # Create tentative schedule linked to an employee
        tentative_emp = StaffSchedule.objects.create(
            season=self.season,
            position='Head Wrangler',
            employee=self.emp_wrangler,
            status=StaffSchedule.Status.TENTATIVE,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 1),
            notes='Pending summer contract confirmation'
        )
        self.assertTrue(tentative_emp.is_tentative)
        self.assertFalse(tentative_emp.is_confirmed)

        # Create tentative schedule unlinked
        tentative_unlinked = StaffSchedule.objects.create(
            season=self.season,
            position='Trail Guide',
            placeholder_name='Alex Rivers',
            status=StaffSchedule.Status.TENTATIVE,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 15),
        )
        self.assertTrue(tentative_unlinked.is_tentative)

        # Verify page renders tentative styling, legend, and badges
        url = reverse('employees:staffing_schedule')
        resp = self.client.get(url, {'season': self.season.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tentative (2)")
        self.assertContains(resp, "Tentative (Employee)")
        self.assertContains(resp, "Tentative Staff")
        self.assertContains(resp, "⏳ [Tentative]")
        self.assertContains(resp, "linear-gradient(135deg, #8b5cf6, #6d28d9)")

        # Verify filtering by status=tentative
        resp_filtered = self.client.get(url, {'season': self.season.pk, 'status': 'tentative'})
        self.assertEqual(resp_filtered.status_code, 200)
        self.assertEqual(len(resp_filtered.context['schedule_rows']), 2)
        self.assertContains(resp_filtered, "Head Wrangler")
        self.assertContains(resp_filtered, "Alex Rivers")
        self.assertNotContains(resp_filtered, "Line Cook Placeholder #1")
        self.assertNotContains(resp_filtered, "Assigned lead wrangler for the entire season.")

    def test_permissions_enforced(self):
        regular_user = User.objects.create_user(
            username="unprivileged",
            password="password123",
            email="regular@example.com"
        )
        unauth_client = Client()
        unauth_client.force_login(regular_user)

        # Read without permission
        resp = unauth_client.get(reverse('employees:staffing_schedule'))
        self.assertEqual(resp.status_code, 403)

        # Write without permission
        resp = unauth_client.get(reverse('employees:staff_schedule_create'))
        self.assertEqual(resp.status_code, 403)

        # Delete without permission
        resp = unauth_client.post(reverse('employees:staff_schedule_delete', kwargs={'pk': self.schedule_confirmed.pk}))
        self.assertEqual(resp.status_code, 403)


class DepartmentPositionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="adminuser",
            password="password123",
            email="admin@example.com"
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.season = OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True
        )

    def test_default_departments_and_positions_seeded(self):
        ensure_default_departments_and_positions()
        
        # Check standard departments exist
        dept_names = list(Department.objects.values_list('name', flat=True))
        for expected in ['Barn', 'Kitchen', 'Housekeeping', 'Maintenance', 'Fishing', 'Office', 'Bar']:
            self.assertIn(expected, dept_names)

        # Check barn positions
        barn = Department.objects.get(name='Barn')
        barn_positions = list(barn.positions.values_list('title', flat=True))
        for expected_pos in ['Head Wrangler', 'Corral Boss', 'Barn Boss', 'Wrangler', 'Wrangler/Packer']:
            self.assertIn(expected_pos, barn_positions)

        # Check kitchen positions
        kitchen = Department.objects.get(name='Kitchen')
        kitchen_positions = list(kitchen.positions.values_list('title', flat=True))
        for expected_pos in ['Head Chef', 'Sous Chef', 'Breakfast Cook', 'Prep Cook']:
            self.assertIn(expected_pos, kitchen_positions)

        # Check head position flag
        head_wrangler = Position.objects.get(department=barn, title='Head Wrangler')
        self.assertTrue(head_wrangler.is_head)
        self.assertEqual(head_wrangler.default_target_count, 1)

        wrangler = Position.objects.get(department=barn, title='Wrangler')
        self.assertFalse(wrangler.is_head)
        self.assertEqual(wrangler.default_target_count, 10)

    def test_department_crud_views(self):
        # List view
        resp = self.client.get(reverse('employees:department_position_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ranch Departments & Positions")
        self.assertContains(resp, "Barn")
        self.assertContains(resp, "Kitchen")

        # Create custom department
        resp = self.client.post(reverse('employees:department_create'), {
            'name': 'Wrangler Activities',
            'code': 'activities',
            'description': 'Guest entertainment and special rodeo events.',
            'display_order': 80
        })
        self.assertEqual(resp.status_code, 302)
        created_dept = Department.objects.filter(name='Wrangler Activities').first()
        self.assertIsNotNone(created_dept)

        # Update department
        resp = self.client.post(reverse('employees:department_update', kwargs={'pk': created_dept.pk}), {
            'name': 'Special Activities',
            'code': 'activities',
            'description': 'Updated description.',
            'display_order': 85
        })
        self.assertEqual(resp.status_code, 302)
        created_dept.refresh_from_db()
        self.assertEqual(created_dept.name, 'Special Activities')

        # Delete custom department
        resp = self.client.post(reverse('employees:department_delete', kwargs={'pk': created_dept.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Department.objects.filter(pk=created_dept.pk).exists())

    def test_position_crud_views(self):
        ensure_default_departments_and_positions()
        barn = Department.objects.get(name='Barn')

        # Create position
        resp = self.client.post(reverse('employees:position_create'), {
            'department': barn.pk,
            'title': 'Night Corral Guard',
            'is_head': False,
            'default_target_count': 1,
            'display_order': 70,
            'description': 'Overnight watch on main corrals.'
        })
        self.assertEqual(resp.status_code, 302)
        pos = Position.objects.filter(title='Night Corral Guard').first()
        self.assertIsNotNone(pos)
        self.assertEqual(pos.department, barn)

        # Update position
        resp = self.client.post(reverse('employees:position_update', kwargs={'pk': pos.pk}), {
            'department': barn.pk,
            'title': 'Lead Night Corral Guard',
            'is_head': True,
            'default_target_count': 2,
            'display_order': 75,
            'description': 'Updated overnight watch lead.'
        })
        self.assertEqual(resp.status_code, 302)
        pos.refresh_from_db()
        self.assertEqual(pos.title, 'Lead Night Corral Guard')
        self.assertTrue(pos.is_head)
        self.assertEqual(pos.default_target_count, 2)

        # Delete position
        resp = self.client.post(reverse('employees:position_delete', kwargs={'pk': pos.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Position.objects.filter(pk=pos.pk).exists())

    def test_season_staffing_plan_sync_and_auto_fill(self):
        ensure_default_departments_and_positions()

        # Create some existing schedules for season
        StaffSchedule.objects.create(
            season=self.season,
            position='Head Wrangler',
            placeholder_name='Placeholder Head Wrangler',
            is_placeholder=True,
            status=StaffSchedule.Status.UNCONFIRMED,
            start_date=self.season.start_date,
            end_date=self.season.end_date
        )
        StaffSchedule.objects.create(
            season=self.season,
            position='Wrangler',
            placeholder_name='Mary Stanton',
            is_placeholder=False,
            status=StaffSchedule.Status.CONFIRMED,
            start_date=self.season.start_date,
            end_date=self.season.end_date
        )

        # Sync targets from schedule
        sync_season_targets_from_schedule(self.season)
        targets = SeasonPositionTarget.objects.filter(season=self.season)
        self.assertTrue(targets.exists())

        # Render season staffing plan view
        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Staffing Plan & Headcounts: Summer 2026")
        self.assertContains(resp, "Head Wrangler")
        self.assertContains(resp, "Wrangler")
        self.assertContains(resp, "Barn Boss")

        # Auto-fill missing schedule slots via view POST
        resp = self.client.post(url, {'action': 'auto_fill'})
        self.assertEqual(resp.status_code, 302)

        # Verify new placeholder schedules were generated
        schedules_count = StaffSchedule.objects.filter(season=self.season).count()
        # Head Wrangler: 1 (existing), Wrangler: 10 (1 existing + 9 new), plus default counts for all other positions
        self.assertGreater(schedules_count, 15)

        # Verify Wrangler has 10 schedules total
        wrangler_schedules = StaffSchedule.objects.filter(season=self.season, position='Wrangler')
        self.assertEqual(wrangler_schedules.count(), 10)

    def test_season_staffing_plan_headcount_breakdown_and_placeholder_not_target_met(self):
        ensure_default_departments_and_positions()
        sync_season_targets_from_schedule(self.season)

        employee = Employee.objects.create(
            first_name='John',
            last_name='Wrangler',
            current_position='Wrangler'
        )

        # Target for Wrangler is 10.
        # Add 1 Confirmed employee, 1 Tentative staff, and 2 placeholders.
        wrangler_target = SeasonPositionTarget.objects.get(season=self.season, position__title='Wrangler')
        wrangler_target.target_count = 10
        wrangler_target.save()

        # 1 Confirmed
        StaffSchedule.objects.create(
            season=self.season,
            position='Wrangler',
            employee=employee,
            is_placeholder=False,
            status=StaffSchedule.Status.CONFIRMED,
            start_date=self.season.start_date,
            end_date=self.season.end_date
        )
        # 1 Tentative
        StaffSchedule.objects.create(
            season=self.season,
            position='Wrangler',
            placeholder_name='Tentative Wrangler Candidate',
            is_placeholder=False,
            status=StaffSchedule.Status.TENTATIVE,
            start_date=self.season.start_date,
            end_date=self.season.end_date
        )
        # 2 Placeholders (total scheduled = 4, target = 10)
        for i in range(2):
            StaffSchedule.objects.create(
                season=self.season,
                position='Wrangler',
                placeholder_name=f'Placeholder Wrangler #{i+1}',
                is_placeholder=True,
                status=StaffSchedule.Status.UNCONFIRMED,
                start_date=self.season.start_date,
                end_date=self.season.end_date
            )

        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Verify breakdown rendered: 1 Confirmed, 1 Tentative, 2 Placeholders
        self.assertContains(resp, "1 Confirmed")
        self.assertContains(resp, "1 Tentative")
        self.assertContains(resp, "2 Placeholders")
        # Placeholders must NOT mark target met: 1 confirmed out of 10 target means Need 9
        self.assertContains(resp, "Need 9")

        # Now auto-fill remaining slots so total scheduled = 10 (1 confirmed, 1 tentative, 8 placeholders)
        resp_fill = self.client.post(url, {'action': 'auto_fill'})
        self.assertEqual(resp_fill.status_code, 302)

        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 200)
        # Even with 10 slots on the schedule, placeholders are NOT target met!
        # It still requires 9 confirmed employees to fill the target quota
        self.assertContains(resp2, "Need 9")
        self.assertContains(resp2, "8 placeholders pending")

    def test_season_staffing_plan_save_and_add_custom_position(self):
        ensure_default_departments_and_positions()
        sync_season_targets_from_schedule(self.season)

        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        target_wrangler = SeasonPositionTarget.objects.filter(season=self.season, position__title='Wrangler').first()
        self.assertIsNotNone(target_wrangler)

        # Update target count for Wranglers from 10 to 12
        resp = self.client.post(url, {
            'action': 'save_targets',
            f'target_{target_wrangler.pk}': '12',
            'auto_fill_after_save': '1'
        })
        self.assertEqual(resp.status_code, 302)

        target_wrangler.refresh_from_db()
        self.assertEqual(target_wrangler.target_count, 12)

        # Verify 12 Wrangler schedules exist now
        wrangler_schedules = StaffSchedule.objects.filter(season=self.season, position='Wrangler')
        self.assertEqual(wrangler_schedules.count(), 12)

        # Add custom position to season
        barn = Department.objects.get(name='Barn')
        resp = self.client.post(url, {
            'action': 'add_custom_position',
            'department_id': barn.pk,
            'position_title': 'Senior Wrangler / Trail Master',
            'target_count': '2',
            'create_master': '1'
        })
        self.assertEqual(resp.status_code, 302)

        custom_target = SeasonPositionTarget.objects.filter(
            season=self.season,
            position__title='Senior Wrangler / Trail Master'
        ).first()
        self.assertIsNotNone(custom_target)
        self.assertEqual(custom_target.target_count, 2)

    def test_season_staffing_plan_set_target_zero_deletes_placeholders(self):
        ensure_default_departments_and_positions()
        sync_season_targets_from_schedule(self.season)

        # Auto-fill so placeholders exist
        auto_fill_schedule_from_season_targets(self.season)
        self.assertEqual(StaffSchedule.objects.filter(season=self.season, position='Wrangler').count(), 10)

        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        target_wrangler = SeasonPositionTarget.objects.get(season=self.season, position__title='Wrangler')

        # Set target to 0
        resp = self.client.post(url, {
            'action': 'save_targets',
            f'target_{target_wrangler.pk}': '0',
        })
        self.assertEqual(resp.status_code, 302)

        target_wrangler.refresh_from_db()
        self.assertEqual(target_wrangler.target_count, 0)

        # Placeholders for Wrangler must be fully deleted
        wrangler_schedules = StaffSchedule.objects.filter(season=self.season, position='Wrangler')
        self.assertEqual(wrangler_schedules.count(), 0)

    def test_season_staffing_plan_reduce_target_cleans_excess_placeholders(self):
        ensure_default_departments_and_positions()
        sync_season_targets_from_schedule(self.season)

        # Auto-fill so 10 placeholders exist for Wrangler
        auto_fill_schedule_from_season_targets(self.season)
        self.assertEqual(StaffSchedule.objects.filter(season=self.season, position='Wrangler').count(), 10)

        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        target_wrangler = SeasonPositionTarget.objects.get(season=self.season, position__title='Wrangler')

        # Reduce target from 10 to 4
        resp = self.client.post(url, {
            'action': 'save_targets',
            f'target_{target_wrangler.pk}': '4',
        })
        self.assertEqual(resp.status_code, 302)

        target_wrangler.refresh_from_db()
        self.assertEqual(target_wrangler.target_count, 4)

        # Excess 6 placeholders deleted, exactly 4 remain
        wrangler_schedules = StaffSchedule.objects.filter(season=self.season, position='Wrangler')
        self.assertEqual(wrangler_schedules.count(), 4)

    def test_season_staffing_plan_delete_target_action(self):
        ensure_default_departments_and_positions()
        barn = Department.objects.get(name='Barn')
        custom_target = SeasonPositionTarget.objects.create(
            season=self.season,
            department=barn,
            custom_position_title='Summer Trail Guide',
            target_count=2
        )
        auto_fill_schedule_from_season_targets(self.season)
        self.assertEqual(StaffSchedule.objects.filter(season=self.season, position='Summer Trail Guide').count(), 2)

        url = reverse('employees:season_staffing_plan', kwargs={'season_id': self.season.pk})
        resp = self.client.post(url, {
            'action': 'delete_target',
            'target_id': custom_target.pk,
        })
        self.assertEqual(resp.status_code, 302)

        # Target and placeholders must be completely deleted
        self.assertFalse(SeasonPositionTarget.objects.filter(pk=custom_target.pk).exists())
        self.assertEqual(StaffSchedule.objects.filter(season=self.season, position='Summer Trail Guide').count(), 0)

    def test_operating_dates_view_staffing_integration(self):
        ensure_default_departments_and_positions()
        sync_season_targets_from_schedule(self.season)

        url = reverse('reservations:operating_dates_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Summer 2026")
        self.assertContains(resp, "Staffing Plan")
        self.assertContains(resp, "scheduled /")
