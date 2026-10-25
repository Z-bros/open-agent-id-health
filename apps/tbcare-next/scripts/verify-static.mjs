import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const required = [
  'app/page.tsx', 'app/globals.css', 'app/layout.tsx',
  'app/api/backend/[...parts]/route.ts', 'lib/api.ts',
  'lib/demo.ts', 'lib/i18n.ts', 'lib/types.ts',
];
for (const path of required) assert.ok(existsSync(new URL(`../${path}`, import.meta.url)), `Missing ${path}`);
const ui = read('app/page.tsx');
const proxy = read('app/api/backend/[...parts]/route.ts');
const demo = read('lib/demo.ts');
const dict = read('lib/i18n.ts');
assert.match(dict, /CaseLens/);
assert.match(dict, /NextStep/);
assert.match(ui, /evidence_snapshot_sha256/);
assert.match(ui, /checked/);
assert.match(ui, /new Date\(\)\.toISOString\(\)/);
assert.match(proxy, /TBCARE_ENABLE_LOCAL_PROXY/);
assert.match(proxy, /127\.0\.0\.1:8765/);
assert.match(proxy, /SNAPSHOT\.test\(digest\)/);
assert.match(demo, /"CASE-TB-001"/);
assert.match(demo, /"CASE-TB-009"/);
assert.match(demo, /"CASE-TB-018"/);
assert.match(dict, /Tinjauan catatan administratif TBC/);
console.log('Static checks passed: files, demo scenarios, bilingual UI, snapshot header, localhost API restriction.');
