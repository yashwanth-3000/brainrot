import { buildBrainrotBackendUrl, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ chatId: string }> },
) {
  const { chatId } = await context.params;
  const upstream = await fetch(buildBrainrotBackendUrl(`/v1/chats/${chatId}`), {
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
