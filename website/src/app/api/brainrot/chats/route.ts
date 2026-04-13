import { buildBrainrotBackendUrl, buildBrainrotProxyHeaders, relayJsonResponse } from "@/lib/brainrot-backend";

export const runtime = "nodejs";

export async function GET() {
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/chats"), {
    headers: await buildBrainrotProxyHeaders(),
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}

export async function POST(request: Request) {
  const body = await request.text();
  const upstream = await fetch(buildBrainrotBackendUrl("/v1/chats"), {
    method: "POST",
    headers: await buildBrainrotProxyHeaders({
      "Content-Type": "application/json",
    }),
    body,
    cache: "no-store",
  });
  return relayJsonResponse(upstream);
}
