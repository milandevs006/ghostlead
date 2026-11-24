export type AnalyticsData = {
  websites: {id:number;name:string;url:string}[];
  monitors: {id:number;site_id:number;name:string;kind:string}[];
  runs: {id:number;monitor_id:number;observed_at:string;status:string;latency_ms:number|null}[];
  lead_events: {id:number;site_id:number;event_key:string;stage:'source'|'destination';observed_at:string}[];
};
export type Range = {start:number;end:number}; // inclusive start, exclusive end (UTC milliseconds)
export function percentile(values:number[], p:number):number|null {
  if (!values.length) return null;
  const a=[...values].sort((x,y)=>x-y);
  return a[Math.max(0,Math.ceil(a.length*p)-1)];
}
export function analyse(data:AnalyticsData, range:Range, siteId:number|null){
  const within=(s:string)=>{const t=Date.parse(s);return t>=range.start&&t<range.end};
  const sites=data.websites.filter(s=>siteId===null||s.id===siteId);
  const siteIds=new Set(sites.map(s=>s.id));
  const monitors=new Map(data.monitors.filter(m=>siteIds.has(m.site_id)).map(m=>[m.id,m]));
  const runs=data.runs.filter(r=>monitors.has(r.monitor_id)&&within(r.observed_at));
  const events=data.lead_events.filter(e=>siteIds.has(e.site_id));
  const sources=events.filter(e=>e.stage==='source'&&within(e.observed_at));
  const key=(e:{site_id:number;event_key:string})=>JSON.stringify([e.site_id,e.event_key]);
  const destinations=new Map(events.filter(e=>e.stage==='destination'&&Date.parse(e.observed_at)<range.end).map(e=>[key(e),e]));
  const sourceKeys=new Set(events.filter(e=>e.stage==='source'&&Date.parse(e.observed_at)<range.end).map(key));
  const destinationOnly=events.filter(e=>e.stage==='destination'&&within(e.observed_at)&&!sourceKeys.has(key(e))).length;
  const matches=sources.map(s=>({source:s,destination:destinations.get(key(s))}));
  const matched=matches.filter(x=>x.destination).length;
  const reversed=matches.filter(x=>x.destination&&Date.parse(x.destination.observed_at)<Date.parse(x.source.observed_at)).length;
  const latency=matches.flatMap(x=>{if(!x.destination)return [];const ms=Date.parse(x.destination.observed_at)-Date.parse(x.source.observed_at);return ms>=0?[ms]:[]});
  const durations=runs.flatMap(r=>r.latency_ms!==null&&Number.isFinite(r.latency_ms)&&r.latency_ms>=0?[r.latency_ms]:[]);
  const counts=(rr:typeof runs)=>({passed:rr.filter(r=>r.status==='passed').length,failed:rr.filter(r=>r.status==='failed').length,inconclusive:rr.filter(r=>r.status==='inconclusive').length,total:rr.length});
  const summary=counts(runs);
  const byDay=new Map<string,typeof runs>();
  const hours=new Map<string,{hour:number;day:number;total:number;failed:number}>();
  const byKind=new Map<string,number>();
  for(const r of runs){
    const d=new Date(r.observed_at),day=d.toISOString().slice(0,10);const rr=byDay.get(day)??[];rr.push(r);byDay.set(day,rr);
    const weekday=(d.getUTCDay()+6)%7,hour=d.getUTCHours(),k=`${weekday}:${hour}`;
    const cell=hours.get(k)??{hour,day:weekday,total:0,failed:0};cell.total++;if(r.status==='failed')cell.failed++;hours.set(k,cell);
    if(r.status==='failed'){const kind=monitors.get(r.monitor_id)!.kind;byKind.set(kind,(byKind.get(kind)??0)+1)}
  }
  const daily=[...byDay.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([date,rr])=>{const v=rr.flatMap(r=>r.latency_ms!==null&&Number.isFinite(r.latency_ms)&&r.latency_ms>=0?[r.latency_ms]:[]);return {date,...counts(rr),p50:percentile(v,.5),p95:percentile(v,.95)}});
  const siteRows=sites.map(s=>{const c=counts(runs.filter(r=>monitors.get(r.monitor_id)?.site_id===s.id));const src=matches.filter(x=>x.source.site_id===s.id);return {...s,...c,sources:src.length,matched:src.filter(x=>x.destination).length}});
  return {summary,sourceCount:sources.length,matched,unmatched:sources.length-matched,destinationOnly,reversed,deliverySample:latency.length,deliveryMedian:percentile(latency,.5),deliveryP95:percentile(latency,.95),checkSample:durations.length,checkMedian:percentile(durations,.5),checkP95:percentile(durations,.95),daily,hours:[...hours.values()],failures:[...byKind.entries()].map(([name,value])=>({name,value})),siteRows};
}
