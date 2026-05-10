import { fetchAllData } from './api.js';
import { processCensus, processRescues, offsetDate } from './dataProcessing.js';
import { renderRescue, renderCensus, updateAll, applyRange, downloadData, updateStats } from './ui.js';
import { ABSOLUTE_START } from './config.js';

let ALL_C = {};
let ALL_R = {};

window.ALL_C = ALL_C;
window.ALL_R = ALL_R;

const fmt = n => n?.toLocaleString('en-GB') ?? '—';

async function load() {
  try {
    const { census, rescues } = await fetchAllData();

    ALL_C = processCensus(census);
    ALL_R = processRescues(rescues);

    // Update window globals so UI functions can access the data
    window.ALL_C = ALL_C;
    window.ALL_R = ALL_R;

    const currentTo = ALL_R.labels.at(-1) ?? '';
    document.getElementById('date-from').value = ABSOLUTE_START;
    document.getElementById('date-to').value = currentTo;

    document.getElementById("s-rescued").textContent   = fmt(ALL_R.datasets["Total"]?.at(-1) ?? 0);
    document.getElementById("s-registered").textContent = fmt(ALL_C.datasets["Total"]?.at(-1) ?? 0);
    document.getElementById("s-days").textContent       = ALL_C.labels.length;
    document.getElementById("last-updated").textContent = ALL_C.labels.at(-1) ?? ALL_R.labels.at(-1) ?? '—';
    updateStats(ALL_R.datasets);

    renderRescue();
    renderCensus();

  } catch(err) {
    console.error(err);
    ['rescue-section','census-section'].forEach(id=>{
      document.getElementById(id).innerHTML=`<div style="padding:40px 0;font-family:'Space Mono',monospace;font-size:0.65rem;color:var(--muted-hi)">Error — ${err.message}</div>`;
    });
  }
}

function init() {
  load();

  document.querySelectorAll('.range-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const m=btn.dataset.months;
      if (m==='all') applyRange(ABSOLUTE_START,'',btn);
      else {
        const months = parseInt(m);
        const from = offsetDate(months);
        applyRange(from,'',btn);
      }
    });
  });

  document.getElementById('apply-custom').addEventListener('click', ()=>{
    const from=document.getElementById('date-from').value;
    const to=document.getElementById('date-to').value;
    if (from) { document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('active')); applyRange(from,to,null); }
  });

  document.getElementById('download-btn').addEventListener('click', () => downloadData());
}

init();