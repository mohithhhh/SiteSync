# SiteSync — Construction Site Daily Report Generator

A WhatsApp bot for site engineers: send a voice note → get a professional PDF report back in seconds.

```
Engineer sends voice note on WhatsApp
          ↓
Twilio webhook → FastAPI
          ↓
Gemini 1.5 Pro (transcribe + extract JSON — one API call)
          ↓
WeasyPrint + Jinja2 → PDF
          ↓
Supabase Storage (upload) + DB (save record)
          ↓
Twilio sends PDF back to engineer + PM via WhatsApp
```

---

## Setup

### 1. Clone & install dependencies

```bash
pip install -r requirements.txt
```

> **WeasyPrint** requires system libraries. On macOS: `brew install pango libffi`. On Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0`.

### 2. Fill in `.env`

```
GEMINI_API_KEY=           # Google AI Studio → https://aistudio.google.com/app/apikey
TWILIO_ACCOUNT_SID=       # Twilio console
TWILIO_AUTH_TOKEN=        # Twilio console
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number (or your approved number)
SUPABASE_URL=             # Supabase project URL
SUPABASE_KEY=             # Supabase service_role key (anon key works for dev)
```

### 3. Create Supabase tables

Run this SQL in your Supabase SQL editor:

```sql
-- Projects table
create table projects (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  pm_phone         text,               -- e.g. +919876543210
  pm_email         text,
  engineer_phones  text[],             -- array of WhatsApp numbers e.g. {+919999000001}
  created_at       timestamptz default now()
);

-- Reports table
create table reports (
  id               uuid primary key default gen_random_uuid(),
  project_id       uuid references projects(id),
  engineer_phone   text,
  date             date,
  transcript_raw   text,
  report_json      jsonb,
  pdf_url          text,
  workers_total    int,
  issues_count     int,
  created_at       timestamptz default now()
);
```

### 4. Create Supabase Storage bucket

In Supabase Dashboard → Storage → New bucket:
- Name: `site-reports`
- Public: **enabled** (so PDF URLs are directly accessible)

### 5. Twilio WhatsApp Sandbox

1. Go to [Twilio Console → Messaging → Try it out → WhatsApp](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. Connect your phone to the sandbox (send the join code)
3. Set the **"When a message comes in"** webhook URL to your ngrok URL:
   ```
   https://<your-ngrok-id>.ngrok.io/webhook/whatsapp
   ```
   Method: `POST`

---

## Running locally

### Start the server

```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

### Expose with ngrok

```bash
ngrok http 8000
```

Copy the `https://` URL → paste into Twilio sandbox webhook settings (step 5 above).

---

## Onboarding a new project

Insert a row into the `projects` table manually (Supabase Table Editor or SQL):

```sql
insert into projects (name, pm_phone, pm_email, engineer_phones)
values (
  'Whitefield Apartment Block A',
  '+919876543210',
  'pm@company.com',
  array['+919999000001', '+919999000002']
);
```

Once inserted, any engineer whose number is in `engineer_phones` can send a voice note and their reports will automatically link to this project and be forwarded to the PM.

---

## Sample voice note for testing

Send this (or a recording of it) as a WhatsApp voice note:

> **"Aaj site pe 12 mason aur 8 helper aaye. Kaam mein ground floor ki column casting complete hui. 40 bags cement aaya Ramesh supplier se. Kal footing excavation karenge block B mein. Koi issue nahi aaj."**

Expected extracted output:
```json
{
  "date": "<today's date>",
  "weather": null,
  "workers_present": { "mason": 12, "helper": 8, "total": 20, "electrician": 0, "plumber": 0, "carpenter": 0, "other": 0 },
  "work_completed": ["Ground floor column casting completed"],
  "materials_received": ["40 bags cement from Ramesh supplier"],
  "materials_used": [],
  "issues_flagged": [],
  "next_day_plan": ["Footing excavation in Block B"],
  "visitors": null,
  "notes": null
}
```

---

## Project structure

```
construction-voice-report/
├── main.py                # FastAPI app + /webhook/whatsapp endpoint
├── gemini_processor.py    # Download audio → Gemini 1.5 Pro → structured JSON
├── pdf_generator.py       # Jinja2 HTML → WeasyPrint PDF
├── supabase_client.py     # DB queries + Storage upload
├── whatsapp_sender.py     # Twilio send message + media
├── templates/
│   └── report.html        # PDF template (orange accent, professional layout)
├── .env                   # Secrets (never commit this)
├── requirements.txt
└── README.md
```

---

## Error handling

| Situation | Bot response |
|-----------|-------------|
| Non-audio message received | "Please send a voice note" |
| Gemini fails to parse JSON | "Could not process your voice note. Please try again." |
| Engineer phone not in any project | "Your number is not registered. Contact your site manager." |
| Any unhandled exception | "An unexpected error occurred. Please try again later." |

All webhook responses return HTTP 200 to prevent Twilio from retrying.

---

## Architecture notes

- **One Gemini API call** handles both transcription and JSON extraction (no Whisper needed).
- **Async throughout** — `httpx.AsyncClient` for downloading audio, `async def` endpoints.
- **WeasyPrint** renders the Jinja2 HTML template string directly via `HTML(string=...).write_pdf()`.
- **Supabase upsert** on storage upload means repeated reports for the same date/project overwrite cleanly.
