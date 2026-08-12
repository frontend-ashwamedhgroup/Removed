import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from diagnosis.services.model_service import clear_model_cache, model_archive_info


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tif', '.tiff'}


class Command(BaseCommand):
    help = (
        'Install the exact class-name order for the currently configured Keras model '
        'from either the training-generated class_names.json or the exact training dataset.'
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--json', dest='json_path', help='Path to class_names.json from the same training run.')
        group.add_argument('--dataset', dest='dataset_path', help='Path to the exact dataset folder used by image_dataset_from_directory.')

    def _from_json(self, path):
        path = Path(path).expanduser()
        if not path.exists() or not path.is_file():
            raise CommandError(f'Label JSON file not found: {path}')
        try:
            labels = json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            raise CommandError(f'Could not read {path}: {exc}') from exc
        return labels

    def _from_dataset(self, path):
        path = Path(path).expanduser()
        if not path.exists() or not path.is_dir():
            raise CommandError(f'Dataset folder not found: {path}')

        # tf.keras.utils.image_dataset_from_directory uses alphanumeric ordering
        # when class_names is not supplied. The immediate child directory names are
        # therefore the class-index order for the common training workflow used here.
        labels = sorted(p.name for p in path.iterdir() if p.is_dir())
        if not labels:
            raise CommandError(f'No class folders were found inside: {path}')
        return labels

    def handle(self, *args, **options):
        archive = model_archive_info()
        expected = int(archive['output_units'])
        if options.get('json_path'):
            labels = self._from_json(options['json_path'])
            source = options['json_path']
        else:
            labels = self._from_dataset(options['dataset_path'])
            source = options['dataset_path']

        if not isinstance(labels, list) or not labels:
            raise CommandError('The supplied label source did not produce a non-empty list.')
        if not all(isinstance(name, str) and name.strip() for name in labels):
            raise CommandError('Every class label must be a non-empty string.')
        if len(labels) != expected:
            raise CommandError(
                f'This model has {expected} outputs, but the supplied source produced '
                f'{len(labels)} labels. These files do not belong to the same training run.'
            )
        if len(set(labels)) != len(labels):
            raise CommandError('Duplicate class labels were found; refusing to install them.')

        output = Path(settings.CLASS_NAMES_PATH)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            backup = output.with_name(output.stem + '_backup.json')
            backup.write_bytes(output.read_bytes())
            self.stdout.write(f'Backed up previous labels to: {backup}')

        output.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding='utf-8')
        clear_model_cache()

        self.stdout.write(self.style.SUCCESS(
            f'Installed {len(labels)} model labels from {source} -> {output}'
        ))
        self.stdout.write(f'First label: {labels[0]}')
        self.stdout.write(f'Last label : {labels[-1]}')
        self.stdout.write('Now run: python manage.py check_model')
