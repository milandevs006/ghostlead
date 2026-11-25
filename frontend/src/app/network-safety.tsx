'use client';
import {useEffect,useState} from 'react';
import {ShieldCheck, ShieldAlert, Globe, Lock, RefreshCw, History} from 'lucide-react';
import styles from './network-safety.module.css';
type Site={id:number;name:string;url:string};
type Audit={id:number;observed_at:string;outcome:string;reason:string;address_count:number};
type Safety={site_id:number;verification_status:string;url_allowed:boolean;url_reason:string;can_preflight:boolean;http_enabled:boolean;history:Audit[]};
async function request(id:number,check=false):Promise<Safety>{
 const res=await fetch(`/api/safety/${id}${check?'/preflight':''}`,{method:check?'POST':'GET',cache:'no-store',credentials:'same-origin',headers:{'X-GhostLead-Request':'1'}});
 const body=await res.json().catch(()=>null);if(!res.ok||!body)throw Error(typeof body?.detail==='string'?body.detail:`Request failed (${res.status})`);return body;
}
export default function NetworkSafety({sites}:{sites:Site[]}){
 const [id,setId]=useState<number|null>(null),[state,setState]=useState<Safety|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 const site=sites.find(s=>s.id===id)??sites[0];const sid=site?.id;
 useEffect(()=>{let active=true;setState(null);setError('');if(sid!==undefined)request(sid).then(r=>{if(active)setState(r)}).catch(e=>{if(active)setError(String(e.message))});return()=>{active=false}},[sid,refresh]);
 async function preflight(){if(sid===undefined||busy)return;setBusy(true);setError('');try{setState(await request(sid,true))}catch(e){setError(e instanceof Error?e.message:'Preflight failed.')}finally{setBusy(false)}}
 if(!site)return <section className={styles.panel}><ShieldAlert/> <h2>No registered websites</h2><p>Register a website first. Public DNS intelligence is separate from authorised monitoring.</p></section>;
 const current=state?.site_id===sid?state:null;
 return <div className={styles.wrap}>
 <section className={styles.panel}><div className={styles.heading}><ShieldCheck size={28}/><div><h2>Monitoring readiness</h2><p>Destination policy and proof checks only — no website HTTP requests.</p></div></div><label className={styles.label}>Registered website<select disabled={busy} value={sid} onChange={e=>{setState(null);setId(Number(e.target.value))}}>{sites.map(s=><option key={s.id} value={s.id}>{s.name} — {s.url}</option>)}</select></label><p className={styles.url}>{site.url}</p><div className={styles.grid}><div><Globe/><small>URL policy</small><strong>{!current?'Checking…':current.url_allowed?'Passed':'Blocked'}</strong><p>{current?.url_reason}</p></div><div><ShieldCheck/><small>Domain verification</small><strong>{current?.verification_status??'Checking…'}</strong><p>Active proof and permission required.</p></div><div><Lock/><small>HTTP monitoring</small><strong>Disabled</strong><p>Connection-layer safeguards are not integrated yet.</p></div></div>
 <p className={styles.note}>Preflight checks a verified hostname with the fixed public DNS resolver. A pass is an advisory snapshot, not permission to make future requests. Unverified sites can still use Website intelligence.</p><div className={styles.actions}><button className="primary" disabled={!current||busy} onClick={preflight}><ShieldCheck size={16}/>{busy?'Checking…':'Run safety preflight'}</button><button className="button" disabled={busy} onClick={()=>setRefresh(x=>x+1)}><RefreshCw size={16}/>Refresh status</button></div>{error&&<p role="alert" className={styles.error}>{error}</p>}
 </section><section className={styles.panel}><div className={styles.heading}><History/><div><h2>Safety audit history</h2><p>Last 30 preflight decisions for this website. These are not monitoring observations.</p></div></div>{!current?.history.length?<p className={styles.note}>No saved preflight decisions.</p>:<div className={styles.history}>{current.history.map(a=><div key={a.id} className={styles.audit}><span className={a.outcome==='passed'?styles.pass:styles.block}>{a.outcome}</span><div><strong>{a.reason}</strong><p>{new Date(a.observed_at).toLocaleString()} · {a.address_count} accepted addresses</p></div></div>)}</div>}</section>
 </div>
}
