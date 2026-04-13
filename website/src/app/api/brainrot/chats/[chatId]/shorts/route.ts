import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ chatId: string }> },
) {
  const { chatId } = await context.params;
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/chats/${chatId}/shorts`), {
    headers: await buildBrainrotProxyHeaders(),
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
