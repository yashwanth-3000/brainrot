import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

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

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    requireSupabaseUrl(),
    requireSupabasePublishableKey(),
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // Server Components and some Route Handler contexts are read-only.
          }
        },
      },
    },
  );
}
