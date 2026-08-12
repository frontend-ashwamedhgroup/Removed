from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("diagnosis", "0002_farmerprofile_encrypted_login_password")]

    operations = [
        migrations.AddField(
            model_name="diagnosisbatch",
            name="crop_hint",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
