IMPORTANT — UPDATED 161-CLASS MODEL
===================================

1. Run setup_windows.bat
2. Run install_updated_model_labels_windows.bat
3. Select the class_names.json from the SAME training run as the attached
   plant_disease_model(2).keras, or, only if the model was trained with image_dataset_from_directory using its default class order, select the exact training dataset folder.
4. Wait for: Model check passed: 161 classes
5. Run run_windows.bat

The previous 38-class class_names.json is not used because it would make
prediction names incorrect.

CROPCARE AI — ADMIN-MANAGED FARMER ACCOUNTS
============================================

1. Extract the complete ZIP.
2. Double-click setup_windows.bat.
3. When prompted, create the mandatory administrator username and password.
4. Double-click run_windows.bat.
5. Open http://127.0.0.1:8000/
6. Sign in as administrator.
7. Open Register farmer and create the farmer username and password.
8. Log out. The farmer can now sign in with the credentials created by admin.

There is no public farmer registration button or public registration process.
Only a logged-in Django superuser can register farmers.

For an existing Fixed v2 installation, read UPGRADE_FROM_V2.txt.
