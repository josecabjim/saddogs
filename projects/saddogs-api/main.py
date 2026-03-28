import json
import os
from collections import defaultdict
from datetime import datetime, time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from saddogs_database.client import DatabaseClient

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
CENSUS_TABLE = "census"
RESCUES_TABLE = "rescues"


db = DatabaseClient()
app = FastAPI()


class DataCache:
    """Cache for database queries with daily refresh at 8 AM"""

    def __init__(self):
        self.census_data = None
        self.rescues_data = None
        self.census_timestamp = None
        self.rescues_timestamp = None

    def _is_expired(self, timestamp):
        """Check if cache expired (data changes at 8 AM daily)"""
        if timestamp is None:
            return True

        now = datetime.now()
        cache_time = datetime.combine(now.date(), time(8, 0, 0))
        if now.time() < time(8, 0, 0):
            cache_time = cache_time.replace(day=cache_time.day - 1)

        return timestamp < cache_time

    def get_census(self, fetch_func):
        if self.census_data is None or self._is_expired(self.census_timestamp):
            self.census_data = fetch_func()
            self.census_timestamp = datetime.now()
        return self.census_data

    def get_rescues(self, fetch_func):
        if self.rescues_data is None or self._is_expired(self.rescues_timestamp):
            self.rescues_data = fetch_func()
            self.rescues_timestamp = datetime.now()
        return self.rescues_data


cache = DataCache()


def _fetch_census_db():
    return db.census.get_all()


def _fetch_rescues_db():
    return db.rescues.get_all()


def fetch_census():
    return cache.get_census(_fetch_census_db)


def fetch_rescues():
    return cache.get_rescues(_fetch_rescues_db)


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

    aggregated = defaultdict(lambda: defaultdict(int))

    for r in rows:
        date_only = r["created_at"][:10]
        island = r["island"]
        aggregated[date_only][island] += r["total_dogs"]

    labels = sorted(aggregated.keys())
    islands = sorted({r["island"] for r in rows})

    datasets = {island: [] for island in islands}
    totals_per_date = []

    for date in labels:
        daily_total = 0
        for island in islands:
            value = aggregated[date].get(island, 0)
            datasets[island].append(value)
            daily_total += value
        totals_per_date.append(daily_total)

    datasets["Total"] = totals_per_date

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
# Base HTML Template
# -------------------------
def get_base_styles():
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        header h1 {
            font-size: 28px;
            color: #667eea;
            margin-bottom: 8px;
        }
        .header-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        .last-updated {
            font-size: 14px;
            color: #666;
            background: #f5f5f5;
            padding: 8px 12px;
            border-radius: 6px;
        }
        nav {
            display: flex;
            gap: 12px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        nav a {
            display: inline-block;
            padding: 10px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        nav a:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        nav a.active {
            background: #764ba2;
        }
        main {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 24px;
        }
        .chart-container {
            position: relative;
            height: 450px;
            margin-bottom: 20px;
        }
        canvas {
            width: 100% !important;
            height: 100% !important;
        }
        .data-table {
            overflow-x: auto;
            background: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }
        pre {
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
            overflow-x: auto;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .stat-card h3 {
            font-size: 14px;
            font-weight: 600;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: bold;
        }
        footer {
            text-align: center;
            margin-top: 24px;
            color: white;
            font-size: 12px;
        }
        @media (max-width: 768px) {
            header h1 {
                font-size: 22px;
            }
            .header-info {
                flex-direction: column;
                align-items: flex-start;
            }
            nav {
                width: 100%;
            }
            nav a {
                flex: 1;
                text-align: center;
            }
            .chart-container {
                height: 300px;
            }
        }
    """


def get_navigation(current_page=None):
    pages = [
        ("Home", "/", "home"),
        ("Census Graph", "/graph", "census"),
        ("Rescues Graph", "/graph-rescues", "rescues"),
    ]
    nav_html = "<nav>"
    for label, url, page_id in pages:
        active = ' style="background: #764ba2;"' if current_page == page_id else ""
        nav_html += f'<a href="{url}"{active}>{label}</a>'
    nav_html += "</nav>"
    return nav_html


def get_last_updated_time(timestamp):
    if timestamp is None:
        return "Never"
    diff = datetime.now() - timestamp
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)} minutes ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)} hours ago"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M")


# -------------------------
# Homepage
# -------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    data = fetch_census()
    table = make_ascii_table(data)
    last_update = get_last_updated_time(cache.census_timestamp)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sad Dogs - Analytics Dashboard</title>
        <style>
            {get_base_styles()}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🐕 Sad Dogs Analytics</h1>
                <div class="header-info">
                    <div class="last-updated">Updated: {last_update}</div>
                </div>
                {get_navigation("home")}
            </header>
            
            <main>
                <h2>Database Overview</h2>
                <p style="color: #666; margin-bottom: 16px;">Latest census data from the Canary Islands dog registry.</p>
                <div class="data-table">
                    <pre>{table}</pre>
                </div>
            </main>
            
            <footer>
                <p>Data refreshes daily at 8:00 AM</p>
            </footer>
        </div>
    </body>
    </html>
    """


# -------------------------
# Census Graph
# -------------------------
@app.get("/graph", response_class=HTMLResponse)
def graph_page():
    rows = fetch_census()
    labels, datasets = rows_to_chart_data(rows)
    last_update = get_last_updated_time(cache.census_timestamp)

    colors = [
        "#667eea",
        "#764ba2",
        "#f093fb",
        "#4facfe",
        "#00f2fe",
        "#43e97b",
        "#fa709a",
        "#fee140",
        "#30cfd0",
    ]
    chart_datasets = []
    for i, (key, values) in enumerate(datasets.items()):
        chart_datasets.append(
            {
                "label": key,
                "data": values,
                "fill": False,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)],
                "tension": 0.4,
                "borderWidth": 3 if key == "Total" else 2,
                "pointRadius": 4 if key == "Total" else 3,
                "pointBackgroundColor": colors[i % len(colors)],
                "pointBorderColor": "#fff",
                "pointBorderWidth": 2,
                "pointHoverRadius": 6,
            }
        )

    date_range = f"{labels[0]} to {labels[-1]}" if labels else "No data"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Census Graph - Sad Dogs Analytics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            {get_base_styles()}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🐕 Sad Dogs Analytics</h1>
                <div class="header-info">
                    <div class="last-updated">Updated: {last_update}</div>
                </div>
                {get_navigation("census")}
            </header>
            
            <main>
                <h2>Dogs Registered in Canary Islands</h2>
                <p style="color: #666; margin-bottom: 16px;">Cumulative dog registrations over time ({date_range})</p>
                <div class="chart-container">
                    <canvas id="chart"></canvas>
                </div>
            </main>
            
            <footer>
                <p>Data refreshes daily at 8:00 AM • Last update: {last_update}</p>
            </footer>
        </div>
        
        <script>
            const labels = {json.dumps(labels)};
            const datasets = {json.dumps(chart_datasets)};
            const ctx = document.getElementById("chart").getContext("2d");
            new Chart(ctx, {{
                type: "line",
                data: {{ labels: labels, datasets: datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                font: {{ size: 12, weight: 600 }},
                                padding: 16,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }}
                        }},
                        tooltip: {{
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {{ size: 14, weight: 'bold' }},
                            bodyFont: {{ size: 12 }},
                            padding: 12,
                            cornerRadius: 8,
                            displayColors: true
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Number of Dogs',
                                font: {{ size: 12, weight: 600 }}
                            }},
                            grid: {{
                                drawBorder: false,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Date',
                                font: {{ size: 12, weight: 600 }}
                            }},
                            grid: {{
                                drawBorder: false,
                                display: false
                            }}
                        }}
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
    rows = fetch_rescues()
    labels, datasets_dict = rescues_rows_to_chart_data(rows)
    last_update = get_last_updated_time(cache.rescues_timestamp)

    colors = [
        "#667eea",
        "#764ba2",
        "#f093fb",
        "#4facfe",
        "#00f2fe",
        "#43e97b",
        "#fa709a",
        "#fee140",
        "#30cfd0",
    ]
    chart_datasets = []
    for i, (key, values) in enumerate(datasets_dict.items()):
        chart_datasets.append(
            {
                "label": key,
                "data": values,
                "fill": False,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)],
                "tension": 0.4,
                "borderWidth": 3 if key == "Total" else 2,
                "pointRadius": 4 if key == "Total" else 3,
                "pointBackgroundColor": colors[i % len(colors)],
                "pointBorderColor": "#fff",
                "pointBorderWidth": 2,
                "pointHoverRadius": 6,
            }
        )

    date_range = f"{labels[0]} to {labels[-1]}" if labels else "No data"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Rescues Graph - Sad Dogs Analytics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            {get_base_styles()}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🐕 Sad Dogs Analytics</h1>
                <div class="header-info">
                    <div class="last-updated">Updated: {last_update}</div>
                </div>
                {get_navigation("rescues")}
            </header>
            
            <main>
                <h2>Rescued Dogs by Island</h2>
                <p style="color: #666; margin-bottom: 16px;">Dog rescue statistics across Canary Islands ({date_range})</p>
                <div class="chart-container">
                    <canvas id="chart"></canvas>
                </div>
            </main>
            
            <footer>
                <p>Data refreshes daily at 8:00 AM • Last update: {last_update}</p>
            </footer>
        </div>
        
        <script>
            const labels = {json.dumps(labels)};
            const datasets = {json.dumps(chart_datasets)};
            const ctx = document.getElementById("chart").getContext("2d");
            new Chart(ctx, {{
                type: "line",
                data: {{ labels: labels, datasets: datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                font: {{ size: 12, weight: 600 }},
                                padding: 16,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }}
                        }},
                        tooltip: {{
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {{ size: 14, weight: 'bold' }},
                            bodyFont: {{ size: 12 }},
                            padding: 12,
                            cornerRadius: 8,
                            displayColors: true
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Total Dogs Rescued',
                                font: {{ size: 12, weight: 600 }}
                            }},
                            grid: {{
                                drawBorder: false,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Date',
                                font: {{ size: 12, weight: 600 }}
                            }},
                            grid: {{
                                drawBorder: false,
                                display: false
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
