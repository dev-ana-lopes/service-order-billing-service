from fastapi import APIRouter
from starlette.responses import Response

from ....infrastructure.observability.metrics import metrics_response

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def get_metrics() -> Response:
    return metrics_response()
