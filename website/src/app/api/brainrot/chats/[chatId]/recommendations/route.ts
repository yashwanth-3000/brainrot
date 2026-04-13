import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  request: Request,
  context: { params: Promise<{ chatId: string }> },
) {
  const { chatId } = await context.params;
  const url = new URL(request.url)
  const sessionId = url.searchParams.get("session_id")
  const search = new URLSearchParams()
  if (sessionId) {
    search.set("session_id", sessionId)
  }

  const suffix = search.toString()
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/chats/${encodeURIComponent(chatId)}/recommendations${suffix ? `?${suffix}` : ""}`), {
    headers: await buildBrainrotProxyHeaders(),
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
