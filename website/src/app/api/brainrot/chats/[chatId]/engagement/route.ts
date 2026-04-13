import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function POST(
  request: Request,
  context: { params: Promise<{ chatId: string }> },
) {
  const { chatId } = await context.params;
  const body = await request.text();
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/chats/${encodeURIComponent(chatId)}/engagement`), {
    method: "POST",
    headers: await buildBrainrotProxyHeaders({
      "Content-Type": "application/json",
    }),
    body,
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
