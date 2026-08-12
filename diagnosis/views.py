import csv
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AdminReviewForm, DiagnosisUploadForm, FarmerRegistrationForm, ProfileForm
from .guidance_catalog import guidance_for
from .models import DiagnosisBatch, DiagnosisItem, FarmerProfile, TreatmentGuide
from .services.file_extractors import ExtractionError, extract_upload
from .services.model_service import model_health, predict_image


def home(request):
    return render(
        request,
        'diagnosis/home.html',
        {'model_health': model_health() if request.user.is_staff else None},
    )


@login_required
def register(request):
    """Allow only the logged-in Django superuser to create farmer accounts."""
    if not request.user.is_superuser:
        messages.error(
            request,
            'Only the main administrator can register farmer accounts.',
        )
        return redirect('dashboard')

    if request.method == 'POST':
        form = FarmerRegistrationForm(request.POST)
        if form.is_valid():
            farmer_user = form.save()
            messages.success(
                request,
                f'Farmer account “{farmer_user.username}” was created successfully. '
                'The farmer can now sign in using the username and password set by you.',
            )
            return redirect('register')
    else:
        form = FarmerRegistrationForm()

    recent_farmers = FarmerProfile.objects.select_related('user').order_by('-created_at')[:10]
    return render(
        request,
        'registration/register.html',
        {
            'form': form,
            'recent_farmers': recent_farmers,
            'farmer_count': FarmerProfile.objects.count(),
        },
    )


@login_required
def dashboard(request):
    if request.user.is_staff:
        admin_stats = {
            'farmers': FarmerProfile.objects.count(),
            'batches': DiagnosisBatch.objects.count(),
            'pending': DiagnosisItem.objects.filter(
                review_status='pending'
            ).exclude(ai_status='error').count(),
        }
        recent_farmers = FarmerProfile.objects.select_related('user').order_by('-created_at')[:8]
        recent_batches = DiagnosisBatch.objects.select_related('farmer').annotate(
            total_items=Count('items'),
            pending_items=Count('items', filter=Q(items__review_status='pending')),
        ).order_by('-created_at')[:8]
        return render(
            request,
            'diagnosis/admin_dashboard.html',
            {
                'stats': admin_stats,
                'recent_farmers': recent_farmers,
                'recent_batches': recent_batches,
            },
        )

    batches = request.user.diagnosis_batches.annotate(
        total_items=Count('items'),
        disease_items=Count('items', filter=Q(items__ai_status='disease')),
        pending_items=Count('items', filter=Q(items__review_status='pending')),
    )[:8]
    stats = request.user.diagnosis_batches.aggregate(
        batches=Count('id', distinct=True),
        diagnoses=Count('items'),
        pending=Count('items', filter=Q(items__review_status='pending')),
    )
    return render(request, 'diagnosis/dashboard.html', {'batches': batches, 'stats': stats})


@login_required
def upload_diagnosis(request):
    if request.user.is_staff:
        messages.info(request, 'Administrators review farmer cases from the review queue.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = DiagnosisUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = form.cleaned_data['all_files']
            skipped_folder_files = form.cleaned_data.get('skipped_folder_files', 0)
            if skipped_folder_files:
                messages.warning(
                    request,
                    f'Skipped {skipped_folder_files} unsupported file(s) from the selected folder.'
                )
            batch = DiagnosisBatch.objects.create(
                farmer=request.user,
                title=form.cleaned_data.get('title') or f'Field diagnosis — {timezone.localdate():%d %b %Y}',
                original_file_count=len(files),
                notes=form.cleaned_data.get('notes', ''),
                crop_hint=form.cleaned_data.get('crop_hint', ''),
            )
            success_count = 0
            error_count = 0
            processed_image_count = 0
            limit_reached = False

            for uploaded in files:
                if processed_image_count >= settings.MAX_TOTAL_EXTRACTED_IMAGES:
                    limit_reached = True
                    break
                try:
                    extracted_images = extract_upload(uploaded.name, uploaded.read())
                except ExtractionError as exc:
                    DiagnosisItem.objects.create(
                        batch=batch,
                        original_name=uploaded.name,
                        source_type=Path(uploaded.name).suffix.lower().lstrip('.'),
                        ai_status='error',
                        review_status='pending',
                        error_message=str(exc),
                    )
                    error_count += 1
                    continue

                for extracted in extracted_images:
                    if processed_image_count >= settings.MAX_TOTAL_EXTRACTED_IMAGES:
                        limit_reached = True
                        break
                    processed_image_count += 1
                    item = DiagnosisItem(
                        batch=batch,
                        original_name=extracted.display_name,
                        source_type=extracted.source_type,
                        source_page=extracted.page_number,
                    )
                    image_buffer = BytesIO()
                    extracted.image.save(image_buffer, format='JPEG', quality=90, optimize=True)
                    safe_stem = ''.join(ch if ch.isalnum() else '_' for ch in extracted.display_name)[:80]
                    item.image.save(f'{safe_stem}.jpg', ContentFile(image_buffer.getvalue()), save=False)

                    try:
                        prediction = predict_image(
                            extracted.image,
                            crop_hint=form.cleaned_data.get('crop_hint', ''),
                        )
                        robustness = prediction.pop('robustness', {})
                        for field, value in prediction.items():
                            setattr(item, field, value)
                        guide = TreatmentGuide.objects.filter(
                            class_name=prediction['predicted_class'], active=True
                        ).first()
                        item.treatment_guide = guide
                        snapshot = guide.as_dict() if guide else guidance_for(prediction['predicted_class'])
                        snapshot['prediction_note'] = robustness.get('note', '')
                        snapshot['robustness'] = robustness
                        item.guidance_snapshot = snapshot
                        success_count += 1
                    except Exception as exc:
                        item.ai_status = 'error'
                        error_text = ' '.join(str(exc).split())
                        item.error_message = (
                            error_text[:900] + '…' if len(error_text) > 900 else error_text
                        )
                        error_count += 1
                    item.save()

            batch.image_count = success_count
            batch.completed_at = timezone.now()
            if success_count and (error_count or limit_reached):
                batch.status = 'partial'
            elif success_count:
                batch.status = 'completed'
            else:
                batch.status = 'failed'
            batch.save(update_fields=['image_count', 'completed_at', 'status'])

            if limit_reached:
                messages.warning(
                    request,
                    f'The batch was limited to {settings.MAX_TOTAL_EXTRACTED_IMAGES} extracted images/pages for safe processing.'
                )
            if success_count:
                messages.success(request, f'Processed {success_count} image/page result(s).')
            if error_count:
                messages.warning(request, f'{error_count} item(s) could not be processed. Open the batch for details.')
            return redirect('batch_detail', batch_id=batch.id)
    else:
        form = DiagnosisUploadForm()
    return render(request, 'diagnosis/upload.html', {
        'form': form,
        'max_upload_files': settings.MAX_UPLOAD_FILES,
        'max_upload_size_mb': settings.MAX_UPLOAD_SIZE_MB,
        'max_total_results': settings.MAX_TOTAL_EXTRACTED_IMAGES,
    })


def _get_batch_for_user(user, batch_id):
    batch = get_object_or_404(DiagnosisBatch.objects.prefetch_related('items'), id=batch_id)
    if not user.is_staff and batch.farmer_id != user.id:
        raise Http404
    return batch


@login_required
def batch_detail(request, batch_id):
    batch = _get_batch_for_user(request.user, batch_id)
    return render(request, 'diagnosis/batch_detail.html', {'batch': batch})


@login_required
def download_batch_csv(request, batch_id):
    batch = _get_batch_for_user(request.user, batch_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="plant_diagnosis_{batch.id}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'File/Page', 'Selected Crop', 'Crop', 'AI Disease', 'Confidence %', 'AI Status',
        'Review Status', 'Final Class', 'Admin Prescription', 'Suggested Products', 'Admin Notes'
    ])
    for item in batch.items.all():
        writer.writerow([
            item.original_name, batch.crop_hint or 'Auto-detect', item.crop_name, item.disease_name, item.confidence,
            item.get_ai_status_display(), item.get_review_status_display(), item.final_class,
            item.admin_prescription, item.admin_products, item.admin_notes,
        ])
    return response


@login_required
def profile(request):
    if request.user.is_staff:
        messages.info(request, 'Administrator account details are managed in Django admin.')
        return redirect('dashboard')

    profile_obj, _ = FarmerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile_obj)
    return render(request, 'diagnosis/profile.html', {'form': form})


@staff_member_required(login_url='login')
def review_queue(request):
    status = request.GET.get('status', 'pending')
    items = DiagnosisItem.objects.select_related('batch', 'batch__farmer').exclude(ai_status='error')
    if status in {'pending', 'confirmed', 'corrected'}:
        items = items.filter(review_status=status)
    return render(request, 'diagnosis/review_queue.html', {'items': items[:200], 'selected_status': status})


@staff_member_required(login_url='login')
def review_item(request, item_id):
    item = get_object_or_404(
        DiagnosisItem.objects.select_related('batch', 'batch__farmer', 'treatment_guide'),
        id=item_id
    )
    if request.method == 'POST':
        form = AdminReviewForm(request.POST, instance=item)
        if form.is_valid():
            reviewed = form.save(commit=False)
            reviewed.reviewed_by = request.user
            reviewed.reviewed_at = timezone.now()
            if reviewed.reviewed_class and reviewed.reviewed_class != reviewed.predicted_class:
                reviewed.review_status = 'corrected'
            elif reviewed.review_status == 'pending' or reviewed.reviewed_class == reviewed.predicted_class:
                reviewed.review_status = 'confirmed'
            reviewed.save()
            messages.success(request, 'Review saved and is now visible to the farmer.')
            return redirect('review_item', item_id=item.id)
    else:
        form = AdminReviewForm(instance=item)
    return render(request, 'diagnosis/review_item.html', {'item': item, 'form': form})
