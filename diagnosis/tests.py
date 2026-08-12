import json
import zipfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils.datastructures import MultiValueDict

from .forms import DiagnosisUploadForm
from .models import FarmerProfile
from .services.file_extractors import extract_upload


class ExtractorTests(TestCase):
    def test_png_is_extracted(self):
        buffer = BytesIO()
        Image.new('RGB', (64, 64), 'green').save(buffer, format='PNG')
        results = extract_upload('leaf.png', buffer.getvalue())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].image.mode, 'RGB')


class UploadFormTests(TestCase):
    @staticmethod
    def image_upload(name):
        buffer = BytesIO()
        Image.new('RGB', (16, 16), 'green').save(buffer, format='JPEG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')

    def test_multiple_individual_files_are_combined(self):
        form = DiagnosisUploadForm(
            data={'title': 'Batch'},
            files=MultiValueDict({'files': [self.image_upload('a.jpg'), self.image_upload('b.jpg')]}),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data['all_files']), 2)

    def test_files_and_folder_files_can_be_submitted_together(self):
        form = DiagnosisUploadForm(
            data={'title': 'Batch'},
            files=MultiValueDict({
                'files': [self.image_upload('single.jpg')],
                'folder_files': [
                    self.image_upload('folder_a.jpg'),
                    self.image_upload('folder_b.jpg'),
                ],
            }),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data['all_files']), 3)


class ModelArchiveTests(TestCase):
    def test_model_archive_contains_38_class_compatible_config(self):
        model_path = Path(settings.MODEL_PATH)
        labels = json.loads(Path(settings.CLASS_NAMES_PATH).read_text(encoding='utf-8'))
        self.assertEqual(len(labels), 38)
        with zipfile.ZipFile(model_path) as archive:
            config_text = archive.read('config.json').decode('utf-8')
            self.assertIn('model.weights.h5', archive.namelist())
            self.assertNotIn('"input_axes"', config_text)
            self.assertNotIn('"output_axes"', config_text)


class PageTests(TestCase):
    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_upload_page_has_file_and_folder_controls(self):
        user = User.objects.create_user(username='farmer', password='pass12345')
        self.client.force_login(user)
        response = self.client.get(reverse('upload_diagnosis'))
        self.assertContains(response, 'Choose files')
        self.assertContains(response, 'Choose folder')
        self.assertContains(response, 'webkitdirectory')


class AdminManagedRegistrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='mainadmin',
            email='admin@example.com',
            password='AdminPass123!',
        )
        self.staff_reviewer = User.objects.create_user(
            username='reviewer',
            password='ReviewPass123!',
            is_staff=True,
        )
        self.farmer = User.objects.create_user(
            username='existingfarmer',
            password='FarmerPass123!',
        )
        FarmerProfile.objects.create(user=self.farmer)

    def test_public_registration_requires_login(self):
        response = self.client.get(reverse('register'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('register')}",
            fetch_redirect_response=False,
        )

    def test_normal_farmer_cannot_open_registration(self):
        self.client.force_login(self.farmer)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_staff_reviewer_cannot_open_registration(self):
        self.client.force_login(self.staff_reviewer)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_superuser_can_open_registration(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator-only registration')

    def test_admin_creates_farmer_without_switching_session(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newfarmer',
                'first_name': 'New',
                'last_name': 'Farmer',
                'email': 'newfarmer@example.com',
                'phone': '9999999999',
                'village': 'Kopargaon',
                'district': 'Ahmednagar',
                'state': 'Maharashtra',
                'preferred_language': 'en',
                'password1': 'StrongFarmerPass123!',
                'password2': 'StrongFarmerPass123!',
            },
        )
        self.assertRedirects(response, reverse('register'))
        new_farmer = User.objects.get(username='newfarmer')
        self.assertFalse(new_farmer.is_staff)
        self.assertFalse(new_farmer.is_superuser)
        self.assertTrue(hasattr(new_farmer, 'farmerprofile'))
        self.assertEqual(
            new_farmer.farmerprofile.visible_login_password,
            'StrongFarmerPass123!',
        )
        self.assertNotEqual(
            new_farmer.farmerprofile.encrypted_login_password,
            'StrongFarmerPass123!',
        )
        self.assertEqual(int(self.client.session['_auth_user_id']), self.admin.id)

        password_list_response = self.client.get(reverse('register'))
        self.assertContains(password_list_response, 'StrongFarmerPass123!')

    def test_public_pages_have_no_self_registration_link(self):
        home_response = self.client.get(reverse('home'))
        login_response = self.client.get(reverse('login'))
        self.assertNotContains(home_response, 'Create farmer account')
        self.assertNotContains(login_response, 'Create an account')
        self.assertContains(login_response, 'Public farmer self-registration is disabled')

    def test_admin_dashboard_is_role_aware(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'diagnosis/admin_dashboard.html')
        self.assertContains(response, 'Register farmer')
