import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from supabase import create_client
import json

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
CENSUS_TABLE = "census"
RESCUES_TABLE = "rescues"

supabase = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
app = FastAPI()


# -------------------------
# Fetch data from Supabase
# -------------------------
def fetch_data(table_name):
    resp = (
        supabase.table(table_name)
        .select("*")
        .order("created_at", desc=False)  # Changed ascending=True to desc=False
        .execute()
    )
    return resp.data or []


# -------------------------
# Convert census rows to chart data
# -------------------------
def rows_to_chart_data(rows):
    if not rows:
        return [], {}
    seen_dates = set()
    filtered_rows = []
    for r in rows:
        date_only = r["created_at"][:10]
        if date_only not in seen_dates:
            filtered_rows.append(r)
            seen_dates.add(date_only)
    labels = [r["created_at"][:10] for r in filtered_rows]
    skip_cols = {"id", "created_at"}
    numeric_cols = [c for c in filtered_rows[0].keys() if c not in skip_cols]
    datasets = {col: [r[col] for r in filtered_rows] for col in numeric_cols}
    datasets["Total"] = [sum(r[col] for col in numeric_cols) for r in filtered_rows]
    return labels, datasets


# -------------------------
# Convert rescues table rows to chart data
# -------------------------
def rescues_rows_to_chart_data(rows):
    if not rows:
        return [], {}
    seen_dates = set()
    filtered_rows = []
    for r in rows:
        date_only = r["created_at"][:10]
        if date_only not in seen_dates:
            filtered_rows.append(r)
            seen_dates.add(date_only)
    labels = [r["created_at"][:10] for r in filtered_rows]
    islands = list({r["island"] for r in filtered_rows})
    datasets = {island: [] for island in islands}
    for r in filtered_rows:
        for island in islands:
            datasets[island].append(r["total_dogs"] if r["island"] == island else 0)
    datasets["Total"] = [sum(r["total_dogs"] for r in filtered_rows)]
    return labels, datasets


# -------------------------
# ASCII table
# -------------------------
def make_ascii_table(rows):
    if not rows:
        return "No data"
    headers = list(rows[0].keys())
    widths = {h: max(len(str(h)), max(len(str(r[h])) for r in rows)) for h in headers}

    def row_line(row):
        return "| " + " | ".join(str(row[h]).ljust(widths[h]) for h in headers) + " |"

    divider = "+-" + "-+-".join("-" * widths[h] for h in headers) + "-+"
    lines = [divider, row_line({h: h for h in headers}), divider]
    for r in rows:
        lines.append(row_line(r))
    lines.append(divider)
    return "\n".join(lines)


# -------------------------
# Homepage
# -------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    data = fetch_data(CENSUS_TABLE)
    table = make_ascii_table(data)
    return f"""
    <html>
        <body style="font-family: Arial; margin: 40px;">
            <h2>Database Data</h2>
            <pre>{table}</pre>
            <p>
                <a href="/graph">Census Graph</a> | 
                <a href="/graph-rescues">Rescues Graph</a>
            </p>
        </body>
    </html>
    """


# -------------------------
# Census Graph
# -------------------------
@app.get("/graph", response_class=HTMLResponse)
def graph_page():
    rows = fetch_data(CENSUS_TABLE)
    labels, datasets = rows_to_chart_data(rows)
    pastel_colors = [
        "#FFB6B9",
        "#FAD0C4",
        "#A8E6CF",
        "#DCEDC2",
        "#FFD3B6",
        "#FFAAA5",
        "#84FAB0",
        "#8FD3F4",
        "#C6FFDD",
    ]
    chart_datasets = []
    for i, (key, values) in enumerate(datasets.items()):
        chart_datasets.append(
            {
                "label": key,
                "data": values,
                "fill": False,
                "borderColor": pastel_colors[i % len(pastel_colors)],
                "tension": 0.3,
                "borderWidth": 2 if key != "Total" else 3,
            }
        )
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial; margin: 40px; background: #fefefe; color: #333; }}
            h2 {{ text-align: center; margin-bottom: 30px; }}
            canvas {{ max-width: 100%; height: 400px; }}
        </style>
    </head>
    <body>
        <h2>Dogs Registered in Canary Islands</h2>
        <canvas id="chart"></canvas>
        <script>
            const labels = {json.dumps(labels)};
            const datasets = {json.dumps(chart_datasets)};
            new Chart(document.getElementById("chart"), {{
                type: "line",
                data: {{ labels: labels, datasets: datasets }},
                options: {{
                    responsive: true,
                    interaction: {{ mode: 'nearest', intersect: false }},
                    plugins: {{ legend: {{ position: 'top' }}, tooltip: {{ mode: 'index', intersect: false }} }},
                    scales: {{
                        y: {{ beginAtZero: true, title: {{ display: true, text: 'Number of Dogs' }} }},
                        x: {{ title: {{ display: true, text: 'Date' }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """


# -------------------------
# Rescues Graph
# -------------------------
@app.get("/graph-rescues", response_class=HTMLResponse)
def graph_rescues():
    rows = fetch_data(RESCUES_TABLE)
    labels, datasets_dict = rescues_rows_to_chart_data(rows)
    pastel_colors = [
        "#FFB6B9",
        "#FAD0C4",
        "#A8E6CF",
        "#DCEDC2",
        "#FFD3B6",
        "#FFAAA5",
        "#84FAB0",
        "#8FD3F4",
        "#C6FFDD",
    ]
    chart_datasets = []
    for i, (key, values) in enumerate(datasets_dict.items()):
        chart_datasets.append(
            {
                "label": key,
                "data": values,
                "fill": False,
                "borderColor": pastel_colors[i % len(pastel_colors)],
                "tension": 0.3,
                "borderWidth": 2 if key != "Total" else 3,
            }
        )
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial; margin: 40px; background: #fefefe; color: #333; }}
            h2 {{ text-align: center; margin-bottom: 30px; }}
            canvas {{ max-width: 100%; height: 400px; }}
        </style>
    </head>
    <body>
        <h2>Rescued Dogs by Island</h2>
        <canvas id="chart"></canvas>
        <script>
            const labels = {json.dumps(labels)};
            const datasets = {json.dumps(chart_datasets)};
            new Chart(document.getElementById("chart"), {{
                type: "line",
                data: {{ labels: labels, datasets: datasets }},
                options: {{
                    responsive: true,
                    interaction: {{ mode: 'nearest', intersect: false }},
                    plugins: {{ legend: {{ position: 'top' }}, tooltip: {{ mode: 'index', intersect: false }} }},
                    scales: {{
                        y: {{ beginAtZero: true, title: {{ display: true, text: 'Total Dogs Rescued' }} }},
                        x: {{ title: {{ display: true, text: 'Date' }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
