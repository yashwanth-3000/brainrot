import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, buildVideoRelayResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  request: Request,
  context: { params: Promise<{ batchId: string }> },
) {
  const { batchId } = await context.params;
  const headers = await buildBrainrotProxyHeaders();
  const rangeHeader = request.headers.get("range");
  const ifRangeHeader = request.headers.get("if-range");
  if (rangeHeader) {
    headers.set("Range", rangeHeader);
  }
  if (ifRangeHeader) {
    headers.set("If-Range", ifRangeHeader);
  }
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/video-edit/previews/${batchId}/video`), {
    headers,
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  }

  return buildVideoRelayResponse(upstream, "video/mp4");
}
