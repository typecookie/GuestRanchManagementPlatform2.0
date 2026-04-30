from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
import os

class Command(BaseCommand):
    help = 'Initializes the ranch management platform with default groups and an optional superuser.'

    def handle(self, *args, **options):
        # 1. Create the Admin Group
        admin_group, created = Group.objects.get_or_create(name='Ranch Admins')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group "Ranch Admins"'))
        
        # 2. Assign permissions to Admin Group
        # We want to give them all permissions for our custom apps + user management
        app_labels = ['clients', 'reservations', 'horses', 'cabins', 'vehicles', 'ranch', 'auth']
        permissions = Permission.objects.filter(content_type__app_label__in=app_labels)
        admin_group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(f'Assigned {permissions.count()} permissions to "Ranch Admins" group'))

        # 3. Create initial superuser if it doesn't exist
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write('No superuser found. You can create one now.')
            try:
                from django.core.management import call_command
                call_command('createsuperuser')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))
                self.stdout.write('Falling back to environment variables or defaults...')
                username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
                email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
                password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'adminpass')
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created.'))
        else:
            self.stdout.write('Superuser already exists.')
