# Supabase disabled — stub implementations so the rest of the app runs unchanged.

import os

PROJECT_NAME = os.getenv("PROJECT_NAME", "My Project")
PM_PHONE = os.getenv("PM_PHONE", "")  # optional: set in .env to forward reports to PM


def get_project_by_engineer(phone: str) -> dict | None:
    """Return a default project for any engineer phone."""
    return {
        "id": "local",
        "name": PROJECT_NAME,
        "pm_phone": PM_PHONE or None,
    }


def upload_pdf(file_path: str, project_id: str, date: str) -> str:
    """No-op — returns empty string (PDF sent as local file path instead)."""
    print(f"[supabase] DISABLED — skipping upload of {file_path}")
    return ""


def save_report(project_id: str, engineer_phone: str, report_data: dict, pdf_url: str) -> None:
    """No-op."""
    print("[supabase] DISABLED — skipping DB insert")
