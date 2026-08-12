import json
import shutil
import tempfile
import threading
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from django.conf import settings

from diagnosis.guidance_catalog import split_class_name

_PREDICT_LOCK = threading.Lock()


class ModelLoadError(RuntimeError):
    """Raised when the supplied AI model cannot be initialized."""


def _short_error(exc: Exception, limit: int = 420) -> str:
    """Keep technical errors useful without printing multi-page model configs."""
    text = " ".join(str(exc).split())
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return f"{exc.__class__.__name__}: {text}"


def _read_saved_keras_version(model_path: Path) -> str:
    try:
        with zipfile.ZipFile(model_path) as archive:
            metadata = json.loads(archive.read("metadata.json"))
        return str(metadata.get("keras_version") or "unknown")
    except Exception:
        return "unknown"


def model_archive_info(model_path=None):
    """Inspect a Keras v3 archive without importing TensorFlow/Keras."""
    model_path = Path(model_path or settings.MODEL_PATH)
    if not model_path.exists():
        raise ModelLoadError(f"Model file not found: {model_path}")

    try:
        with zipfile.ZipFile(model_path) as archive:
            metadata = json.loads(archive.read("metadata.json"))
            config = json.loads(archive.read("config.json"))
    except Exception as exc:
        raise ModelLoadError(
            f"Could not inspect Keras archive: {_short_error(exc)}"
        ) from exc

    root = config.get("config") or {}
    layers = root.get("layers") or []
    input_shape = None
    output_units = None

    for layer in layers:
        layer_config = layer.get("config") or {}
        if layer.get("class_name") == "InputLayer" and input_shape is None:
            input_shape = layer_config.get("batch_shape") or layer_config.get("batch_input_shape")
        if layer.get("class_name") == "Dense":
            units = layer_config.get("units")
            if isinstance(units, int):
                output_units = units

    if output_units is None:
        raise ModelLoadError(
            "Could not determine the classifier output size from config.json."
        )

    width = height = 224
    if isinstance(input_shape, list) and len(input_shape) >= 4:
        try:
            height = int(input_shape[1] or 224)
            width = int(input_shape[2] or 224)
        except (TypeError, ValueError):
            pass

    return {
        "output_units": int(output_units),
        "image_size": (width, height),
        "saved_keras": str(metadata.get("keras_version") or "unknown"),
        "date_saved": str(metadata.get("date_saved") or "unknown"),
    }


def _extract_weights_file(model_path: Path) -> Path:
    """
    Extract the weights stored inside a Keras v3 .keras ZIP into a writable
    temporary cache. This is used only as a compatibility fallback when an
    older installed Keras cannot deserialize a newer model configuration.
    """
    stat = model_path.stat()
    cache_key = f"{model_path.stem}_{stat.st_size}_{stat.st_mtime_ns}"
    cache_dir = Path(tempfile.gettempdir()) / "cropcare_ai_model_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    weights_path = cache_dir / f"{cache_key}.weights.h5"

    if weights_path.exists() and weights_path.stat().st_size > 0:
        return weights_path

    temporary_path = weights_path.with_suffix(weights_path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(model_path) as archive:
            member_name = "model.weights.h5"
            if member_name not in archive.namelist():
                raise ModelLoadError(
                    "The .keras archive does not contain model.weights.h5."
                )
            with archive.open(member_name) as source, temporary_path.open("wb") as target:
                shutil.copyfileobj(source, target)
        temporary_path.replace(weights_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return weights_path


def _build_supplied_architecture(keras, class_count: int):
    """Rebuild the exact architecture used in the supplied training notebook."""
    keras.backend.clear_session()

    augmentation = keras.Sequential(
        [
            keras.layers.RandomFlip("horizontal_and_vertical"),
            keras.layers.RandomRotation(0.12),
            keras.layers.RandomZoom(0.12),
            keras.layers.RandomContrast(0.12),
        ],
        name="augmentation",
    )

    base_model = keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights=None,
    )
    base_model.trainable = True

    inputs = keras.Input(shape=(224, 224, 3), name="input_layer_1")
    x = augmentation(inputs)
    x = keras.applications.mobilenet_v2.preprocess_input(x)
    x = base_model(x, training=False)
    x = keras.layers.GlobalAveragePooling2D(name="global_average_pooling2d")(x)
    x = keras.layers.Dropout(0.25, name="dropout")(x)
    outputs = keras.layers.Dense(
        class_count, activation="softmax", name="dense"
    )(x)
    return keras.Model(inputs, outputs, name="functional_1")


def _load_model_with_compatibility_fallback(model_path: Path, class_count: int):
    try:
        import keras
    except ImportError as exc:
        raise ModelLoadError(
            "Keras/TensorFlow is not installed. Run setup_windows.bat or "
            "repair_environment.bat."
        ) from exc

    installed_keras = getattr(keras, "__version__", "unknown")
    saved_keras = _read_saved_keras_version(model_path)
    native_error = None

    try:
        model = keras.models.load_model(model_path, compile=False, safe_mode=True)
        return model, "native", installed_keras, saved_keras
    except Exception as exc:
        native_error = exc

    # Compatibility route: instantiate the known MobileNetV2 architecture and
    # load only the numerical weights. This avoids deserializing newer config
    # fields such as initializer arguments that older Keras versions do not know.
    try:
        model = _build_supplied_architecture(keras, class_count)
        weights_path = _extract_weights_file(model_path)
        model.load_weights(weights_path)
        return model, "weights-fallback", installed_keras, saved_keras
    except Exception as fallback_exc:
        raise ModelLoadError(
            "The Keras model could not be loaded. "
            f"Saved Keras version: {saved_keras}; installed Keras version: "
            f"{installed_keras}. Native load error: {_short_error(native_error)}. "
            f"Weights fallback error: {_short_error(fallback_exc)}. "
            "Run repair_environment.bat, then run: python manage.py check_model"
        ) from fallback_exc


@lru_cache(maxsize=1)
def _load_assets():
    model_path = Path(settings.MODEL_PATH)
    labels_path = Path(settings.CLASS_NAMES_PATH)
    archive = model_archive_info(model_path)
    expected_count = int(archive["output_units"])

    if not labels_path.exists():
        raise ModelLoadError(
            f"The updated model has {expected_count} outputs, but its matching "
            f"class_names.json is not installed at {labels_path}. The previous "
            "38-class label file is intentionally not reused because that would "
            "mislabel predictions. Copy the class_names.json generated during the "
            "same training run, or run: python manage.py install_model_labels "
            "--json <path-to-class_names.json>. If you still have the exact "
            "training dataset folders, use --dataset <dataset-folder>."
        )

    try:
        class_names = json.loads(labels_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModelLoadError(f"Could not read class names: {_short_error(exc)}") from exc

    if not isinstance(class_names, list) or not class_names:
        raise ModelLoadError("class_names.json must contain a non-empty JSON list.")
    if not all(isinstance(name, str) and name.strip() for name in class_names):
        raise ModelLoadError("Every entry in class_names.json must be a non-empty string.")
    if len(set(class_names)) != len(class_names):
        raise ModelLoadError("class_names.json contains duplicate label names.")
    if len(class_names) != expected_count:
        raise ModelLoadError(
            f"Class label count ({len(class_names)}) does not match the updated "
            f"model output ({expected_count}). Do not use labels from an older model."
        )

    model, load_mode, installed_keras, saved_keras = (
        _load_model_with_compatibility_fallback(model_path, expected_count)
    )

    output_units = int(model.output_shape[-1])
    if output_units != expected_count:
        raise ModelLoadError(
            f"Loaded model output ({output_units}) does not match archive output "
            f"({expected_count})."
        )

    input_shape = model.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]
    height = int(input_shape[1] or archive["image_size"][1])
    width = int(input_shape[2] or archive["image_size"][0])
    return model, class_names, (width, height), {
        "load_mode": load_mode,
        "installed_keras": installed_keras,
        "saved_keras": saved_keras,
        "date_saved": archive.get("date_saved"),
        "archive_output_units": expected_count,
    }


def clear_model_cache():
    """Useful for tests and after replacing the model while the server is running."""
    _load_assets.cache_clear()


def model_health():
    try:
        model, class_names, image_size, metadata = _load_assets()
        return {
            "ok": True,
            "classes": len(class_names),
            "image_size": image_size,
            **metadata,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _canonical_crop(value: str) -> str:
    return " ".join((value or "").replace("_", " ").replace(",", " ").split()).casefold()


def _class_crop(class_name: str) -> str:
    crop_name, _ = split_class_name(class_name)
    return crop_name


def _build_real_world_views(image: Image.Image, image_size):
    """
    Build several inference views that resemble the augmentations used during
    training. Averaging predictions across them is more stable for web/field
    photos than relying on one stretched resize only.
    """
    rgb = ImageOps.exif_transpose(image.convert("RGB"))
    full = rgb.resize(image_size, Image.Resampling.LANCZOS)
    center = ImageOps.fit(
        rgb,
        image_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    contrast = ImageOps.autocontrast(center, cutoff=1)
    return [
        full,
        center,
        ImageOps.mirror(center),
        ImageOps.flip(center),
        contrast,
    ]


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    totals = values.sum(axis=1, keepdims=True)
    totals = np.where(totals <= 1e-12, 1.0, totals)
    return values / totals


def predict_image(image: Image.Image, crop_hint: str = ""):
    """
    Predict one image using real-world test-time augmentation (TTA).

    When crop_hint is provided, prediction is restricted to disease classes for
    that crop. This is especially useful for Google/field photographs because
    the supplied multi-crop model was trained as a joint crop+disease classifier
    and can otherwise make a cross-crop error when the background differs from
    the training dataset.
    """
    model, class_names, image_size, _metadata = _load_assets()
    views = _build_real_world_views(image, image_size)
    batch = np.stack(
        [np.asarray(view, dtype=np.float32) for view in views],
        axis=0,
    )

    # The supplied model already contains MobileNetV2 preprocessing.
    with _PREDICT_LOCK:
        view_probabilities = np.asarray(
            model.predict(batch, verbose=0), dtype=float
        )

    if view_probabilities.ndim != 2 or view_probabilities.shape[1] != len(class_names):
        raise RuntimeError(
            "Unexpected prediction output shape: "
            f"{tuple(view_probabilities.shape)}"
        )

    crop_names = [_class_crop(name) for name in class_names]
    normalized_hint = _canonical_crop(crop_hint)
    crop_hint_used = bool(normalized_hint)
    raw_crop_support = None

    if crop_hint_used:
        allowed_indices = [
            idx for idx, crop in enumerate(crop_names)
            if _canonical_crop(crop) == normalized_hint
        ]
        if not allowed_indices:
            supported = sorted(set(crop_names))
            raise ValueError(
                f"Unsupported crop selection: {crop_hint}. "
                f"Supported crops are: {', '.join(supported)}"
            )

        restricted = view_probabilities[:, allowed_indices]
        raw_crop_support = float(restricted.mean(axis=0).sum())
        restricted = _normalize_rows(restricted)
        averaged = restricted.mean(axis=0)
        local_best = int(np.argmax(averaged))
        best_index = int(allowed_indices[local_best])

        # Per-view winners inside the farmer/admin-selected crop.
        view_local_winners = np.argmax(restricted, axis=1)
        view_best_indices = np.asarray(
            [allowed_indices[int(i)] for i in view_local_winners], dtype=int
        )
        ranked_local = np.argsort(averaged)[::-1]
        ranked_indices = [allowed_indices[int(i)] for i in ranked_local]
        ranked_scores = [float(averaged[int(i)]) for i in ranked_local]
    else:
        averaged = view_probabilities.mean(axis=0)
        best_index = int(np.argmax(averaged))
        view_best_indices = np.argmax(view_probabilities, axis=1)
        ranked_indices = [int(i) for i in np.argsort(averaged)[::-1]]
        ranked_scores = [float(averaged[i]) for i in ranked_indices]

    predicted_class = class_names[best_index]
    crop_name, disease_name = split_class_name(predicted_class)
    confidence = float(ranked_scores[0] * 100.0)
    second_confidence = float(ranked_scores[1] * 100.0) if len(ranked_scores) > 1 else 0.0
    margin = max(0.0, confidence - second_confidence)

    selected_crop_key = _canonical_crop(crop_name)
    view_crop_agreement = float(np.mean([
        _canonical_crop(crop_names[int(index)]) == selected_crop_key
        for index in view_best_indices
    ]))
    view_class_agreement = float(np.mean(view_best_indices == best_index))

    top_predictions = []
    for index, score in zip(ranked_indices[:3], ranked_scores[:3]):
        class_name = class_names[int(index)]
        top_predictions.append({
            "class_name": class_name,
            "display_name": class_name
            .replace("___", " — ")
            .replace("__", " — ")
            .replace("_", " "),
            "confidence": round(float(score * 100.0), 2),
        })

    # A high softmax value alone is not enough for web/field photos. Mark the
    # result uncertain when transformed views disagree or the top two classes
    # are too close. This prevents many confidently wrong Google-image results
    # from being presented as a definitive diagnosis.
    uncertain_reasons = []
    if confidence < settings.LOW_CONFIDENCE_THRESHOLD:
        uncertain_reasons.append(
            f"confidence is below {settings.LOW_CONFIDENCE_THRESHOLD:.0f}%"
        )
    if margin < 7.0:
        uncertain_reasons.append("the top two disease scores are too close")
    if view_crop_agreement < 0.60:
        uncertain_reasons.append("the crop prediction changes across image views")
    if crop_hint_used and raw_crop_support is not None and raw_crop_support < 0.08:
        uncertain_reasons.append("the model has very weak raw support for the selected crop")

    if uncertain_reasons:
        ai_status = "uncertain"
    elif "healthy" in disease_name.lower():
        ai_status = "healthy"
    else:
        ai_status = "disease"

    if crop_hint_used:
        support_text = (
            f" Raw model support for this crop was {raw_crop_support * 100:.1f}%."
            if raw_crop_support is not None else ""
        )
        prediction_note = (
            f"Real-world mode used 5 transformed views and restricted the model "
            f"to {crop_name} disease classes because that crop was selected before upload."
            f"{support_text} View agreement for the final class was "
            f"{view_class_agreement * 100:.0f}%."
        )
    else:
        prediction_note = (
            "Real-world mode averaged 5 transformed views. "
            f"Crop agreement was {view_crop_agreement * 100:.0f}% and the "
            f"top-two margin was {margin:.1f} percentage points. "
            "For Google or field photos, selecting the known crop before upload "
            "usually gives safer results than Auto-detect."
        )

    if uncertain_reasons:
        prediction_note += " Needs expert review because " + "; ".join(uncertain_reasons) + "."

    return {
        "predicted_class": predicted_class,
        "crop_name": crop_name,
        "disease_name": disease_name,
        "confidence": round(confidence, 2),
        "top_predictions": top_predictions,
        "ai_status": ai_status,
        "robustness": {
            "crop_hint": crop_name if crop_hint_used else "",
            "crop_hint_used": crop_hint_used,
            "raw_crop_support": (
                round(raw_crop_support * 100.0, 2)
                if raw_crop_support is not None else None
            ),
            "view_crop_agreement": round(view_crop_agreement * 100.0, 2),
            "view_class_agreement": round(view_class_agreement * 100.0, 2),
            "margin": round(margin, 2),
            "note": prediction_note,
        },
    }

