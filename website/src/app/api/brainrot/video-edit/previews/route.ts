import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const payload = await request.text();
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/video-edit/previews"), {
    method: "POST",
    body: payload,
    cache: "no-store",
    headers: await buildBrainrotProxyHeaders({
      "Content-Type": "application/json",
    }),
  });
  return relayJsonResponse(upstream);
}
