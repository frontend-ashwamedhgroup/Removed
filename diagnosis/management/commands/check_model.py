from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from diagnosis.services.model_service import model_archive_info, model_health, predict_image


class Command(BaseCommand):
    help = 'Validate the supplied Keras model archive, label mapping and one inference.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archive-only',
            action='store_true',
            help='Validate the .keras archive without requiring class_names.json or TensorFlow inference.',
        )

    def handle(self, *args, **options):
        try:
            archive = model_archive_info()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            'Keras archive valid: '
            f"{archive['output_units']} outputs, "
            f"{archive['image_size'][0]}x{archive['image_size'][1]}, "
            f"saved Keras={archive.get('saved_keras')}, date={archive.get('date_saved')}."
        ))

        if options.get('archive_only'):
            return

        health = model_health()
        if not health.get('ok'):
            raise CommandError(health.get('error', 'Unknown model loading error.'))

        sample = Image.new('RGB', (224, 224), (75, 135, 70))
        try:
            result = predict_image(sample)
        except Exception as exc:
            raise CommandError(f'Model loaded but prediction failed: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(
            'Model check passed: '
            f"{health['classes']} classes, {health['image_size'][0]}x{health['image_size'][1]}, "
            f"loader={health.get('load_mode')}, installed Keras={health.get('installed_keras')}, "
            f"saved Keras={health.get('saved_keras')}."
        ))
        self.stdout.write(
            f"Test prediction completed: {result['predicted_class']} "
            f"({result['confidence']:.2f}%)."
        )
