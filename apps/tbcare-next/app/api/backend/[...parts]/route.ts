import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
// This optional adapter can ONLY be used on the developer's own loopback machine.
// There are no public-health-system integrations or arbitrary SQL operations here.
const ID = /^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$/;
const SNAPSHOT = /^[a-f0-9]{64}$/;
const BACKEND = "http://127.0.0.1:8765";
function pathFor(parts: string[], method: string): string | null {
  if (method === "GET" && parts.join("/") === "cases") return "/api/cases";
  if (method === "GET" && parts.join("/") === "review-activity") return "/api/review-activity";
  if (parts.length !== 3 || parts[0] !== "cases" || !ID.test(parts[1])) return null;
  const a = parts[2];
  if (method === "GET" && ["evidence", "reviews", "audit", "activity"].includes(a)) return `/api/cases/${parts[1]}/${a}`;
  if (method === "POST" && ["explain", "plan", "reviews"].includes(a)) return `/api/cases/${parts[1]}/${a}`;
  return null;
}
async function handler(req: NextRequest, ctx: { params: Promise<{ parts: string[] }> }, method: "GET" | "POST") {
  const host = req.headers.get("host") ?? "";
  if (process.env.TBCARE_ENABLE_LOCAL_PROXY !== "1" || process.env.NEXT_PUBLIC_TBCARE_MODE !== "local" || !/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host))
    return NextResponse.json({ error: "Local-only backend proxy is disabled.", error_code: "local_proxy_disabled" }, { status: 403 });
  // Reject cross-site POSTs even if a browser targets localhost through a
  // guessed/forged Host header. This is a local-only demonstration bridge.
  if (method === "POST") {
    const origin = req.headers.get("origin");
    if (origin !== `http://${host}`) {
      return NextResponse.json({ error: "Cross-origin mutation request rejected", error_code: "origin_rejected" }, { status: 403 });
    }
  }
  const { parts } = await ctx.params;
  const route = pathFor(parts, method);
  if (!route) return NextResponse.json({ error: "Unknown allowlisted route", error_code: "unsupported_route" }, { status: 404 });
  const headers: Record<string, string> = { "Accept": "application/json" };
  let body: string | undefined;
  if (method === "POST" && parts[2] !== "reviews") {
    if (req.headers.get("content-length") && req.headers.get("content-length") !== "0") {
      return NextResponse.json({ error: "Agent endpoints accept no body", error_code: "agent_body_rejected" }, { status: 400 });
    }
    const digest = req.headers.get("X-TBCareOS-Evidence-SHA256") ?? "";
    if (!SNAPSHOT.test(digest)) return NextResponse.json({ error: "Evidence digest is missing or invalid.", error_code: "snapshot_required" }, { status: 400 });
    headers["X-TBCareOS-Evidence-SHA256"] = digest;
  }
  if (method === "POST" && parts[2] === "reviews") {
    const type = (req.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
    if (type !== "application/json") return NextResponse.json({ error: "JSON review body required", error_code: "review_content_type" }, { status: 415 });
    if (req.headers.get("X-TBCareOS-Review-Intent") !== "record-human-admin-review-v1")
      return NextResponse.json({ error: "Explicit review intent is required", error_code: "review_intent_required" }, { status: 400 });
    body = await req.text();
    if (new TextEncoder().encode(body).length > 4096) return NextResponse.json({ error: "Review exceeds local limit", error_code: "review_too_large" }, { status: 413 });
    headers["Content-Type"] = "application/json";
    headers["Origin"] = BACKEND;
    headers["X-TBCareOS-Review-Intent"] = "record-human-admin-review-v1";
  }
  try {
    const upstream = await fetch(BACKEND + route, { method, headers, body, cache: "no-store", signal: AbortSignal.timeout(65000) });
    const json = await upstream.json();
    return NextResponse.json(json, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Local Python API unavailable or returned unreadable JSON.", error_code: "local_api_unavailable", next_step: "Check the trusted local Zetaris/Python process at 127.0.0.1:8765." }, { status: 503 });
  }
}
export async function GET(req: NextRequest, ctx: { params: Promise<{ parts: string[] }> }) { return handler(req, ctx, "GET"); }
export async function POST(req: NextRequest, ctx: { params: Promise<{ parts: string[] }> }) { return handler(req, ctx, "POST"); }
