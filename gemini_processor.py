import os
import json
import tempfile
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

EXTRACTION_PROMPT = """
You are a construction site report assistant for Indian construction sites.
This is a voice note from a site engineer giving their daily update.
Audio may be Hindi, Kannada, English, or mixed Hinglish.

Extract ALL information into this exact JSON. Return ONLY raw JSON, no markdown, no backticks.

{
  "date": "YYYY-MM-DD or null",
  "weather": "clear/cloudy/rainy/hot or null",
  "workers_present": {
    "mason": 0, "helper": 0, "electrician": 0,
    "plumber": 0, "carpenter": 0, "other": 0, "total": 0
  },
  "work_completed": [],
  "materials_received": [],
  "materials_used": [],
  "issues_flagged": [],
  "next_day_plan": [],
  "visitors": null,
  "notes": null
}

Rules:
- "15 log aaye" → total workers = 15
- "aaj kuch kaam nahi hua" → work_completed = ["No work done today"]
- Missing fields → null for strings, 0 for numbers, [] for arrays
- Translate everything to English in the output
"""


async def process_voice_to_report(audio_url: str, twilio_sid: str, twilio_token: str) -> dict:
    tmp_path = None
    gemini_file = None

    try:
        # Download audio from Twilio with basic auth
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, auth=(twilio_sid, twilio_token), follow_redirects=True)
            response.raise_for_status()
            audio_bytes = response.content

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Upload to Gemini Files API
        gemini_file = genai.upload_file(tmp_path, mime_type="audio/ogg")

        # Call Gemini 1.5 Pro with the audio file and extraction prompt
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content([EXTRACTION_PROMPT, gemini_file])

        raw_text = response.text.strip()

        # Strip any markdown fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        report_data = json.loads(raw_text)
        return report_data

    finally:
        # Clean up Gemini uploaded file
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
            except Exception as e:
                print(f"Warning: Could not delete Gemini file: {e}")

        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file: {e}")
