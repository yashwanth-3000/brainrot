import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const formData = await request.formData();
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/batches"), {
    method: "POST",
    headers: await buildBrainrotProxyHeaders(),
    body: formData,
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
