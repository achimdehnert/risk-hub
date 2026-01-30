from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI

from actions.api import router as actions_router
from config.api_auth import ApiKeyAuth
from documents.api import router as documents_router
from risk.api import router as risk_router


api = NinjaAPI(
    title="risk-hub API",
    version="1.0.0",
    auth=ApiKeyAuth(),
)

api.add_router("/risk", risk_router)
api.add_router("/documents", documents_router)
api.add_router("/actions", actions_router)


@api.get("/health", auth=None, tags=["system"])
def health(request: HttpRequest) -> dict[str, Any]:
    return {"status": "ok"}
