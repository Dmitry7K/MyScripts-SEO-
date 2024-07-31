from django.db import models

class Domain(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateField()

    def __str__(self):
        return self.name
# Create your models here.
