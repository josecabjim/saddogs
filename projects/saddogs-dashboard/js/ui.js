import { slice, toDelta, fmtLabel, clamp, offsetDate } from './dataProcessing.js';
import { mkAbsDS, mkDeltaDS, TOOLTIP, LEGEND, YS, XS } from './charts.js';
import { ABSOLUTE_START } from './config.js';

let absChart = null, deltaChart = null, trendChart = null;
let absMode = 'total', deltaMode = 'total';
let currentFrom = ABSOLUTE_START, currentTo = '';

const fmt = n => n?.toLocaleString('en-GB') ?? '—';
const fmtD = n => n == null ? '—' : (n >= 0 ? '+' : '') + n.toLocaleString('en-GB');

export function updateStats(rDS) {
  const tot = rDS["Total"];
  if (!tot?.length) return;
  const delta = tot.at(-1) - tot[0];
  const el = document.getElementById("s-delta");
  el.textContent = fmtD(delta);
  el.className = "stat-val " + (delta>0?'up':delta<0?'dn':'');
  document.getElementById("s-delta-note").textContent = `rescue change since ${currentFrom}`;
}

  export function updateCensusCards(cL, cDS) {
    const el = document.getElementById('census-cards');
    if (!el) return;
    const islands = Object.keys(cDS).filter(k=>k!=="Total").sort();
    const maxVal = Math.max(...islands.map(isl=>cDS[isl].at(-1)??0));
    el.innerHTML = islands.map(isl=>{
      const vals=cDS[isl], latest=vals.at(-1)??0, first=vals.find(v=>v!=null)??0, delta=latest-first;
      const pct=maxVal>0?(latest/maxVal)*100:0, cls=delta>0?'up':delta<0?'dn':'flat', arrow=delta>0?'↑':delta<0?'↓':'→';
      return `<div class="island-card"><div class="ic-name">${fmtLabel(isl)}</div><div class="ic-val">${fmt(latest)}</div><div class="ic-change ${cls}">${arrow} ${fmtD(delta)}</div><div class="ic-bar" style="width:${pct.toFixed(1)}%"></div></div>`;
    }).join('');
  }

  export function renderRescue() {
    const { labels:rL, datasets:rDS } = slice(window.ALL_R.labels, window.ALL_R.datasets, currentFrom, currentTo);
    document.getElementById("rescue-section").innerHTML = `
      <div class="section-head">
        <div>
          <div class="section-title">Dogs in <strong>Rescue</strong></div>
          <div class="section-desc">Left: absolute count · Right: change from period start · toggle total / per island on each chart independently</div>
        </div>
      </div>
      <div class="chart-pair">
        <div class="chart-pane">
          <div class="chart-pane-head">
            <div class="chart-pane-label">Absolute count</div>
            <div class="view-toggle" id="abs-toggle">
              <button class="view-btn active" data-mode="total">Total</button>
              <button class="view-btn" data-mode="islands">By island</button>
            </div>
          </div>
          <div class="chart-wrap"><canvas id="cAbs"></canvas></div>
        </div>
        <div class="chart-pane">
          <div class="chart-pane-head">
            <div class="chart-pane-label">Change from period start</div>
            <div class="view-toggle" id="delta-toggle">
              <button class="view-btn active" data-mode="total">Total</button>
              <button class="view-btn" data-mode="islands">By island</button>
            </div>
          </div>
          <div class="chart-wrap"><canvas id="cDelta"></canvas></div>
        </div>
      </div>`;

    absChart = new window.Chart(document.getElementById('cAbs'), {
      type:'line', data:{labels:rL, datasets:mkAbsDS(rDS, absMode)},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:LEGEND, tooltip:{...TOOLTIP, callbacks:{label:c=>` ${c.dataset.label}: ${fmt(c.parsed.y)}`}} },
        scales:{ y:{...YS, beginAtZero:false, ticks:{...YS.ticks, callback:v=>fmt(v)}}, x:XS } }
    });

    deltaChart = new window.Chart(document.getElementById('cDelta'), {
      type:'line', data:{labels:rL, datasets:mkDeltaDS(rDS, deltaMode)},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:LEGEND, tooltip:{...TOOLTIP, callbacks:{label:c=>` ${c.dataset.label}: ${c.parsed.y>=0?'+':''}${fmt(c.parsed.y)}`}} },
        scales:{ y:{...YS, beginAtZero:false, ticks:{...YS.ticks, callback:v=>(v>=0?'+':'')+fmt(v)}}, x:XS } }
    });

    document.getElementById('abs-toggle').addEventListener('click', e=>{
      const btn=e.target.closest('.view-btn'); if (!btn) return;
      absMode=btn.dataset.mode;
      document.querySelectorAll('#abs-toggle .view-btn').forEach(b=>b.classList.toggle('active',b===btn));
      const {labels:l2,datasets:d2}=slice(window.ALL_R.labels,window.ALL_R.datasets,currentFrom,currentTo);
      absChart.data.labels=l2; absChart.data.datasets=mkAbsDS(d2,absMode); absChart.update();
    });

    document.getElementById('delta-toggle').addEventListener('click', e=>{
      const btn=e.target.closest('.view-btn'); if (!btn) return;
      deltaMode=btn.dataset.mode;
      document.querySelectorAll('#delta-toggle .view-btn').forEach(b=>b.classList.toggle('active',b===btn));
      const {labels:l2,datasets:d2}=slice(window.ALL_R.labels,window.ALL_R.datasets,currentFrom,currentTo);
      deltaChart.data.labels=l2; deltaChart.data.datasets=mkDeltaDS(d2,deltaMode); deltaChart.update();
    });
  }

  export function renderCensus() {
    const { labels:cL, datasets:cDS } = slice(window.ALL_C.labels, window.ALL_C.datasets, currentFrom, currentTo);
    const islands = Object.keys(cDS).filter(k=>k!=="Total").sort();
    const maxVal = Math.max(...islands.map(isl=>cDS[isl].at(-1)??0));
    const cards = islands.map(isl=>{
      const vals=cDS[isl], latest=vals.at(-1)??0, first=vals.find(v=>v!=null)??0, delta=latest-first;
      const pct=maxVal>0?(latest/maxVal)*100:0, cls=delta>0?'up':delta<0?'dn':'flat', arrow=delta>0?'↑':delta<0?'↓':'→';
      return `<div class="island-card"><div class="ic-name">${fmtLabel(isl)}</div><div class="ic-val">${fmt(latest)}</div><div class="ic-change ${cls}">${arrow} ${fmtD(delta)}</div><div class="ic-bar" style="width:${pct.toFixed(1)}%"></div></div>`;
    }).join('');

    document.getElementById("census-section").innerHTML = `
      <div class="section-head">
        <div>
          <div class="section-title"><strong>Registered</strong> Dogs by Island</div>
          <div class="section-desc">Latest snapshot · bar shows share relative to highest island · change within selected period</div>
        </div>
      </div>
      <div class="island-cards" id="census-cards">${cards}</div>
      <div style="margin-top:20px">
        <div class="chart-pane-label" style="margin-bottom:12px">Total registered — trend</div>
        <div class="chart-wrap-sm"><canvas id="cTrend"></canvas></div>
      </div>`;

    trendChart = new window.Chart(document.getElementById('cTrend'), {
      type:'line', data:{ labels:cL, datasets:[{ label:'Total registered', data:cDS["Total"], fill:true, borderColor:'#e8c547', backgroundColor:'#e8c54710', borderWidth:1.5, pointRadius:0, pointHoverRadius:3, tension:0.3 }] },
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:{display:false}, tooltip:{...TOOLTIP, callbacks:{label:c=>` Total: ${fmt(c.parsed.y)}`}} },
        scales:{ y:{...YS, beginAtZero:false, ticks:{...YS.ticks, callback:v=>fmt(v)}}, x:XS } }
    });
  }

  export function updateStats(rDS) {
    const tot = rDS["Total"];
    if (!tot?.length) return;
    const delta = tot.at(-1) - tot[0];
    const el = document.getElementById("s-delta");
    el.textContent = fmtD(delta);
    el.className = "stat-val " + (delta>0?'up':delta<0?'dn':'');
    document.getElementById("s-delta-note").textContent = `rescue change since ${currentFrom}`;
  }

  export function updateAll() {
    const { labels:rL, datasets:rDS } = slice(window.ALL_R.labels, window.ALL_R.datasets, currentFrom, currentTo);
    const { labels:cL, datasets:cDS } = slice(window.ALL_C.labels, window.ALL_C.datasets, currentFrom, currentTo);
    updateStats(rDS);
    if (absChart)   { absChart.data.labels = rL;   absChart.data.datasets   = mkAbsDS(rDS, absMode);   absChart.update(); }
    if (deltaChart) { deltaChart.data.labels = rL; deltaChart.data.datasets = mkDeltaDS(rDS, deltaMode); deltaChart.update(); }
    updateCensusCards(cL, cDS);
    if (trendChart) { trendChart.data.labels = cL; trendChart.data.datasets[0].data = cDS["Total"]; trendChart.update(); }
  }

  export function applyRange(from, to, activeBtn) {
    currentFrom = clamp(from || ABSOLUTE_START);
    currentTo   = to || '';
    document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');
    document.getElementById('date-from').value = currentFrom;
    if (currentTo) document.getElementById('date-to').value = currentTo;
    updateAll();
  }

  export function downloadData() {
    if (!window.ALL_C.labels || !window.ALL_C.labels.length || !window.ALL_R.labels || !window.ALL_R.labels.length) {
      alert('No data available to download');
      return;
    }
    const islands = Object.keys(window.ALL_C.datasets).filter(k => k !== 'Total').sort();
    const cIslands = Object.keys(window.ALL_C.datasets).filter(k => k !== 'Total').sort();
    const rIslands = Object.keys(window.ALL_R.datasets).filter(k => k !== 'Total').sort();
    
    // Use rescue data labels as primary (more complete)
    const labels = window.ALL_R.labels;
    const censusMap = {}; for (let i = 0; i < window.ALL_C.labels.length; i++) { censusMap[window.ALL_C.labels[i]] = i; }
    
    const rows = [];
    const header = ['Date'];
    cIslands.forEach(isl => header.push(`${isl} (Registered)`));
    rIslands.forEach(isl => header.push(`${isl} (Rescue)`));
    rows.push(header.join(','));
    
    for (let i = 0; i < labels.length; i++) {
      const date = labels[i];
      const row = [date];
      const cIdx = censusMap[date];
      cIslands.forEach(isl => row.push(cIdx !== undefined ? (window.ALL_C.datasets[isl][cIdx] || 0) : 0));
      rIslands.forEach(isl => row.push(window.ALL_R.datasets[isl][i] || 0));
      rows.push(row.join(','));
    }
    
    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sad-dogs-data-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }
