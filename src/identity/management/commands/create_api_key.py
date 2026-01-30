import hashlib
import secrets
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from identity.models import ApiKey


class Command(BaseCommand):
    help = "Create an API key for a user"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--tenant-id", required=False)
        parser.add_argument("--name", required=False, default="")

    def handle(self, *args, **options):
        username: str = options["username"]
        name: str = options["name"]
        tenant_id_raw: str | None = options.get("tenant_id")

        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"Unknown user: {username}")

        if tenant_id_raw:
            tenant_id = UUID(tenant_id_raw)
        else:
            tenant_id = getattr(user, "tenant_id", None)

        if tenant_id is None:
            raise CommandError(
                "tenant_id required (user has no tenant_id and "
                "--tenant-id not set)"
            )

        token = secrets.token_urlsafe(32)
        key_prefix = token[:16]
        key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        ApiKey.objects.create(
            tenant_id=tenant_id,
            user_id=user.id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )

        self.stdout.write(self.style.SUCCESS("API key created"))
        self.stdout.write(f"Token: {token}")
        self.stdout.write(
            "Store this token securely. It will not be shown again."
        )
