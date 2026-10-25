/** E09/Product C: query persisted real Meterless World Model events in read-only mode.
 * No ingest(), saves, source writes, source queries, or synthetic invented audit.
 * Reference lib is imported from the local separately installed upstream checkout.
 */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

function getFlag(name: string): string {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw Error("Missing " + name);
  return process.argv[index + 1];
}
async function main(): Promise<void> {
  const ref = path.resolve(getFlag("--reference"));
  const stateDir = path.resolve(getFlag("--state-dir"));
  const caseId = getFlag("--case-id");
  if (!/^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$/.test(caseId)) {
    throw Error("Only indexed synthetic TB case IDs can be audited");
  }
  if (!fs.existsSync(path.join(ref, "src", "index.ts")) ||
      !fs.existsSync(path.join(ref, "package.json"))) {
    throw Error("Meterless reference is not installed");
  }
  if (!fs.existsSync(stateDir) || !fs.statSync(stateDir).isDirectory()) {
    throw Error("Meterless synthetic audit state directory does not exist");
  }

  const moduleUrl = pathToFileURL(path.join(ref, "src", "index.ts")).href;
  const { WorldModel } = await import(moduleUrl);
  const namespace = "tbcareos_" + caseId.toLowerCase().replace(/[^a-z0-9]/g, "_");
  const world = new WorldModel({ namespace, storage: "local", directory: stateDir });
  const sourceEvents = world.events();
  const sourceAudit = world.audit();
  if (!Array.isArray(sourceEvents) || !Array.isArray(sourceAudit)) {
    throw Error("Meterless source did not return an auditable event collection");
  }
  if (sourceEvents.length > 10_000 || sourceAudit.length > 20_000) {
    throw Error("Meterless audit exceeds bounded reader limit");
  }
  const events = sourceEvents.slice(-200).map((event: unknown) => {
    if (!event || typeof event !== "object") {
      throw Error("Invalid Meterless event");
    }
    const item = event as {id?: unknown; kind?: unknown; at?: unknown};
    if (typeof item.id !== "string" || !/^evt_[0-9]{1,12}$/.test(item.id) ||
        typeof item.kind !== "string" || !/^[A-Za-z][A-Za-z0-9]{0,60}$/.test(item.kind) ||
        typeof item.at !== "string" || !Number.isFinite(Date.parse(item.at))) {
      throw Error("Meterless returned an unsupported event identity or timestamp");
    }
    return { event_id: item.id, event_type: item.kind, event_at: item.at };
  });
  // world.audit() may include free text/raw observations. Never expose it.
  const reply = {
    schema_version: "1.0.0",
    kind: "meterless_world_model_event_index",
    case_id: caseId,
    namespace,
    store: "real_meterless_reference",
    event_count: sourceEvents.length,
    audit_count: sourceAudit.length,
    has_persisted_events: sourceEvents.length > 0,
    events,
    truncated: sourceEvents.length > events.length,
    source: "local_meterless_world_model",
    timestamp_meaning: "Synthetic evidence snapshot/event time, not agent invocation or human-review time",
  };
  process.stdout.write(JSON.stringify(reply) + "\n");
}
main().catch((error: unknown) => {
  process.stderr.write("Meterless audit reader failed\n");
  process.exitCode = 2;
});
