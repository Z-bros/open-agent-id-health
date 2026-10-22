/**
 * TB-CareOS -> actual Meterless World Model reference integration.
 * Executed with the tsx binary installed in Meterless reference checkout.
 * The upstream reference is NOT vendored, emulated, or modified here.
 *
 * stdin: JSON array of IngestObservation records produced by mapper.py
 * argv: --reference /path/to/world-model/reference --state-dir ... --case-id CASE-TB-001
 */
import { readFileSync, mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
import path from "node:path";

function option(name: string): string {
  const i = process.argv.indexOf(name);
  if (i < 0 || !process.argv[i + 1]) throw new Error("Missing " + name);
  return process.argv[i + 1];
}

async function readStdin(): Promise<string> {
  let data = "";
  for await (const chunk of process.stdin) {
    data += chunk.toString();
    if (data.length > 2_000_000) throw new Error("Evidence batch exceeded safe size");
  }
  return data;
}

async function main(): Promise<void> {
  const caseId = option("--case-id");
  if (!/^CASE-TB-[A-Za-z0-9_-]{1,60}$/.test(caseId)) throw new Error("Unsafe synthetic case ID");
  const reference = path.resolve(option("--reference"));
  const stateDir = path.resolve(option("--state-dir"));
  const entry = path.join(reference, "src", "index.ts");
  if (!readFileSync(entry, "utf8").includes("export class WorldModel")) {
    throw new Error("Meterless reference WorldModel not found");
  }
  const observations = JSON.parse(await readStdin());
  if (!Array.isArray(observations) || observations.length < 1 || observations.length > 500) {
    throw new Error("Expected 1–500 mapped synthetic observations");
  }
  const prefix = "tbcareos:" + caseId + ":";
  const seen = new Set<string>();
  for (const obs of observations) {
    if (typeof obs.externalId !== "string" || !obs.externalId.startsWith(prefix)
        || seen.has(obs.externalId) || typeof obs.at !== "string"
        || obs.source?.at !== obs.at || obs.source?.kind !== "pipeline"
        || typeof obs.text !== "string" || typeof obs.title !== "string") {
      throw new Error("Invalid/mixed-case observation or non-deterministic provenance");
    }
    seen.add(obs.externalId);
  }

  // tsx resolves the upstream TypeScript module at runtime via an unchanged
  // file URL; only the known local reference checkout is accepted.
  const upstream: any = await import(pathToFileURL(entry).href);
  if (typeof upstream.WorldModel !== "function") throw new Error("Not a Meterless World Model");
  const WorldModel = upstream.WorldModel;
  mkdirSync(stateDir, { recursive: true });
  const namespace = "tbcareos_" + caseId.replace(/[^A-Za-z0-9_]/g, "_");

  const world = new WorldModel({ namespace, storage: "local", directory: stateDir });
  const first = await world.ingest(observations);
  const firstShape = world.stateShapeCanonical();
  const firstEvents = world.events().length;
  const replay = await world.ingest(observations);
  const replayShape = world.stateShapeCanonical();
  const replayEvents = world.events().length;
  const reloaded = new WorldModel({ namespace, storage: "local", directory: stateDir });
  const persisted = reloaded.stateShapeCanonical() === replayShape;
  const unchanged = replayShape === firstShape && firstEvents === replayEvents;
  const timeline = reloaded.view("timeline").get();
  const report = {
    case_id: caseId,
    integration: "Meterless World Model reference",
    persistence: "local_event_log",
    namespace,
    mapped_observations: observations.length,
    first_run: {
      processed: first.processed,
      skipped_unchanged: first.skippedUnchanged,
      events_appended: first.eventsAppended,
    },
    replay: {
      processed: replay.processed,
      skipped_unchanged: replay.skippedUnchanged,
      events_appended: replay.eventsAppended,
      projection_unchanged: unchanged,
    },
    event_count: replayEvents,
    persisted_projection_matches: persisted,
    timeline_sample: timeline.slice(-8).map((e: any) => ({
      id: e.id, kind: e.kind, at: e.at,
    })),
    note: "Event timestamps reflect synthetic evidence timestamps; no clinical action occurred.",
  };
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  if (!unchanged || !persisted || replay.processed !== 0 || replay.eventsAppended !== 0) process.exitCode = 2;
}

main().catch((e) => {
  // Do not print raw input/URLs/tokens; only a redacted exception type/message.
  process.stderr.write("Meterless bridge failed: " + (e instanceof Error ? e.message : "unknown error") + "\n");
  process.exitCode = 2;
});
