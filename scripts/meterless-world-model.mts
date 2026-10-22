/** TB-CareOS -> actual Meterless World Model reference, no vendored library.
 *
 * Invoke with locally installed tsx from Meterless reference directory:
 *    /path/to/reference/node_modules/.bin/tsx scripts/meterless-world-model.mts \
 *      --input /tmp/tbcareos_....json --reference /path/to/reference \
 *      --state-dir /path/to/outputs/meterless
 *
 * The reference is loaded from --reference/src/index.ts; the reference's
 * local persistent storage belongs to --state-dir/.world/.
 */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

type Observation = {
  externalId: string;
  type: string;
  title: string;
  text: string;
  at: string;
  source: { kind: string; by: string; at: string; url?: string };
  entities: { type: string; name: string }[];
};

function flag(name: string): string {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) {
    throw new Error("Missing required argument " + name);
  }
  return process.argv[index + 1];
}

function validate(items: unknown): asserts items is Observation[] {
  if (!Array.isArray(items) || items.length === 0 || items.length > 600) {
    throw new Error("Expected 1–600 fabricated observations");
  }
  const ids = new Set<string>();
  for (const item of items) {
    if (!item || typeof item !== "object") throw new Error("Invalid observation");
    const obs = item as Observation;
    if (typeof obs.externalId !== "string" ||
        !obs.externalId.startsWith("tb-careos:CASE-TB-") ||
        ids.has(obs.externalId) ||
        typeof obs.title !== "string" || typeof obs.text !== "string" ||
        typeof obs.at !== "string" || !Number.isFinite(Date.parse(obs.at)) ||
        obs.source?.at !== obs.at ||
        !["api", "agent"].includes(obs.source?.kind) ||
        !Array.isArray(obs.entities)) {
      throw new Error("Invalid or duplicate synthetic observation; no ingest");
    }
    ids.add(obs.externalId);
  }
}

async function main(): Promise<void> {
  const inputPath = path.resolve(flag("--input"));
  const referencePath = path.resolve(flag("--reference"));
  const stateDir = path.resolve(flag("--state-dir"));
  const caseId = flag("--case-id");
  if (!/^CASE-TB-[0-9]{3,}$/.test(caseId)) {
    throw new Error("Only synthetic CASE-TB case IDs permitted");
  }
  if (!fs.existsSync(path.join(referencePath, "package.json")) ||
      !fs.existsSync(path.join(referencePath, "src", "index.ts"))) {
    throw new Error("Meterless reference implementation not found at --reference");
  }
  const data = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  validate(data);
  if (data.some((obs) => !obs.externalId.startsWith("tb-careos:" + caseId + ":"))) {
    throw new Error("Cross-case World Model ingestion rejected");
  }

  const moduleUrl = pathToFileURL(path.join(referencePath, "src", "index.ts")).href;
  const { WorldModel } = await import(moduleUrl);
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });

  const namespace = "tbcareos_" + caseId.toLowerCase().replace(/[^a-z0-9]/g, "_");
  const world = new WorldModel({ namespace, storage: "local", directory: stateDir });
  const before = world.stateShapeCanonical();
  const first = await world.ingest(data);
  const afterFirst = world.stateShapeCanonical();
  const eventsAfterFirst = world.events().length;
  const second = await world.ingest(data);
  const afterReplay = world.stateShapeCanonical();
  const eventsAfterReplay = world.events().length;
  const idem = (afterFirst === afterReplay &&
                eventsAfterFirst === eventsAfterReplay &&
                second.processed === 0 &&
                second.eventsAppended === 0 &&
                !second.changed);
  if (!idem) throw new Error("Meterless World Model application replay was not idempotent");

  // Return only generated synthetic-case audit metadata. We don't echo
  // raw evidence text, identifiers other than fabricated provenance keys,
  // or credentials. Meterless retains a full local audit and event history.
  const report = {
    case_id: caseId,
    world_model: "Meterless World Model reference",
    persistence: "local",
    namespace,
    input_observations: data.length,
    first_pass: {
      processed: first.processed,
      skipped_unchanged: first.skippedUnchanged,
      events_appended: first.eventsAppended,
      state_changed: before !== afterFirst,
      // Meterless' reference saves append-only events, observations and
      // stories, but not all rebuilt entity aggregates in its event log.
      // A zero-write ingest after reopening can repopulate that projection.
      derived_projection_rebuilt_on_reload:
        first.processed === 0 && first.eventsAppended === 0 && before !== afterFirst,
    },
    replay: {
      processed: second.processed,
      skipped_unchanged: second.skippedUnchanged,
      events_appended: second.eventsAppended,
      state_unchanged: idem,
    },
    durable_state: {
      event_count: world.events().length,
      audit_count: world.audit().length,
      observation_count: (world.stateShape() as {observations: unknown[]}).observations.length,
      most_recent_events: world.events().slice(-5).map((event: { kind: string; at: string; id: string }) => ({
        event_id: event.id, type: event.kind, observed_at: event.at,
      })),
    },
  };
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}

main().catch((error: unknown) => {
  // Prevent exception dumps from exposing raw source records/credentials.
  process.stderr.write(
    "Meterless sidecar failed: " + (error instanceof Error ? error.message : "unknown error") + "\n"
  );
  process.exitCode = 1;
});
