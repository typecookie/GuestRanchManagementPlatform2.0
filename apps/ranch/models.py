from django.db import models

class RanchPermissions(models.Model):
    class Meta:
        managed = False  # No database table
        permissions = [
            ("view_ranch", "Can view ranch operations"),
            ("edit_ranch", "Can edit ranch operations"),
        ]
