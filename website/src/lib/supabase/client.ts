import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
const SUPABASE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();

function requireSupabaseUrl() {
  if (!SUPABASE_URL) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL is required to use Supabase authentication.");
  }
  return SUPABASE_URL;
}

function requireSupabasePublishableKey() {
  if (!SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY is required to use Supabase authentication.");
  }
  return SUPABASE_PUBLISHABLE_KEY;
}

export function createClient() {
  if (browserClient) {
    return browserClient;
  }

  browserClient = createBrowserClient(
    requireSupabaseUrl(),
    requireSupabasePublishableKey(),
  );
  return browserClient;
}
