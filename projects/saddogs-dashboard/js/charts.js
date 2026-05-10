import { fmtLabel } from './dataProcessing.js';
import { toDelta } from './dataProcessing.js';
import { PAL } from './config.js';

window.Chart.defaults.font.family = "'Space Mono', monospace";
window.Chart.defaults.font.size = 10;
window.Chart.defaults.color = "#4a4a44";

  export function mkAbsDS(ds, mode) {
    const keys = mode==='total' ? ['Total'] : Object.keys(ds);
    return keys.map((k,i)=>{
      const tot=k==='Total', solo=mode==='total';
      return { label:fmtLabel(k), data:ds[k], fill:solo, borderColor:solo?'#e8c547':tot?'#e8e8e4':PAL[i%PAL.length], backgroundColor:solo?'#e8c54718':'transparent', borderWidth:tot?2:1, pointRadius:0, pointHoverRadius:3, tension:0.3, order:tot?0:1 };
    });
  }

  export function mkDeltaDS(ds, mode) {
    const delta = toDelta(ds);
    const keys = mode==='total' ? ['Total'] : Object.keys(delta);
    return keys.map((k,i)=>{
      const tot=k==='Total', solo=mode==='total';
      return { label:fmtLabel(k), data:delta[k], fill:false, borderColor:solo?'#e8c547':tot?'#e8e8e4':PAL[i%PAL.length], backgroundColor:'transparent', borderWidth:tot?2:1, pointRadius:0, pointHoverRadius:3, tension:0.3, order:tot?0:1 };
    });
  }

  export const TOOLTIP = { backgroundColor:'#1e1e1e', titleFont:{size:9,weight:'400'}, bodyFont:{size:9}, padding:10, cornerRadius:0, titleColor:'#7a7a74', bodyColor:'#e8e8e4', borderColor:'#2e2e2e', borderWidth:1 };
  export const LEGEND  = { position:'bottom', align:'start', labels:{font:{size:9},padding:14,usePointStyle:true,pointStyle:'line',color:'#4a4a44',boxWidth:18} };
  export const YS = { grid:{color:'#181818',lineWidth:1}, border:{display:false}, ticks:{font:{size:9},color:'#4a4a44',maxTicksLimit:5} };
  export const XS = { grid:{display:false}, border:{display:false}, ticks:{font:{size:9},color:'#4a4a44',maxTicksLimit:6,maxRotation:0} };
