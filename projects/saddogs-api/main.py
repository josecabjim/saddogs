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


@app.get("/graph-beautiful", response_class=HTMLResponse)
def modern_dogs_graph():
    rows = fetch_data()
    if not rows:
        return "<h2>No data available</h2>"

    # Dates for x-axis
    labels = [f"{r['year']}-{r['month']:02d}-{r['day']:02d}" for r in rows]

    # Islands columns
    islands = [
        "no_canario",
        "el_hierro",
        "fuerteventura",
        "gran_canaria",
        "la_gomera",
        "la_palma",
        "lanzarote",
        "tenerife",
    ]

    # Per-island datasets
    datasets_dict = {island: [r[island] for r in rows] for island in islands}

    # Total per date
    datasets_dict["Total"] = [sum(r[island] for island in islands) for r in rows]

    import json

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(160deg, #ffecd2 0%, #fcb69f 100%);
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: auto;
                padding: 30px;
                background: rgba(255, 255, 255, 0.85);
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
            }}
            h2 {{
                text-align: center;
                font-weight: 600;
                margin-bottom: 40px;
                color: #222;
            }}
            canvas {{
                max-width: 100%;
                height: 500px;
            }}
            @media (prefers-color-scheme: dark) {{
                body {{
                    background: linear-gradient(160deg, #2e2b3d 0%, #5a4e7c 100%);
                    color: #eee;
                }}
                .container {{
                    background: rgba(30,30,50,0.85);
                    color: #eee;
                }}
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.1.1/dist/chartjs-plugin-zoom.min.js"></script>
    </head>
    <body>
        <div class="container">
            <h2>Dogs Registered in the Canary Islands</h2>
            <canvas id="chart"></canvas>
        </div>
        <script>
            const labels = {json.dumps(labels)};
            const rawDatasets = {json.dumps(datasets_dict)};

            // Pastel gradient colors for islands
            const baseColors = [
                ['#FF9A9E','#FAD0C4'],
                ['#A18CD1','#FBC2EB'],
                ['#FBC2EB','#A6C1EE'],
                ['#84FAB0','#8FD3F4'],
                ['#C6FFDD','#FBD786'],
                ['#FFD3B6','#FFAAA5'],
                ['#FFB6B9','#FAE3D9'],
                ['#B5FFFC','#85A3FF'],
                ['#FFFFFF','#FFD700'] // Total
            ];

            const datasets = Object.keys(rawDatasets).map((key, i) => {{
                const ctx = document.createElement('canvas').getContext('2d');
                const gradient = ctx.createLinearGradient(0,0,0,400);
                gradient.addColorStop(0, baseColors[i % baseColors.length][0]);
                gradient.addColorStop(1, baseColors[i % baseColors.length][1]);
                return {{
                    label: key,
                    data: rawDatasets[key],
                    fill: true,
                    backgroundColor: gradient,
                    borderColor: baseColors[i % baseColors.length][0],
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    borderWidth: key === "Total" ? 4 : 2,
                }};
            }});

            new Chart(document.getElementById('chart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    interaction: {{
                        mode: 'nearest',
                        intersect: false
                    }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: {{
                                    size: 14,
                                    weight: 600
                                }}
                            }}
                        }},
                        tooltip: {{
                            mode: 'index',
                            intersect: false
                        }},
                        zoom: {{
                            pan: {{
                                enabled: true,
                                mode: 'x',
                            }},
                            zoom: {{
                                wheel: {{
                                    enabled: true
                                }},
                                pinch: {{
                                    enabled: true
                                }},
                                mode: 'x',
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Number of Dogs',
                                font: {{
                                    size: 16,
                                    weight: 600
                                }}
                            }},
                            grid: {{
                                color: 'rgba(0,0,0,0.05)'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Date',
                                font: {{
                                    size: 16,
                                    weight: 600
                                }}
                            }},
                            grid: {{
                                color: 'rgba(0,0,0,0.05)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
