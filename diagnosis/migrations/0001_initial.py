import uuid
import diagnosis.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TreatmentGuide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_name', models.CharField(max_length=220, unique=True)),
                ('crop_name', models.CharField(max_length=120)),
                ('disease_name', models.CharField(max_length=160)),
                ('summary', models.TextField(blank=True)),
                ('symptoms', models.TextField(blank=True)),
                ('immediate_actions', models.TextField(blank=True)),
                ('organic_options', models.TextField(blank=True)),
                ('chemical_options', models.TextField(blank=True)),
                ('prevention', models.TextField(blank=True)),
                ('disclaimer', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['crop_name', 'disease_name']},
        ),
        migrations.CreateModel(
            name='DiagnosisBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=160)),
                ('original_file_count', models.PositiveIntegerField(default=0)),
                ('image_count', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('processing', 'Processing'), ('completed', 'Completed'), ('partial', 'Completed with errors'), ('failed', 'Failed')], default='processing', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('farmer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diagnosis_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='FarmerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('village', models.CharField(blank=True, max_length=120)),
                ('district', models.CharField(blank=True, max_length=120)),
                ('state', models.CharField(blank=True, default='Maharashtra', max_length=120)),
                ('preferred_language', models.CharField(choices=[('en', 'English'), ('mr', 'Marathi'), ('hi', 'Hindi')], default='en', max_length=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DiagnosisItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_name', models.CharField(max_length=255)),
                ('source_type', models.CharField(blank=True, max_length=30)),
                ('source_page', models.PositiveIntegerField(blank=True, null=True)),
                ('image', models.ImageField(blank=True, upload_to=diagnosis.models.diagnosis_upload_path)),
                ('predicted_class', models.CharField(blank=True, max_length=220)),
                ('crop_name', models.CharField(blank=True, max_length=120)),
                ('disease_name', models.CharField(blank=True, max_length=160)),
                ('confidence', models.FloatField(default=0)),
                ('top_predictions', models.JSONField(blank=True, default=list)),
                ('ai_status', models.CharField(choices=[('healthy', 'Healthy'), ('disease', 'Disease detected'), ('uncertain', 'Needs review'), ('error', 'Processing error')], default='uncertain', max_length=20)),
                ('guidance_snapshot', models.JSONField(blank=True, default=dict)),
                ('review_status', models.CharField(choices=[('pending', 'Pending review'), ('confirmed', 'Confirmed'), ('corrected', 'Corrected')], default='pending', max_length=20)),
                ('reviewed_class', models.CharField(blank=True, max_length=220)),
                ('admin_prescription', models.TextField(blank=True)),
                ('admin_products', models.TextField(blank=True)),
                ('admin_notes', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='diagnosis.diagnosisbatch')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_diagnoses', to=settings.AUTH_USER_MODEL)),
                ('treatment_guide', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='diagnosis.treatmentguide')),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
