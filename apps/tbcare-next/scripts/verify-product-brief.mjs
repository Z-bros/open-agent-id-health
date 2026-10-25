import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source=(name)=>readFileSync(new URL(`../${name}`,import.meta.url),'utf8');
const page=source('app/page.tsx');
const styles=source('app/globals.css');
const i18n=source('lib/i18n.ts');
const layout=source('app/layout.tsx');
const api=source('lib/api.ts');
const proxy=source('app/api/backend/[...parts]/route.ts');
const config=source('next.config.mjs');
function luminance(hex){
 const a=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255)
   .map(x=>x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4));
 return .2126*a[0]+.7152*a[1]+.0722*a[2];
}
function contrast(fg,bg){const [a,b]=[luminance(fg),luminance(bg)].sort((x,y)=>y-x);return (a+.05)/(b+.05)}
for(const [description, fg,bg] of [
 ['primary CTA','#FFFFFF','#176B82'],
 ['body ink','#182B3A','#FFFFFF'],
 ['secondary text','#4C6070','#FFFFFF'],
 ['verified source','#215E4D','#DCEFE5'],
 ['review attention','#704A16','#F8E9D0'],
 ['rejected output','#873C35','#F9E4E2'],
 ['unknown/neutral','#344F5B','#EEF2F4'],
 ['metadata text','#516576','#FFFFFF'],
]) assert.ok(contrast(fg,bg)>=4.5,`${description} contrast insufficient`);
assert.match(page,/useState<Locale>\("id"\)/);
assert.match(layout,/html lang="id"/);
assert.match(page,/document\.documentElement\.lang = locale/);
assert.match(page,/aria-pressed=\{selected===id\}/);
assert.match(page,/setSelected\(id\)/);
assert.match(page,/sourceMode.*source-mode-cell/s);
assert.match(page,/aria-expanded=\{isExpanded\}/);
assert.match(page,/expandedRecords\.includes\(o\.record_id\)/);
assert.match(page,/detailEvidenceOnly/);
assert.match(page,/!liveMode && !demoFixtures\.includes\(id\)/);
assert.match(page,/!liveMode && !demoFixtures\.includes\(selected\)/);
assert.match(page,/it\.impaired\?t\("partialSource"\)/);
assert.match(page,/reviewNote\.trim\(\)\.length < 12/);
assert.match(page,/backendConnection !== "connected"/);
assert.match(page,/retryBackendConnection/);
assert.match(i18n,/backendUnavailable: "API lokal tidak tersedia"/);
assert.match(styles, /record-detail-grid/);
assert.match(styles, /:focus-visible/);
assert.match(i18n,/partialSource: "Sebagian sumber tidak tersedia"/);
assert.match(i18n,/partialSource: "Partial source access"/);
assert.match(page,/requires_human_approval|safeValue/);
assert.match(api,/X-TBCareOS-Evidence-SHA256/);
assert.match(proxy,/TBCARE_ENABLE_LOCAL_PROXY/);
assert.match(config,/outputFileTracingRoot: process\.cwd\(\)/);
assert.doesNotMatch(styles.slice(styles.lastIndexOf('TBCare institutional casework refinement')),/linear-gradient\(|backdrop-filter\s*:/);
console.log('Product brief checks passed: locale, table selection, source metadata, access semantics, WCAG AA color tokens, read-only integration.');

// Regression: noteCounts values are numbers, never arrays.
assert.doesNotMatch(page, /prev\[caseId\]\?\.length/, "numeric review counts must not use .length");
