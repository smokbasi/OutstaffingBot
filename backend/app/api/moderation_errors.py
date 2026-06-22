from fastapi.responses import JSONResponse

from app.schemas.moderation import ContentRejectedResponse
from app.services.content_moderation_service import CONTENT_REJECTED_MESSAGE, ContentRejectedError


def content_rejected_response(exc: ContentRejectedError) -> JSONResponse:
    body = ContentRejectedResponse(
        detail=CONTENT_REJECTED_MESSAGE,
        code="content_rejected",
        field=exc.violation.field,
    )
    return JSONResponse(status_code=400, content=body.model_dump(mode="json"))
