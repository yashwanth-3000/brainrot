import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ batchId: string }> },
) {
  const { batchId } = await context.params;
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/batches/${batchId}`), {
    headers: await buildBrainrotProxyHeaders(),
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
