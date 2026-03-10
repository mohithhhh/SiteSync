import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

_twilio = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN"),
)
FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def _ensure_whatsapp_prefix(phone: str) -> str:
    if not phone.startswith("whatsapp:"):
        return f"whatsapp:{phone}"
    return phone


def send_report(to_phone: str, pdf_url: str, report_data: dict) -> None:
    """Send the PDF report summary + attachment to a WhatsApp number."""
    to = _ensure_whatsapp_prefix(to_phone)

    date = report_data.get("date", "N/A")
    workers_total = report_data.get("workers_present", {}).get("total", 0)
    work_completed = report_data.get("work_completed", [])
    issues = report_data.get("issues_flagged", [])

    if issues:
        issues_line = f"⚠️ Issues: {len(issues)} flagged"
    else:
        issues_line = "✅ No issues"

    body = (
        f"📋 *Daily Site Report*\n"
        f"Date: {date}\n"
        f"👷 Workers: {workers_total}\n"
        f"✅ Tasks: {len(work_completed)}\n"
        f"{issues_line}\n\n"
        f"Full report 👇"
    )

    # Only attach as media if it's a real public URL (not a local path or empty)
    is_public_url = pdf_url and pdf_url.startswith("http")
    create_kwargs = dict(from_=FROM, to=to, body=body)
    if is_public_url:
        create_kwargs["media_url"] = [pdf_url]

    try:
        _twilio.messages.create(**create_kwargs)
        print(f"[whatsapp] Report sent to {to_phone}")
    except Exception as e:
        print(f"[whatsapp] Failed to send to {to_phone}: {e}")
        raise


def send_text(to_phone: str, message: str) -> None:
    """Send a plain text WhatsApp message (for error/info notifications)."""
    to = _ensure_whatsapp_prefix(to_phone)
    try:
        _twilio.messages.create(from_=FROM, to=to, body=message)
    except Exception as e:
        print(f"[whatsapp] Failed to send text to {to_phone}: {e}")
