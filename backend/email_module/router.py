from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import verify_token
from email_module.sender   import send_email
from email_module.receiver import fetch_unread_emails


router = APIRouter(prefix="/api/email", tags=["email"])


class SendRequest(BaseModel):
    to:      str
    subject: str
    body:    str


@router.post("/send")
def send(_body: SendRequest, _: str = Depends(verify_token)):
    """Send an email. Requires admin JWT."""
    return send_email(_body.to, _body.subject, _body.body)


@router.get("/fetch")
def fetch(_: str = Depends(verify_token)):
    """Fetch unread emails from inbox. Requires admin JWT."""
    return {"emails": fetch_unread_emails()}
