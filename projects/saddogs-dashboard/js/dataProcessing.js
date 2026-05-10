import { ABSOLUTE_START } from './config.js';

export function makeDateRange(s, e) {
  const out = [], cur = new Date(s + "T00:00:00Z"), end = new Date(e + "T00:00:00Z");
  while (cur <= end) { out.push(cur.toISOString().slice(0,10)); cur.setUTCDate(cur.getUTCDate()+1); }
  return out;
}

  export function offsetDate(months) {
    const d = new Date();
    d.setUTCMonth(d.getUTCMonth() - months);
    return clamp(d.toISOString().slice(0, 10));
  }

  export function processCensus(rows) {
    const seen = new Set(), first = [];
    for (const r of rows) { const d = r.created_at.slice(0,10); if (!seen.has(d)) { seen.add(d); first.push({...r,_d:d}); } }
    if (!first.length) return { labels:[], datasets:{} };
    const skip = ["id","created_at","_d"];
    const cols = Object.keys(first[0]).filter(c => !skip.includes(c));
    const byDate = {}; for (const r of first) byDate[r._d] = r;
    const all = makeDateRange(first[0]._d, first.at(-1)._d);
    const ds = {}; cols.forEach(c => ds[c]=[]); ds["Total"]=[];
    let last = null;
    for (const d of all) {
      if (byDate[d]) last = byDate[d];
      if (!last) continue;
      let t = 0; cols.forEach(c => { const v = last[c]??0; ds[c].push(v); t+=v; }); ds["Total"].push(t);
    }
    return { labels: all, datasets: ds };
  }

  export function processRescues(rows) {
    if (!rows.length) return { labels:[], datasets:{} };
    const rescues = [...new Set(rows.map(r=>`${r.rescue_name}__${r.island}`))];
    const islands = [...new Set(rows.map(r=>r.island))].sort();
    const fp = {};
    for (const r of rows) { const d=r.created_at.slice(0,10), k=`${r.rescue_name}__${r.island}__${d}`; if (!fp[k]) fp[k]={date:d,island:r.island,rescue_name:r.rescue_name,total_dogs:r.total_dogs}; }
    const deduped = Object.values(fp);
    const brd = {};
    const rescueFirstDate = {};
    const rescueFirstValue = {};
    for (const r of deduped) { 
      const k=`${r.rescue_name}__${r.island}`; 
      if (!brd[k]) brd[k]={};
      brd[k][r.date]=r.total_dogs;
      if (!rescueFirstDate[k] || r.date < rescueFirstDate[k]) {
        rescueFirstDate[k] = r.date;
        rescueFirstValue[k] = r.total_dogs;
      }
    }
    const sorted = deduped.map(r=>r.date).sort();
    const allD = makeDateRange(sorted[0], sorted.at(-1));
    const lkr={}, ds={}; islands.forEach(i=>ds[i]=[]); ds["Total"]=[];
    for (const d of allD) {
      const it={};
      for (const rk of rescues) {
        const isl=rk.split("__")[1];
        let v = brd[rk]?.[d];
        if (v===undefined) {
          if (d < rescueFirstDate[rk]) {
            v = rescueFirstValue[rk];
          } else {
            v = lkr[rk] ?? 0;
          }
        }
        if (v!==undefined) lkr[rk] = v;
        it[isl]=(it[isl]||0)+(lkr[rk]??0);
      }
      let t=0; islands.forEach(isl=>{const v=it[isl]||0;ds[isl].push(v);t+=v;}); ds["Total"].push(t);
    }
    return { labels: allD, datasets: ds };
  }

  export function slice(labels, datasets, from, to) {
    const s = clamp(from || ABSOLUTE_START);
    const e = to || labels.at(-1) || s;
    const i0 = labels.findIndex(d => d >= s);
    const i1 = [...labels].reverse().findIndex(d => d <= e);
    if (i0 === -1) return { labels, datasets };
    const end = i1 === -1 ? labels.length-1 : labels.length-1-i1;
    const newL = labels.slice(i0, end+1);
    const newDS = {};
    for (const [k,v] of Object.entries(datasets)) newDS[k] = v.slice(i0, end+1);
    return { labels: newL, datasets: newDS };
  }

  export function toDelta(ds) {
    const out = {};
    for (const [k,v] of Object.entries(ds)) { const b = v.find(x=>x!=null)??0; out[k]=v.map(x=>x-b); }
    return out;
  }
  export const fmtLabel = k => k === "Total" ? "Total" : k.split("_").map(w => w[0].toUpperCase() + w.slice(1)).join(" ");

  export const clamp = d => d < ABSOLUTE_START ? ABSOLUTE_START : d;
