"use client";

import {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";

import { createClient } from "@/lib/supabase/client";

const GUEST_MODE_STORAGE_KEY = "draftr:guest-mode";
const SUPABASE_GOOGLE_AUTH_ENABLED = process.env.NEXT_PUBLIC_SUPABASE_GOOGLE_AUTH_ENABLED === "true";

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isGuestMode: boolean;
  guestModeChosen: boolean;
  libraryLabel: string;
  displayName: string;
  avatarUrl: string | null;
  scopeKey: string;
  signInWithGoogle: (nextPath?: string) => Promise<void>;
  signInWithPassword: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
  skipLogin: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function extractDisplayName(user: User | null) {
  if (!user) {
    return "Guest";
  }
  const metadata = user.user_metadata ?? {};
  const candidates = [
    metadata.full_name,
    metadata.name,
    metadata.user_name,
    metadata.preferred_username,
    metadata.given_name,
    user.email?.split("@")[0],
  ];
  const match = candidates.find(value => typeof value === "string" && value.trim().length > 0);
  return match?.trim() ?? "User";
}

function extractAvatarUrl(user: User | null) {
  if (!user) {
    return null;
  }
  const metadata = user.user_metadata ?? {};
  const identities = Array.isArray(user.identities) ? user.identities : [];
  const identityCandidates = identities.flatMap(identity => {
    const identityData = identity?.identity_data ?? {};
    return [identityData.avatar_url, identityData.picture, identityData.photo_url];
  });
  const candidates = [metadata.avatar_url, metadata.picture, metadata.photo_url, ...identityCandidates];
  const match = candidates.find(value => typeof value === "string" && value.trim().length > 0);
  return match?.trim() ?? null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [guestModeChosen, setGuestModeChosen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const nextGuestModeChosen = window.localStorage.getItem(GUEST_MODE_STORAGE_KEY) === "1";
    const frame = window.requestAnimationFrame(() => {
      setGuestModeChosen(nextGuestModeChosen);
    });
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadUser() {
      const { data } = await supabase.auth.getUser();
      if (!mounted) {
        return;
      }
      setUser(data.user ?? null);
      if (data.user && typeof window !== "undefined") {
        window.localStorage.removeItem(GUEST_MODE_STORAGE_KEY);
        setGuestModeChosen(false);
      }
      setIsLoading(false);
    }

    void loadUser();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user && typeof window !== "undefined") {
        window.localStorage.removeItem(GUEST_MODE_STORAGE_KEY);
        setGuestModeChosen(false);
      }
      setIsLoading(false);
      startTransition(() => {
        router.refresh();
      });
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [router, supabase]);

  const signInWithGoogle = useCallback(async (nextPath?: string) => {
    const next = nextPath ?? (typeof window !== "undefined" ? `${window.location.pathname}${window.location.search}` : "/shorts");
    const loginErrorPath = `/login?auth=error&next=${encodeURIComponent(next)}`;
    if (!SUPABASE_GOOGLE_AUTH_ENABLED) {
      startTransition(() => {
        router.push(loginErrorPath);
      });
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        skipBrowserRedirect: true,
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        queryParams: {
          access_type: "offline",
          prompt: "select_account",
        },
      },
    });
    if (error || !data?.url) {
      startTransition(() => {
        router.push(loginErrorPath);
      });
      return;
    }
    window.location.assign(data.url);
  }, [router, supabase]);

  const signInWithPassword = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim();
    const normalizedPassword = password.trim();
    if (!normalizedEmail || !normalizedPassword) {
      return "Enter both your email and password."
    }

    const { error } = await supabase.auth.signInWithPassword({
      email: normalizedEmail,
      password: normalizedPassword,
    });

    if (error) {
      return error.message;
    }

    return null;
  }, [supabase]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(GUEST_MODE_STORAGE_KEY, "1");
    }
    setGuestModeChosen(true);
    setUser(null);
    startTransition(() => {
      router.refresh();
    });
  }, [router, supabase]);

  const skipLogin = useCallback(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(GUEST_MODE_STORAGE_KEY, "1");
    }
    setGuestModeChosen(true);
    startTransition(() => {
      router.refresh();
    });
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: Boolean(user),
      isGuestMode: !user,
      guestModeChosen,
      libraryLabel: user ? "Your library" : "General library",
      displayName: extractDisplayName(user),
      avatarUrl: extractAvatarUrl(user),
      scopeKey: user ? `user:${user.id}` : guestModeChosen ? "guest:chosen" : "guest",
      signInWithGoogle,
      signInWithPassword,
      signOut,
      skipLogin,
    }),
    [guestModeChosen, isLoading, signInWithGoogle, signInWithPassword, signOut, skipLogin, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
