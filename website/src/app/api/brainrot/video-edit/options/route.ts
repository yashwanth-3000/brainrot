import { buildBrainrotBackendUrl, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET() {
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/video-edit/options"), {
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
