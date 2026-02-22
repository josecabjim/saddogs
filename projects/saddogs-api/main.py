import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
TABLE_NAME = "census"

supabase = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)

app = FastAPI()


def fetch_data():
    resp = supabase.table(TABLE_NAME).select("*").execute()
    print("status:", getattr(resp, "status_code", None))
    print("error:", getattr(resp, "error", None))
    print("data:", getattr(resp, "data", None))
    return resp.data


def make_ascii_table(rows):
    if not rows:
        return "No data"

    headers = list(rows[0].keys())

    widths = {h: max(len(str(h)), max(len(str(r[h])) for r in rows)) for h in headers}

    def row_line(row):
        return "| " + " | ".join(str(row[h]).ljust(widths[h]) for h in headers) + " |"

    divider = "+-" + "-+-".join("-" * widths[h] for h in headers) + "-+"

    lines = [divider]
    lines.append(row_line({h: h for h in headers}))
    lines.append(divider)

    for r in rows:
        lines.append(row_line(r))

    lines.append(divider)
    return "\n".join(lines)


@app.get("/", response_class=HTMLResponse)
def homepage():
    data = fetch_data()
    table = make_ascii_table(data)

    return f"""
    <html>
        <body>
            <h2>Database Data</h2>
            <pre>{table}</pre>
        </body>
    </html>
    """
