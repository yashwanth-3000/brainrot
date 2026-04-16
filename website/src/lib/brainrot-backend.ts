import { createClient as createSupabaseServerClient } from "@/lib/supabase/server";

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

export async function buildBrainrotProxyHeaders(headers?: HeadersInit): Promise<Headers> {
  const nextHeaders = new Headers(headers);

  try {
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (user) {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        nextHeaders.set("Authorization", `Bearer ${session.access_token}`);
      }
    }
  } catch {
    // Auth is optional for guest flows, so route handlers can continue without a token.
  }

  return nextHeaders;
}

export function buildVideoRelayResponse(upstream: Response, fallbackContentType: string): Response {
  const headers = new Headers({
    "Cache-Control": "no-store",
    "Content-Type": upstream.headers.get("content-type") ?? fallbackContentType,
  });

  for (const headerName of [
    "accept-ranges",
    "content-length",
    "content-range",
    "etag",
    "last-modified",
  ]) {
    const value = upstream.headers.get(headerName);
    if (value) {
      headers.set(headerName, value);
    }
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  });
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
