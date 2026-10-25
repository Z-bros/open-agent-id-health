import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const load = name => readFileSync(new URL(`../${name}`, import.meta.url), 'utf8');
const page = load('app/page.tsx');
const activity = load('app/components/AgentActivity.tsx');
const i18n = load('lib/i18n.ts');
const css = load('app/globals.css');
for(const component of ['IntentStrip','ThinkingTrace','HumanCheckpoint','NotificationCenter','ActivityToast']) {
  assert.match(activity, new RegExp(`function ${component}\\(`), `${component} missing`);
  assert.match(page, new RegExp(`<${component}\\b`), `${component} not mounted`);
}
for(const key of ['intentTitle','thinkingStepWait','humanGateTitle','humanGateComplete','activityCenterTitle','notificationNoBackend','eventNoFindings','eventTrackingStopped']) {
  assert.equal((i18n.match(new RegExp(`\\b${key}:`, 'g')) || []).length,2,`${key} missing translation`);
}
assert.match(page, /!evidenceReviewed\|\|!scopeAcknowledged/);
assert.match(page, /eventStale/);
assert.match(page, /eventNoteSaved/);
assert.match(page, /eventExplainRejected/);
assert.match(page, /eventPlanRejected/);
assert.match(page, /backendApi\.explain\(id, evidence\.evidence_snapshot_sha256\)/);
assert.match(page, /backendApi\.plan\(id, evidence\.evidence_snapshot_sha256\)/);
assert.match(page, /Notification\.requestPermission\(\)/);
assert.match(page, /document\.hidden/);
assert.match(i18n, /No server push, queued workers/);
assert.match(i18n, /not private model reasoning/i);
assert.match(css, /prefers-reduced-motion/);
console.log('Agentic UX static checks passed: intent, request thinking states, human approval, bilingual notifications, no unsupported background claims.');
