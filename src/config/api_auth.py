import hashlib
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja.security import HttpBearer

from common.context import set_db_tenant, set_tenant, set_user_id
from identity.models import ApiKey


class ApiKeyAuth(HttpBearer):
    def authenticate(
        self,
        request: HttpRequest,
        token: str,
    ) -> dict[str, UUID] | None:
        if not token:
            return None

        key_prefix = token[:16]
        key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        api_key = ApiKey.objects.filter(
            key_prefix=key_prefix,
            key_hash=key_hash,
            revoked_at__isnull=True,
        ).select_related("user").first()

        if api_key is None:
            return None

        set_tenant(api_key.tenant_id, None)
        set_db_tenant(api_key.tenant_id)
        set_user_id(api_key.user_id)

        ApiKey.objects.filter(id=api_key.id).update(
            last_used_at=timezone.now(),
        )

        return {"tenant_id": api_key.tenant_id, "user_id": api_key.user_id}
