from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Verify that at least one active Django superuser administrator exists.'

    def handle(self, *args, **options):
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True, is_active=True)
        if not admins.exists():
            raise CommandError(
                'No active administrator exists. Run: python manage.py createsuperuser'
            )
        usernames = ', '.join(admins.values_list('username', flat=True))
        self.stdout.write(self.style.SUCCESS(f'Administrator check passed: {usernames}'))
