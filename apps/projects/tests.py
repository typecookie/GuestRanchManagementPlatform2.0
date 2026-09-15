from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.projects.models import Project
from apps.contractors.models import Contractor


class ProjectContractorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="projadmin",
            password="password123",
            email="proj@guestranch.com"
        )
        self.client.login(username="projadmin", password="password123")

        self.contractor = Contractor.objects.create(
            name="Timberline Roofing & Construction",
            contact_name="Mark Evans",
            category=Contractor.Category.CONTRACTOR,
            phone="307-555-8833",
            city="Dubois",
            state="WY"
        )

        self.project = Project.objects.create(
            name="Main Lodge Roof Repair",
            status=Project.Status.PROPOSED,
            contractor=self.contractor,
            proposed_cost=4500.00
        )

    def test_project_contractor_link(self):
        self.assertEqual(self.project.contractor, self.contractor)
        self.assertIn(self.project, self.contractor.projects.all())

    def test_project_detail_shows_contractor(self):
        response = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Timberline Roofing &amp; Construction")
        self.assertContains(response, "307-555-8833")

    def test_project_create_with_contractor(self):
        response = self.client.post(reverse('projects:project_create'), {
            'name': 'Saloon Deck Staining',
            'contractor': self.contractor.pk,
            'proposed_cost': '1200.00',
            'actual_cost': '0.00',
        })
        self.assertEqual(response.status_code, 302)
        new_proj = Project.objects.get(name='Saloon Deck Staining')
        self.assertEqual(new_proj.contractor, self.contractor)
