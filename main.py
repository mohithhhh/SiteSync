import os
import json
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

import gemini_processor
import pdf_generator
import supabase_client
import whatsapp_sender

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI(title="SiteSync - Construction Report Bot")


@app.get("/")
async def health():
    return {"status": "ok", "service": "SiteSync"}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    MediaContentType0: str = Form(default=""),
    MediaUrl0: str = Form(default=""),
    NumMedia: str = Form(default="0"),
):
    """
    Twilio WhatsApp webhook.
    Always returns HTTP 200 to prevent Twilio retries.
    """
    sender_phone = From.replace("whatsapp:", "")

    try:
        # ── 1. Validate media type ──────────────────────────────────────────
        if "audio" not in MediaContentType0.lower() or not MediaUrl0:
            whatsapp_sender.send_text(
                sender_phone,
                "🎙️ Please send a *voice note* with your daily site update.",
            )
            return PlainTextResponse("ok", status_code=200)

        # ── 2. Transcribe + extract structured data via Gemini ──────────────
        print(f"[main] Processing voice note from {sender_phone}")
        try:
            report_data = await gemini_processor.process_voice_to_report(
                audio_url=MediaUrl0,
                twilio_sid=TWILIO_SID,
                twilio_token=TWILIO_TOKEN,
            )
        except Exception as e:
            print(f"[main] Gemini processing failed: {e}")
            whatsapp_sender.send_text(
                sender_phone,
                "⚠️ Could not process your voice note. Please try again or speak more clearly.",
            )
            return PlainTextResponse("ok", status_code=200)

        # ── 3. Lookup project ───────────────────────────────────────────────
        project = supabase_client.get_project_by_engineer(sender_phone)
        if not project:
            whatsapp_sender.send_text(
                sender_phone,
                "❌ Your number is not registered. Please contact your site manager.",
            )
            return PlainTextResponse("ok", status_code=200)

        project_id = project["id"]
        project_name = project.get("name", "Unknown Project")
        pm_phone = project.get("pm_phone")

        # ── 4. Generate PDF ─────────────────────────────────────────────────
        pdf_path = pdf_generator.generate_pdf(
            report_data=report_data,
            project_name=project_name,
            engineer_phone=sender_phone,
        )

        # ── 5. Upload PDF to storage (no-op when Supabase is disabled) ─────────
        date_str = report_data.get("date") or "unknown-date"
        pdf_url = supabase_client.upload_pdf(
            file_path=pdf_path,
            project_id=project_id,
            date=date_str,
        )
        # Fall back to local file path so the sender can still attach it
        effective_pdf = pdf_url or pdf_path

        # ── 6. Save report record to DB (no-op when Supabase is disabled) ───
        supabase_client.save_report(
            project_id=project_id,
            engineer_phone=sender_phone,
            report_data=report_data,
            pdf_url=pdf_url,
        )

        # ── 7. Send PDF back to engineer ────────────────────────────────────
        whatsapp_sender.send_report(
            to_phone=sender_phone,
            pdf_url=effective_pdf,
            report_data=report_data,
        )

        # ── 8. Send PDF to PM ───────────────────────────────────────────────
        if pm_phone:
            whatsapp_sender.send_report(
                to_phone=pm_phone,
                pdf_url=effective_pdf,
                report_data=report_data,
            )

        print(f"[main] Report flow complete for {sender_phone}, project={project_name}")

    except Exception as e:
        print(f"[main] Unhandled error for {sender_phone}: {e}")
        try:
            whatsapp_sender.send_text(
                sender_phone,
                "⚠️ An unexpected error occurred. Please try again later.",
            )
        except Exception:
            pass

    # Always return 200 to Twilio
    return PlainTextResponse("ok", status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
