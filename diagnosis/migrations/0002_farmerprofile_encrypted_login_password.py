from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('diagnosis', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmerprofile',
            name='encrypted_login_password',
            field=models.TextField(blank=True, editable=False),
        ),
    ]
