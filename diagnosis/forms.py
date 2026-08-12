import json
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import DiagnosisItem, FarmerProfile


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'accept': '.jpg,.jpeg,.png,.webp,.bmp,.gif,.tif,.tiff,.pdf,.zip,.docx,.pptx',
            'class': 'file-input',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)]


class FarmerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    village = forms.CharField(max_length=120, required=False)
    district = forms.CharField(max_length=120, required=False)
    state = forms.CharField(max_length=120, initial='Maharashtra', required=False)
    preferred_language = forms.ChoiceField(choices=FarmerProfile.LANGUAGE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = FarmerProfile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', ''),
                village=self.cleaned_data.get('village', ''),
                district=self.cleaned_data.get('district', ''),
                state=self.cleaned_data.get('state', ''),
                preferred_language=self.cleaned_data.get('preferred_language', 'en'),
            )
            # UserCreationForm has already stored Django's one-way password hash.
            # Keep a separate encrypted copy so the main administrator can view
            # the assigned farmer password permanently from the registration page.
            profile.store_login_password(self.cleaned_data['password1'])
        return user


def _supported_crop_choices():
    """Build crop choices from the exact class-name file shipped with the model."""
    try:
        from .guidance_catalog import split_class_name
        class_names = json.loads(Path(settings.CLASS_NAMES_PATH).read_text(encoding="utf-8"))
        crops = sorted({split_class_name(name)[0] for name in class_names})
    except Exception:
        crops = []
    return [("", "Auto-detect crop (use for mixed-crop batches)")] + [
        (crop, crop) for crop in crops
    ]


class DiagnosisUploadForm(forms.Form):
    title = forms.CharField(
        max_length=160, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Example: Onion field — north plot'})
    )
    crop_hint = forms.ChoiceField(
        required=False,
        choices=(),
        help_text=(
            "Recommended for Google/field photos. Choosing the known crop prevents "
            "cross-crop predictions. Leave Auto-detect only for mixed-crop batches."
        ),
    )
    files = MultipleFileField(
        required=False,
        help_text='Choose one or many individual files.',
        widget=MultipleFileInput(attrs={
            'accept': '.jpg,.jpeg,.png,.webp,.bmp,.gif,.tif,.tiff,.pdf,.zip,.docx,.pptx',
            'class': 'file-input',
            'data-file-input': 'files',
        }),
    )
    folder_files = MultipleFileField(
        required=False,
        help_text='Choose a folder; every supported file inside it will be uploaded.',
        widget=MultipleFileInput(attrs={
            'class': 'file-input folder-input',
            'webkitdirectory': True,
            'directory': True,
            'multiple': True,
            'data-file-input': 'folder',
        }),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Optional: crop age, symptoms, recent weather or treatments',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["crop_hint"].choices = _supported_crop_choices()

    @staticmethod
    def _validate_uploads(files):
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        allowed = {
            '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif',
            '.tiff', '.pdf', '.zip', '.docx', '.pptx'
        }
        errors = []
        for uploaded in files:
            suffix = Path(uploaded.name).suffix.lower()
            if suffix not in allowed:
                errors.append(f'Unsupported file type: {uploaded.name}')
            elif uploaded.size > max_bytes:
                errors.append(
                    f'{uploaded.name} is larger than '
                    f'{settings.MAX_UPLOAD_SIZE_MB} MB.'
                )
        if errors:
            raise forms.ValidationError(errors[:10])

    def clean(self):
        cleaned = super().clean()
        files = list(cleaned.get('files') or [])
        folder_files = list(cleaned.get('folder_files') or [])
        allowed = {
            '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif',
            '.tiff', '.pdf', '.zip', '.docx', '.pptx'
        }

        # Individual selections are validated strictly. A folder may contain
        # harmless unrelated files such as desktop.ini or notes.txt, so those
        # are skipped rather than causing the entire crop batch to fail.
        self._validate_uploads(files)
        supported_folder_files = [
            uploaded for uploaded in folder_files
            if Path(uploaded.name).suffix.lower() in allowed
        ]
        skipped_folder_files = len(folder_files) - len(supported_folder_files)
        self._validate_uploads(supported_folder_files)

        all_files = files + supported_folder_files
        if not all_files:
            raise forms.ValidationError(
                'Choose at least one supported file or a folder containing '
                'supported images/documents.'
            )
        if len(all_files) > settings.MAX_UPLOAD_FILES:
            raise forms.ValidationError(
                f'Choose no more than {settings.MAX_UPLOAD_FILES} supported '
                'source files in one batch.'
            )

        cleaned['all_files'] = all_files
        cleaned['skipped_folder_files'] = skipped_folder_files
        return cleaned


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = FarmerProfile
        fields = ('phone', 'village', 'district', 'state', 'preferred_language')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile


class AdminReviewForm(forms.ModelForm):
    class Meta:
        model = DiagnosisItem
        fields = (
            'review_status', 'reviewed_class', 'admin_prescription',
            'admin_products', 'admin_notes'
        )
        widgets = {
            'admin_prescription': forms.Textarea(attrs={'rows': 5}),
            'admin_products': forms.Textarea(attrs={'rows': 4}),
            'admin_notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            class_names = json.loads(Path(settings.CLASS_NAMES_PATH).read_text(encoding='utf-8'))
        except Exception:
            class_names = []
        choices = [('', 'Keep AI prediction')] + [(name, name.replace('_', ' ')) for name in class_names]
        self.fields['reviewed_class'] = forms.ChoiceField(choices=choices, required=False)
