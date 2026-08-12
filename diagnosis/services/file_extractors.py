from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
import zipfile

import fitz
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError
from django.conf import settings


class ExtractionError(ValueError):
    pass


@dataclass
class ExtractedImage:
    display_name: str
    source_type: str
    page_number: int | None
    image: Image.Image


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff'}
OFFICE_EXTENSIONS = {'.docx', '.pptx'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | OFFICE_EXTENSIONS | {'.pdf', '.zip'}


def _safe_name(name):
    return Path(PurePosixPath(name).name).name[:180] or 'image'


def _normalize_image(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    max_side = 2200
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return image.copy()


def _images_from_image_bytes(name, data, source_type='image'):
    results = []
    try:
        with Image.open(BytesIO(data)) as opened:
            for number, frame in enumerate(ImageSequence.Iterator(opened), start=1):
                if len(results) >= settings.MAX_EXTRACTED_IMAGES_PER_FILE:
                    break
                page = number if getattr(opened, 'n_frames', 1) > 1 else None
                display = f'{_safe_name(name)} — frame {number}' if page else _safe_name(name)
                results.append(ExtractedImage(display, source_type, page, _normalize_image(frame)))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ExtractionError(f'Could not open image {name}: {exc}') from exc
    return results


def _images_from_pdf(name, data):
    results = []
    try:
        document = fitz.open(stream=data, filetype='pdf')
    except Exception as exc:
        raise ExtractionError(f'Could not open PDF {name}: {exc}') from exc
    try:
        page_limit = min(document.page_count, settings.MAX_EXTRACTED_IMAGES_PER_FILE)
        for index in range(page_limit):
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes('png')))
            results.append(ExtractedImage(
                f'{_safe_name(name)} — page {index + 1}', 'pdf', index + 1, _normalize_image(image)
            ))
    finally:
        document.close()
    if not results:
        raise ExtractionError(f'PDF {name} contains no pages.')
    return results


def _images_from_office(name, data, suffix):
    media_prefix = 'word/media/' if suffix == '.docx' else 'ppt/media/'
    results = []
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            members = [
                info for info in archive.infolist()
                if not info.is_dir()
                and info.filename.startswith(media_prefix)
                and Path(info.filename).suffix.lower() in IMAGE_EXTENSIONS
            ]
            for info in members[:settings.MAX_EXTRACTED_IMAGES_PER_FILE]:
                member_data = archive.read(info)
                embedded_name = f'{_safe_name(name)} — {_safe_name(info.filename)}'
                for extracted in _images_from_image_bytes(embedded_name, member_data, source_type=suffix[1:]):
                    results.append(extracted)
                    if len(results) >= settings.MAX_EXTRACTED_IMAGES_PER_FILE:
                        break
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ExtractionError(f'Could not read {suffix.upper()[1:]} file {name}: {exc}') from exc
    if not results:
        raise ExtractionError(f'No embedded images were found in {name}.')
    return results


def _images_from_zip(name, data):
    results = []
    max_total = settings.MAX_ZIP_UNCOMPRESSED_MB * 1024 * 1024
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if len(members) > settings.MAX_ZIP_MEMBERS:
                raise ExtractionError(
                    f'ZIP contains more than {settings.MAX_ZIP_MEMBERS} files.'
                )
            if sum(info.file_size for info in members) > max_total:
                raise ExtractionError(
                    f'ZIP expands beyond {settings.MAX_ZIP_UNCOMPRESSED_MB} MB.'
                )
            for info in members:
                if len(results) >= settings.MAX_EXTRACTED_IMAGES_PER_FILE:
                    break
                # Reject encrypted entries and suspicious absolute/traversal paths.
                member_path = PurePosixPath(info.filename)
                if info.flag_bits & 0x1 or member_path.is_absolute() or '..' in member_path.parts:
                    continue
                suffix = Path(info.filename).suffix.lower()
                if suffix not in (IMAGE_EXTENSIONS | OFFICE_EXTENSIONS | {'.pdf'}):
                    continue
                member_data = archive.read(info)
                nested_name = f'{_safe_name(name)} / {_safe_name(info.filename)}'
                nested = extract_upload(nested_name, member_data, allow_zip=False)
                for extracted in nested:
                    results.append(extracted)
                    if len(results) >= settings.MAX_EXTRACTED_IMAGES_PER_FILE:
                        break
    except zipfile.BadZipFile as exc:
        raise ExtractionError(f'Could not open ZIP {name}: {exc}') from exc
    if not results:
        raise ExtractionError(f'No supported plant images or PDF pages were found in {name}.')
    return results


def extract_upload(name, data, allow_zip=True):
    suffix = Path(name).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return _images_from_image_bytes(name, data)
    if suffix == '.pdf':
        return _images_from_pdf(name, data)
    if suffix in OFFICE_EXTENSIONS:
        return _images_from_office(name, data, suffix)
    if suffix == '.zip' and allow_zip:
        return _images_from_zip(name, data)
    raise ExtractionError(f'Unsupported file type: {name}')
