import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  request: Request,
  context: { params: Promise<{ batchId: string }> },
) {
  const { batchId } = await context.params;
  const headers = await buildBrainrotProxyHeaders({
    Accept: "text/event-stream",
    "Cache-Control": "no-cache",
    ...(request.headers.get("last-event-id")
      ? { "Last-Event-ID": request.headers.get("last-event-id") as string }
      : {}),
  });
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/batches/${batchId}/events`), {
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

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
