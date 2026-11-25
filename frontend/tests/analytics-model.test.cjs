// Test-only fixtures. Never imported by the application or written to a database.
async function main(){
const {default:assert}=await import('node:assert/strict');
const {pathToFileURL}=await import('node:url');
const {default:model}=await import(pathToFileURL(process.argv[2]).href);
const {analyse,percentile}=model;
const range={start:Date.parse('2026-01-01T00:00:00Z'),end:Date.parse('2026-01-03T00:00:00Z')};
const empty={websites:[],monitors:[],runs:[],lead_events:[]};
let a=analyse(empty,range,null);assert.equal(a.summary.total,0);assert.equal(a.deliveryMedian,null);assert.equal(a.checkP95,null);assert.deepEqual(a.daily,[]);assert.deepEqual(a.hours,[]);
const d={websites:[{id:1,name:'test A',url:'https://a.invalid'},{id:2,name:'test B',url:'https://b.invalid'}],monitors:[{id:1,site_id:1,name:'check',kind:'form'},{id:2,site_id:2,name:'check',kind:'webhook'}],runs:[{id:1,monitor_id:1,observed_at:'2026-01-01T01:00:00Z',status:'passed',latency_ms:100},{id:2,monitor_id:1,observed_at:'2026-01-01T01:30:00Z',status:'failed',latency_ms:300},{id:3,monitor_id:2,observed_at:'2026-01-02T02:00:00Z',status:'inconclusive',latency_ms:null},{id:4,monitor_id:1,observed_at:'2026-01-03T00:00:00Z',status:'failed',latency_ms:999}],lead_events:[]};
const event=(site_id,event_key,stage,observed_at)=>d.lead_events.push({id:d.lead_events.length+1,site_id,event_key,stage,observed_at});
event(1,'x','source','2026-01-01T00:00:00Z');event(1,'x','destination','2026-01-01T00:00:02Z');event(1,'y','source','2026-01-02T00:00:00Z');event(1,'y','destination','2026-01-03T00:00:00Z');event(1,'z','source','2026-01-02T00:00:00Z');event(1,'z','destination','2026-01-01T00:00:00Z');event(2,'y','destination','2026-01-02T00:00:00Z');
a=analyse(d,range,null);assert.deepEqual(a.summary,{passed:1,failed:1,inconclusive:1,total:3});assert.equal(a.sourceCount,3);assert.equal(a.matched,2);assert.equal(a.unmatched,1);assert.equal(a.reversed,1);assert.equal(a.deliveryMedian,2000);assert.equal(a.deliverySample,1);assert.equal(a.destinationOnly,1);assert.equal(a.checkMedian,100);assert.equal(a.checkP95,300);assert.equal(a.hours.find(h=>h.hour===1).failed,1);assert.equal(a.hours.find(h=>h.hour===1).total,2);assert.deepEqual(a.failures,[{name:'form',value:1}]);assert.equal(analyse(d,range,2).summary.total,1);assert.equal(analyse(d,range,2).matched,0);assert.equal(analyse(d,range,1).destinationOnly,0);assert.equal(percentile([5],.95),5);assert.equal(percentile([],.5),null);console.log('Analytics model checks passed: empty state, period boundaries, website isolation, outcomes, matching, latency, heatmap, and failure distribution.');
}
main().catch(error=>{console.error(error);process.exitCode=1});
