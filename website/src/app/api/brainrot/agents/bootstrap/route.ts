import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function POST() {
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/agents/bootstrap"), {
    method: "POST",
    headers: await buildBrainrotProxyHeaders(),
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
