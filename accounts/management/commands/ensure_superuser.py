import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create superuser from env vars if it doesn't exist"

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not password:
            self.stdout.write("DJANGO_SUPERUSER_PASSWORD not set, skipping")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists")
            return
        User.objects.create_superuser(username=username, password=password)
        self.stdout.write(f"Superuser '{username}' created")
