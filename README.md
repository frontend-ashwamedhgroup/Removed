# UPDATED MODEL (3) — 161-CLASS REAL-WORLD BUILD

This build contains the newly supplied **plant_disease_model(3).keras**. It expects **224×224 RGB** input and has **161 softmax outputs**. The model was saved with Keras 3.15.0 on 11 Aug 2026.

The supplied model (3) is byte-for-byte identical to the previously supplied model (2), so the **same correct 161-class `class_names.json`** must be reused. Its SHA-256 is `dd227e1499204252cc0e44dfa0dcf75142d7ba87c7f8ee8bf919087bc8c0f26d`.

**Important:** the original v4 Real-World project had a 38-class JSON mapping. Do not use that old 38-class file with this 161-output model. If you already have the working 161-class JSON used with model (2), copy it to `ml_models/class_names.json`. Otherwise use `install_updated_model_labels_windows.bat` to install the exact 161-class mapping from your training JSON or exact training dataset folder.

The project refuses to start diagnosis when the label count does not equal the model output count. This prevents silent disease-name/index mismatches.

---

# CropCare AI — Fixed v3 with Administrator-Managed Farmer Accounts

A Django plant-disease farmer–expert portal built around the supplied MobileNetV2 Keras model. The main administrator controls farmer registration. Farmers cannot register themselves from the public website.

## Main change requested in v3

- An active Django **superuser administrator is mandatory**.
- Public farmer self-registration has been removed.
- Only a logged-in superuser can open **Register farmer**.
- The administrator creates the farmer's username, password and profile.
- Creating a farmer keeps the administrator logged in; it does not switch the session to the new farmer.
- Farmers sign in using credentials provided by the administrator.
- Staff reviewers can review diagnoses, but only the main superuser can register farmers.
- A dedicated administrator dashboard shows farmer, diagnosis and pending-review counts.
- `run_windows.bat` checks for an active administrator and will not start the server without one.

## Fixes retained from Fixed v2

- Keras 3.15 model compatibility handling for the deserialization error shown in Query 1–3.
- `keras==3.15.0` and the supplied model's trained weights.
- Automatic MobileNetV2 weights-only loading fallback.
- `python manage.py check_model` model/inference health check.
- **Choose files** and **Choose folder** controls on the same diagnosis page.
- Individual files and an entire folder can be submitted together.
- Default source-file limit of 500 and per-file limit of 100 MB.
- Concise model errors instead of a multi-page configuration dump.

## Included features

- Administrator-controlled farmer account creation.
- Administrator/farmer login through one secure login page.
- Farmer profile, dashboard and diagnosis history.
- Multiple individual files and complete-folder upload.
- Supported images: JPG, JPEG, PNG, WEBP, BMP, GIF, TIFF/TIF.
- Multi-page PDF processing.
- ZIP batch processing.
- Embedded-image extraction from DOCX and PPTX.
- Exact 224×224 RGB input expected by the supplied model.
- Exact model/label count validation; this updated model requires **161 labels** in `ml_models/class_names.json`.
- Top-three predictions and confidence scores.
- Healthy, disease, uncertain and processing-error states.
- Disease guidance and administrator/expert review workflow.
- CSV export for every diagnosis batch.
- SQLite by default and optional PostgreSQL through `DATABASE_URL`.
- Professional responsive classic-style interface.

## Important safety limitation

The result is AI screening, not a guaranteed diagnosis. Similar diseases, nutrient deficiencies, pesticide injury, lighting and background can affect predictions. Product selection, dose, pre-harvest interval and application method must follow the locally registered product label and advice from a qualified agriculture officer.

## Model details

- Architecture: MobileNetV2 transfer learning.
- Input shape: 224 × 224 × 3.
- Output: **161 softmax classes**.
- Model: `ml_models/plant_disease_model.keras`.
- Labels: `ml_models/class_names.json`.
- Training notebook: `notebooks/Plant_Disease_Model_Training.ipynb`.

The JSON file maps model output positions to disease names. Reuse the same correct **161-class** JSON used with model (2); the old 38-class mapping must not be used.

## First-time Windows installation

Use 64-bit Python 3.11.

1. Extract the ZIP.
2. Double-click `setup_windows.bat`.
3. When the setup reports that no administrator exists, enter the mandatory superuser username, email and password.
4. Double-click `run_windows.bat`.
5. Open `http://127.0.0.1:8000/`.
6. Sign in using the administrator credentials.
7. Select **Register farmer**.
8. Create the farmer username and password and give those credentials securely to the farmer.

The server-start script checks both the administrator account and the AI model. No default or hard-coded administrator password is included.

To create another superuser later, double-click:

```text
create_admin_windows.bat
```

## Upgrade from CropCare AI Fixed v2 without losing data

1. Stop the old server with `Ctrl+C`.
2. Extract this v3 ZIP into a new folder.
3. Copy `db.sqlite3` from the old project into this project.
4. Copy the old `media` folder into this project.
5. Do not copy the old `venv` folder.
6. Double-click `repair_environment.bat`.
7. Double-click `run_windows.bat`.
8. Sign in using the existing superuser account.

No database migration is required specifically for the registration change because no database field was changed.

## Account workflows

### Main administrator

1. Sign in on the normal login page.
2. Open **Admin dashboard**.
3. Select **Register farmer**.
4. Enter farmer details, username and a unique password.
5. Submit the form.
6. Stay logged in as administrator and register additional farmers as needed.
7. Open **Review queue** to confirm or correct diagnoses and publish guidance.

### Farmer

1. Obtain username and password from the administrator.
2. Sign in on the normal login page.
3. Open **New diagnosis**.
4. Choose individual files, a complete folder, or both.
5. Submit and view every image/page result.
6. Return later to view administrator-reviewed guidance.

### Staff agriculture reviewer

A staff account can open the review queue but cannot register farmers unless it is also a Django superuser.

## Uploading files and folders

The farmer can use both controls in one submission:

- **Choose files**: select one or many individual files.
- **Choose folder**: select a complete folder. Supported files from that folder and its subfolders are uploaded by the browser.

The page shows the combined file total before processing.

## Default upload limits

- 500 source files per batch.
- 100 MB per uploaded source file.
- 200 extracted images/pages from one source file.
- 500 total extracted image/page results per batch.
- 500 ZIP members.
- 500 MB uncompressed ZIP limit.
- 1,000 multipart file entries accepted by Django.

These values can be changed with environment variables documented in `plant_disease_portal/settings.py` and `.env.example`.

## Health-check commands

```bat
venv\Scripts\activate
python manage.py check_admin
python manage.py check_model
```

`check_admin` succeeds only when at least one active Django superuser exists. `check_model` validates the **161 labels**, 224×224 model input and a test inference.

## Project structure

```text
CropCare_AI_Fixed_v3_Admin_Managed/
├── manage.py
├── requirements.txt
├── setup_windows.bat
├── repair_environment.bat
├── create_admin_windows.bat
├── run_windows.bat
├── UPGRADE_FROM_V2.txt
├── plant_disease_portal/
├── diagnosis/
│   ├── management/commands/check_admin.py
│   ├── management/commands/check_model.py
│   ├── services/model_service.py
│   └── services/file_extractors.py
├── ml_models/
│   ├── plant_disease_model.keras
│   └── class_names.json
├── notebooks/
└── media/
```

## Deployment note

On Railway or another hosted platform, create the first superuser after migrations with an interactive shell or a secure deployment process. Do not place a permanent administrator password in source control or environment files. Use PostgreSQL and persistent media storage for production deployment.

## Active navigation update (v4)

The main navigation now highlights only the currently open page. This applies to Home, Admin dashboard, Register farmer, Review queue and Django admin. The same current-page behavior is also used for farmer navigation.


## Permanent farmer password display update

The password entered by the superuser while registering a farmer is permanently
available in the **Recently registered farmers** table. Django's normal one-way
password hash is still used for login; a separate encrypted copy is kept for
administrator retrieval. Passwords are not stored as plain text.

Keep `DJANGO_SECRET_KEY` private and unchanged. Changing it makes previously
stored encrypted farmer passwords unreadable. Farmers created before this update
will display **Not stored (farmer registered before this update)**.

After upgrading an existing database, run:

```bat
python manage.py migrate
```


## Real-world / Google image prediction mode

This build adds a **Crop type** selector to New diagnosis. For a known crop, select it before uploading Google or field photographs. The model then compares only disease classes belonging to that crop. Auto-detect remains available for mixed-crop batches.

Inference also averages five transformed views and marks unstable predictions as **Needs review** instead of presenting them as certain. This improves robustness but does not replace retraining on representative real-world field data.
