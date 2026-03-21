import { buildBrainrotBackendUrl, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET() {
  const upstream = await fetch(buildBrainrotBackendUrl("/health"), {
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
