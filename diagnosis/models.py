import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from .services.credential_vault import (
    CredentialVaultError, decrypt_password, encrypt_password,
)


def diagnosis_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower() or '.jpg'
    return f'diagnoses/user_{instance.batch.farmer_id}/{instance.batch_id}/{uuid.uuid4().hex}{suffix}'


class FarmerProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('mr', 'Marathi'),
        ('hi', 'Hindi'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    village = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True, default='Maharashtra')
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    encrypted_login_password = models.TextField(blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def store_login_password(self, raw_password):
        """Encrypt and save the farmer password for superuser-only retrieval."""
        self.encrypted_login_password = encrypt_password(raw_password)
        self.save(update_fields=['encrypted_login_password'])

    @property
    def visible_login_password(self):
        """Return the decrypted password, or a safe status message."""
        if not self.encrypted_login_password:
            return 'Not stored (farmer registered before this update)'
        try:
            return decrypt_password(self.encrypted_login_password)
        except CredentialVaultError:
            return 'Unavailable — DJANGO_SECRET_KEY changed'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class TreatmentGuide(models.Model):
    class_name = models.CharField(max_length=220, unique=True)
    crop_name = models.CharField(max_length=120)
    disease_name = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    immediate_actions = models.TextField(blank=True)
    organic_options = models.TextField(blank=True)
    chemical_options = models.TextField(blank=True)
    prevention = models.TextField(blank=True)
    disclaimer = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['crop_name', 'disease_name']

    def __str__(self):
        return f'{self.crop_name} — {self.disease_name}'

    def as_dict(self):
        return {
            'summary': self.summary,
            'symptoms': self.symptoms,
            'immediate_actions': self.immediate_actions,
            'organic_options': self.organic_options,
            'chemical_options': self.chemical_options,
            'prevention': self.prevention,
            'disclaimer': self.disclaimer,
        }


class DiagnosisBatch(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partial', 'Completed with errors'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diagnosis_batches')
    title = models.CharField(max_length=160, blank=True)
    original_file_count = models.PositiveIntegerField(default=0)
    image_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    notes = models.TextField(blank=True)
    crop_hint = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.title:
            return self.title
        if self.created_at:
            return f'Diagnosis {self.created_at:%d %b %Y %H:%M}'
        return 'New diagnosis batch'


class DiagnosisItem(models.Model):
    AI_STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('disease', 'Disease detected'),
        ('uncertain', 'Needs review'),
        ('error', 'Processing error'),
    ]
    REVIEW_CHOICES = [
        ('pending', 'Pending review'),
        ('confirmed', 'Confirmed'),
        ('corrected', 'Corrected'),
    ]

    batch = models.ForeignKey(DiagnosisBatch, on_delete=models.CASCADE, related_name='items')
    original_name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=30, blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to=diagnosis_upload_path, blank=True)
    predicted_class = models.CharField(max_length=220, blank=True)
    crop_name = models.CharField(max_length=120, blank=True)
    disease_name = models.CharField(max_length=160, blank=True)
    confidence = models.FloatField(default=0)
    top_predictions = models.JSONField(default=list, blank=True)
    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='uncertain')
    guidance_snapshot = models.JSONField(default=dict, blank=True)
    treatment_guide = models.ForeignKey(TreatmentGuide, null=True, blank=True, on_delete=models.SET_NULL)
    review_status = models.CharField(max_length=20, choices=REVIEW_CHOICES, default='pending')
    reviewed_class = models.CharField(max_length=220, blank=True)
    admin_prescription = models.TextField(blank=True)
    admin_products = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_diagnoses'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.original_name}: {self.predicted_class or self.ai_status}'

    @property
    def final_class(self):
        return self.reviewed_class or self.predicted_class

    @property
    def final_class_display(self):
        return self.final_class.replace('___', ' — ').replace('__', ' — ').replace('_', ' ')

    @property
    def needs_review(self):
        return self.review_status == 'pending'
