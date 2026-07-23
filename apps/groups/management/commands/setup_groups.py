from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Initializes default groups'

    def handle(self, *args, **options):
        groups = [
            'superuser', 
            'administrator', 
            'barn managers', 
            'barn', 
            'office', 
            'kitchen', 
            'maintanice', 
            'fishing guides', 
            'housekeeping', 
            'wait staff', 
            'kids program', 
            'hiking guide'
        ]
        
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {group_name}'))
            else:
                self.stdout.write(f'Group already exists: {group_name}')
