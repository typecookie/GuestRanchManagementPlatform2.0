from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from apps.employees.models import Employee, PositionHistory, Interview
from apps.employees.forms import InterviewForm, EmployeeForm

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
