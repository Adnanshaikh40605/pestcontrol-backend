from django.db import models

class Technician(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=255)
    
    # Fields from legacy/core Technician
    age = models.IntegerField(blank=True, null=True)
    alternative_phone = models.CharField(max_length=15, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
