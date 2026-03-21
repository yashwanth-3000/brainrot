import { buildBrainrotBackendUrl } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ batchId: string; itemId: string }> },
) {
  const { batchId, itemId } = await context.params;
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/batches/${batchId}/items/${itemId}/video`), {
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

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "video/mp4",
      "Cache-Control": "no-store",
    },
  });
}
