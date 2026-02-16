from fastapi import APIRouter

from .routes_status import router as status_router
from .routes_command import router as command_router
from .routes_approvals import router as approvals_router
from .routes_logs import router as logs_router
from .routes_runs import router as runs_router
from .webhooks_facebook import router as facebook_webhook_router
from .webhooks_whatsapp import router as whatsapp_webhook_router


def build_api_router() -> APIRouter:
    router = APIRouter()

    # Core API
    router.include_router(status_router)
    router.include_router(command_router)
    router.include_router(approvals_router)
    router.include_router(logs_router)
    router.include_router(runs_router)

    # Webhooks
    router.include_router(facebook_webhook_router)
    router.include_router(whatsapp_webhook_router)

    return router


api_router = build_api_router()
