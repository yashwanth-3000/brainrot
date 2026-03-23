const LOCAL_BACKEND_URL = "http://127.0.0.1:8000";

function resolveBrainrotBackendBaseUrl(): string {
  const configuredUrl = process.env.BRAINROT_BACKEND_URL?.trim();
  if (configuredUrl) {
    return configuredUrl;
  }

  if (process.env.NODE_ENV !== "production") {
    return LOCAL_BACKEND_URL;
  }

  throw new Error(
    "BRAINROT_BACKEND_URL is required in production. Set it to the deployed backend service URL.",
  );
}

export function buildBrainrotBackendUrl(path: string): URL {
  const baseUrl = resolveBrainrotBackendBaseUrl();
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
