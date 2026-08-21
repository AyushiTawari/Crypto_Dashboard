import requests
import streamlit.components.v1 as components
import streamlit as st

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

response = requests.get("http://localhost:8000/snapshots")
snapshots = response.json() if response.status_code == 200 else []

if not snapshots:
    st.warning("No data yet. Is ingestion running?")
    st.stop()


@st.cache_data(ttl=120)
def fetch_ticker_data(symbol_list):
    data = {}
    for symbol in symbol_list:
        r = requests.get(f"http://localhost:8000/ticker24h/{symbol}")
        if r.status_code == 200:
            data[symbol] = r.json()
    return data


ticker_data = fetch_ticker_data(tuple(s["symbol"] for s in snapshots))

top_symbol = max(snapshots, key=lambda s: s["volume"])["symbol"]
highest = max(snapshots, key=lambda s: s["last_price"])
lowest = min(snapshots, key=lambda s: s["last_price"])
popular = max(snapshots, key=lambda s: s["volume"])

symbols = [s["symbol"] for s in snapshots]


def render_detail_view(detail):
    symbol = detail["symbol"]
    day_stats = ticker_data.get(symbol, {"high_price": "--", "low_price": "--"})
    detail_html = f"""
    <style>
      .detail-wrap {{ font-family:sans-serif; color:white; }}
      .detail-header {{ display:flex; align-items:baseline; gap:16px; }}
      .stats-row {{ display:flex; gap:24px; margin-top:16px; flex-wrap:wrap; }}
      .stat-box {{ background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:14px 20px; }}
      .stat-label {{ color:rgba(255,255,255,0.5); font-size:11px; text-transform:uppercase; }}
      .stat-value {{ font-size:18px; font-weight:600; margin-top:4px; }}
      .pos {{ color:#00d68f; }}
      .neg {{ color:#ff4d4d; }}
    </style>

    <div class="detail-wrap">
      <div style="font-size:18px; opacity:0.6; text-transform:uppercase;">{symbol}</div>
      <div class="detail-header">
        <div id="d-price" style="font-size:40px; font-weight:600;">{detail['last_price']}</div>
        <div id="d-change" style="font-size:18px;" class="{'pos' if detail['price_change_pct'] >= 0 else 'neg'}">{detail['price_change_pct']}%</div>
      </div>

      <div class="stats-row">
        <div class="stat-box"><div class="stat-label">VWAP</div><div class="stat-value" id="d-vwap">{detail['vwap']}</div></div>
        <div class="stat-box"><div class="stat-label">Trade Count</div><div class="stat-value" id="d-trades">{detail['trade_count']}</div></div>
        <div class="stat-box"><div class="stat-label">Volume</div><div class="stat-value" id="d-volume">{detail['volume']}</div></div>
        <div class="stat-box"><div class="stat-label">24h High</div><div class="stat-value">{day_stats['high_price']}</div></div>
        <div class="stat-box"><div class="stat-label">24h Low</div><div class="stat-value">{day_stats['low_price']}</div></div>
      </div>

      <div id="d-chart" style="width:100%; height:380px; margin-top:20px;"></div>
    </div>

    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
      const prices = [];
      const times = [];
      const maxPoints = 200;
      let latest = null;
      let hasRenderedOnce = false;
      const RENDER_INTERVAL_MS = 2000;

      const axisStyle = {{
        visible: true, showgrid: true, gridcolor: "rgba(255,255,255,0.08)",
        zeroline: false, color: "rgba(255,255,255,0.4)", tickfont: {{ size: 11 }},
        showline: true, linecolor: "rgba(255,255,255,0.15)", mirror: true
      }};

      const layout = {{
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
        margin: {{ t: 10, b: 30, l: 60, r: 20 }},
        xaxis: {{ ...axisStyle, showgrid: false, showticklabels: false }},
        yaxis: {{ ...axisStyle }}, showlegend: false
      }};

      const trace = {{
        y: prices, x: times, mode: "lines",
        line: {{ color: "#00d68f", width: 2, shape: "spline" }},
        fill: "tonexty", fillcolor: "rgba(0,214,143,0.15)",
        hovertemplate: "%{{y}}<extra></extra>"
      }};

      const baseline = {{ y: prices, x: times, mode: "lines", line: {{ width: 0 }}, showlegend: false, hoverinfo: "skip" }};

      Plotly.newPlot("d-chart", [baseline, trace], layout, {{ displayModeBar: false }});

      const ws = new WebSocket("ws://localhost:8000/ws/{symbol}");

      ws.onmessage = (event) => {{
        latest = JSON.parse(event.data);
        if (!hasRenderedOnce) {{ render(); hasRenderedOnce = true; }}
      }};

      function render() {{
        if (!latest) return;

        document.getElementById("d-price").innerText = latest.last_price;
        const changeEl = document.getElementById("d-change");
        changeEl.innerText = latest.price_change_pct + "%";
        changeEl.className = latest.price_change_pct >= 0 ? "pos" : "neg";

        document.getElementById("d-vwap").innerText = latest.vwap;
        document.getElementById("d-trades").innerText = latest.trade_count;
        document.getElementById("d-volume").innerText = latest.volume;

        prices.push(latest.last_price);
        times.push(new Date().toLocaleTimeString());
        if (prices.length > maxPoints) {{ prices.shift(); times.shift(); }}

        const minPrice = Math.min(...prices);
        const baselineY = prices.map(() => minPrice);

        Plotly.update("d-chart", {{ y: [baselineY, prices], x: [times, times] }}).then(() => {{
          Plotly.relayout("d-chart", {{ "xaxis.autorange": true, "yaxis.autorange": true }});
        }});
      }}

      setInterval(render, RENDER_INTERVAL_MS);
    </script>
    """
    components.html(detail_html, height=650)


table_rows = "".join(f'''
<tr>
  <td class="sym-cell">{s['symbol'].upper()}</td>
  <td>
    <span id="price-{s['symbol']}">{s['last_price']}</span>
    <span id="change-{s['symbol']}" class="{'pos' if s['price_change_pct'] >= 0 else 'neg'}">{s['price_change_pct']}%</span>
  </td>
  <td id="volume-{s['symbol']}">{s['volume']}</td>
  <td>{ticker_data.get(s['symbol'], {}).get('low_price', '--')}</td>
  <td>{ticker_data.get(s['symbol'], {}).get('high_price', '--')}</td>
  <td><div class="row-spark" id="rowspark-{s['symbol']}"></div></td>
</tr>
''' for s in snapshots)

page_html = f"""
<style>
  .top-row {{ display:flex; gap:20px; font-family:sans-serif; align-items:stretch; margin-bottom:24px; }}
  .kpi-col {{ display:flex; flex-direction:column; gap:14px; width:220px; flex-shrink:0; }}
  .kpi-card {{ background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:16px; aspect-ratio:1.6/1; display:flex; flex-direction:column; justify-content:center; }}
  .kpi-label {{ color:rgba(255,255,255,0.5); font-size:11px; text-transform:uppercase; }}
  .kpi-symbol {{ color:white; font-size:13px; margin-top:6px; }}
  .kpi-price {{ color:white; font-size:20px; font-weight:600; margin-top:4px; }}
  .kpi-change {{ font-size:12px; margin-left:6px; }}
  .chart-col {{ flex:1; color:white; min-width:0; display:flex; flex-direction:column; }}
  .pos {{ color:#00d68f; }}
  .neg {{ color:#ff4d4d; }}
</style>

<div class="top-row">
  <div class="kpi-col">
    <div class="kpi-card">
      <div class="kpi-label">Highest Price</div>
      <div class="kpi-symbol">{highest['symbol'].upper()}</div>
      <div class="kpi-price"><span id="kpi-price-highest">{highest['last_price']}</span><span id="kpi-change-highest" class="kpi-change">{highest['price_change_pct']}%</span></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Lowest Price</div>
      <div class="kpi-symbol">{lowest['symbol'].upper()}</div>
      <div class="kpi-price"><span id="kpi-price-lowest">{lowest['last_price']}</span><span id="kpi-change-lowest" class="kpi-change">{lowest['price_change_pct']}%</span></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Most Popular (Volume)</div>
      <div class="kpi-symbol">{popular['symbol'].upper()}</div>
      <div class="kpi-price"><span id="kpi-price-popular">{popular['last_price']}</span><span id="kpi-change-popular" class="kpi-change">{popular['price_change_pct']}%</span></div>
    </div>
  </div>

  <div class="chart-col">
    <div style="font-size:16px; opacity:0.6; text-transform:uppercase;">{top_symbol}</div>
    <div style="display:flex; align-items:baseline; gap:16px;">
      <div id="price" style="font-size:36px; font-weight:600;">--</div>
      <div id="change" style="font-size:16px;">--</div>
    </div>
    <div id="chart" style="width:100%; height:100%; margin-top:12px;"></div>
  </div>
</div>

<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script>
  const topSymbol = "{top_symbol}";
  const kpiSymbols = {{
    "{highest['symbol']}": "highest",
    "{lowest['symbol']}": "lowest",
    "{popular['symbol']}": "popular"
  }};

  const prices = [];
  const times = [];
  const maxPoints = 200;
  let latestChart = null;
  let hasRenderedChartOnce = false;
  const RENDER_INTERVAL_MS = 3000;

  const axisStyle = {{
    visible: true,
    showgrid: true,
    gridcolor: "rgba(255,255,255,0.08)",
    zeroline: false,
    color: "rgba(255,255,255,0.4)",
    tickfont: {{ size: 11 }},
    showline: true,
    linecolor: "rgba(255,255,255,0.15)",
    mirror: true
  }};

  const layout = {{
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: {{ t: 10, b: 30, l: 55, r: 20 }},
    xaxis: {{ ...axisStyle, showgrid: false, showticklabels: false }},
    yaxis: {{ ...axisStyle }},
    showlegend: false,
    hovermode: "x unified"
  }};

  const trace = {{
    y: prices,
    x: times,
    mode: "lines",
    line: {{ color: "#00d68f", width: 2, shape: "spline" }},
    fill: "tonexty",
    fillcolor: "rgba(0,214,143,0.15)",
    hovertemplate: "%{{y}}<extra></extra>"
  }};

  const baseline = {{
    y: prices,
    x: times,
    mode: "lines",
    line: {{ width: 0 }},
    showlegend: false,
    hoverinfo: "skip"
  }};

  Plotly.newPlot("chart", [baseline, trace], layout, {{ displayModeBar: false }});

  function renderChart() {{
    if (!latestChart) return;

    document.getElementById("price").innerText = latestChart.last_price;
    const changeEl = document.getElementById("change");
    changeEl.innerText = latestChart.price_change_pct + "%";
    changeEl.style.color = latestChart.price_change_pct >= 0 ? "#00d68f" : "#ff4d4d";

    prices.push(latestChart.last_price);
    times.push(new Date().toLocaleTimeString());
    if (prices.length > maxPoints) {{
      prices.shift();
      times.shift();
    }}

    const minPrice = Math.min(...prices);
    const baselineY = prices.map(() => minPrice);

    Plotly.update("chart", {{
      y: [baselineY, prices],
      x: [times, times]
    }}).then(() => {{
      Plotly.relayout("chart", {{
        "xaxis.autorange": true,
        "yaxis.autorange": true
      }});
    }});
  }}

  setInterval(renderChart, RENDER_INTERVAL_MS);

  const kpiWs = new WebSocket("ws://localhost:8000/ws");

  kpiWs.onmessage = (event) => {{
    const data = JSON.parse(event.data);
    const role = kpiSymbols[data.symbol];
    if (role) {{
      document.getElementById("kpi-price-" + role).innerText = data.last_price;
      const kpiChangeEl = document.getElementById("kpi-change-" + role);
      kpiChangeEl.innerText = data.price_change_pct + "%";
      kpiChangeEl.style.color = data.price_change_pct >= 0 ? "#00d68f" : "#ff4d4d";
    }}
  }};

  const chartWs = new WebSocket("ws://localhost:8000/ws/{top_symbol}");

  chartWs.onmessage = (event) => {{
    latestChart = JSON.parse(event.data);
    if (!hasRenderedChartOnce) {{
      renderChart();
      hasRenderedChartOnce = true;
    }}
  }};
</script>
"""

components.html(page_html, height=485)

symbol_options = [""] + symbols
selected_symbol = st.selectbox(
    "Search",
    options=symbol_options,
    format_func=lambda x: "Type to search..." if x == "" else x.upper(),
)

if selected_symbol:
    detail = next(s for s in snapshots if s["symbol"] == selected_symbol)
    render_detail_view(detail)
else:
    table_html = f"""
    <style>
      table {{ width:100%; border-collapse:collapse; font-family:sans-serif; color:white; }}
      th {{ text-align:left; color:rgba(255,255,255,0.5); font-size:12px; text-transform:uppercase; padding:10px; border-bottom:1px solid rgba(255,255,255,0.1); }}
      td {{ padding:10px; border-bottom:1px solid rgba(255,255,255,0.05); font-size:14px; }}
      .sym-cell {{ font-weight:600; }}
      .pos {{ color:#00d68f; }}
      .neg {{ color:#ff4d4d; }}
      .row-spark {{ width:100px; height:30px; }}
    </style>
    <table>
      <thead>
        <tr><th>Symbol</th><th>Price</th><th>Volume</th><th>24h Low</th><th>24h High</th><th>Trend</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>

    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
      const symbols = {symbols!r};
      const history = {{}};
      symbols.forEach(sym => history[sym] = []);

      symbols.forEach(sym => {{
        Plotly.newPlot("rowspark-" + sym, [{{
          y: [], mode: "lines", line: {{ color: "#00d68f", width: 1.5, shape: "spline" }}
        }}], {{
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          margin: {{ t: 0, b: 0, l: 0, r: 0 }},
          xaxis: {{ visible: false }},
          yaxis: {{ visible: false }},
          showlegend: false
        }}, {{ displayModeBar: false, staticPlot: true }});
      }});

      const ws = new WebSocket("ws://localhost:8000/ws");

      ws.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        const sym = data.symbol;
        if (!history[sym]) return;

        const priceEl = document.getElementById("price-" + sym);
        const changeEl = document.getElementById("change-" + sym);
        const volumeEl = document.getElementById("volume-" + sym);
        if (priceEl) priceEl.innerText = data.last_price;
        if (volumeEl) volumeEl.innerText = data.volume;
        if (changeEl) {{
          changeEl.innerText = data.price_change_pct + "%";
          changeEl.className = data.price_change_pct >= 0 ? "pos" : "neg";
        }}

        history[sym].push(data.last_price);
        if (history[sym].length > 50) history[sym].shift();

        Plotly.update("rowspark-" + sym, {{ y: [history[sym]] }});
      }};
    </script>
    """
    components.html(table_html, height=450)