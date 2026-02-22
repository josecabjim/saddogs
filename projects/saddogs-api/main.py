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


def rows_to_chart_data(rows):
    if not rows:
        return [], {}

    # x axis = date from year/month/day
    labels = [f"{r['year']}-{r['month']:02d}-{r['day']:02d}" for r in rows]

    # numeric columns (skip metadata)
    skip_cols = {"id", "created_at", "year", "month", "day"}

    numeric_cols = [c for c in rows[0].keys() if c not in skip_cols]

    datasets = {col: [r[col] for r in rows] for col in numeric_cols}

    return labels, datasets


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


import json


@app.get("/graph", response_class=HTMLResponse)
def graph_page():
    rows = fetch_data()

    labels, datasets = rows_to_chart_data(rows)

    return f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>

    <body style="font-family: Arial; margin: 40px;">
        <h2>Census Graph</h2>

        <canvas id="chart"></canvas>

        <script>
            const labels = {json.dumps(labels)};

            const datasets = {json.dumps(datasets)};

            const chartDatasets = Object.keys(datasets).map((key, i) => {{
                return {{
                    label: key,
                    data: datasets[key],
                    fill: false
                }};
            }});

            new Chart(
                document.getElementById("chart"),
                {{
                    type: "line",
                    data: {{
                        labels: labels,
                        datasets: chartDatasets
                    }},
                    options: {{
                        responsive: true,
                        interaction: {{
                            mode: 'index',
                            intersect: false
                        }},
                        stacked: false,
                        plugins: {{
                            legend: {{
                                position: 'top'
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }}
            );
        </script>

    </body>
    </html>
    """
