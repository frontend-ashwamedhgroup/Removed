import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from diagnosis.guidance_catalog import guidance_for, split_class_name
from diagnosis.models import TreatmentGuide


class Command(BaseCommand):
    help = 'Create or update treatment guidance for all model classes.'

    def handle(self, *args, **options):
        labels_path = Path(settings.CLASS_NAMES_PATH)
        if not labels_path.exists():
            raise CommandError(f'Class names file not found: {labels_path}')
        class_names = json.loads(labels_path.read_text(encoding='utf-8'))
        created = 0
        updated = 0
        for class_name in class_names:
            crop, disease = split_class_name(class_name)
            defaults = {
                'crop_name': crop,
                'disease_name': disease,
                **guidance_for(class_name),
                'active': True,
            }
            _, was_created = TreatmentGuide.objects.update_or_create(
                class_name=class_name, defaults=defaults
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(
            f'Treatment guides ready: {created} created, {updated} updated.'
        ))
