from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, EmailSenderDep
from app.schemas.notification import TestEmailResult
from app.services.notification_service import EmailDisabledError, NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/test", response_model=TestEmailResult)
def send_test_email(current_user: CurrentUser, sender: EmailSenderDep) -> TestEmailResult:
    try:
        message = NotificationService(sender).send_test_email(current_user)
    except EmailDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email is disabled"
        ) from exc
    return TestEmailResult(sent=True, to=message.to, provider=sender.provider)
