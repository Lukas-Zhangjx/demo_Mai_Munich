import os
import imaplib
import email
from email.header import decode_header
from typing import List


MAX_FETCH = 10   # max emails to fetch per call


def fetch_unread_emails() -> List[dict]:
    """
    Connect to Gmail via IMAP and fetch unread emails from inbox.
    Marks fetched emails as read.
    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in env.
    """
    gmail_address  = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(gmail_address, gmail_password)
        imap.select("INBOX")

        _, message_ids = imap.search(None, "UNSEEN")
        ids = message_ids[0].split()[-MAX_FETCH:]  # latest N unread

        emails = []
        for msg_id in ids:
            _, data = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            emails.append({
                "id":      msg_id.decode(),
                "from":    _decode_header(msg.get("From", "")),
                "subject": _decode_header(msg.get("Subject", "(no subject)")),
                "date":    msg.get("Date", ""),
                "body":    _extract_body(msg),
            })

            # Mark as read
            imap.store(msg_id, "+FLAGS", "\\Seen")

    return emails


def _decode_header(value: str) -> str:
    """Decode RFC2047-encoded email headers."""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg) -> str:
    """Extract plain-text body from a possibly multipart email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="ignore")
    return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
