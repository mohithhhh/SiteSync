import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Resolve templates directory relative to this file
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def generate_pdf(report_data: dict, project_name: str, engineer_phone: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("report.html")

    generated_at = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")

    html_string = template.render(
        report=report_data,
        project_name=project_name,
        engineer_phone=engineer_phone,
        generated_at=generated_at,
    )

    date_str = report_data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    # Sanitize phone for filename
    safe_phone = engineer_phone.replace("+", "").replace(":", "").replace(" ", "")
    output_path = f"/tmp/report_{date_str}_{safe_phone}.pdf"

    HTML(string=html_string).write_pdf(output_path)

    return output_path
