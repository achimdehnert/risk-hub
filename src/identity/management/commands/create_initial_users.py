"""Create initial superuser and staff user."""

from django.core.management.base import BaseCommand

from identity.models import User


class Command(BaseCommand):
    help = "Create initial admin (superuser) and achim (staff) users"

    def handle(self, *args, **options):
        # Superuser
        if not User.objects.filter(username="admin").exists():
            u = User.objects.create_superuser(
                "admin", "admin@schutztat.de", "Schutztat2026!",
            )
            u.first_name = "System"
            u.last_name = "Admin"
            u.save()
            self.stdout.write(self.style.SUCCESS(
                "Created superuser: admin / Schutztat2026!",
            ))
        else:
            self.stdout.write("Superuser 'admin' already exists")

        # Staff user
        if not User.objects.filter(username="achim").exists():
            u = User.objects.create_user(
                "achim", "achim@schutztat.de", "Schutztat2026!",
            )
            u.first_name = "Achim"
            u.last_name = "Dehnert"
            u.is_staff = True
            u.save()
            self.stdout.write(self.style.SUCCESS(
                "Created staff user: achim / Schutztat2026!",
            ))
        else:
            self.stdout.write("Staff user 'achim' already exists")

        self.stdout.write(self.style.SUCCESS("Done."))
