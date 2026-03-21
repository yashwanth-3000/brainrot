const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function buildBrainrotBackendUrl(path: string): URL {
  const baseUrl = process.env.BRAINROT_BACKEND_URL ?? DEFAULT_BACKEND_URL;
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  return new URL(normalizedPath, normalizedBase);
}

export async function relayJsonResponse(upstream: Response): Promise<Response> {
  const payload = await upstream.text();
  return new Response(payload || "{}", {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}
