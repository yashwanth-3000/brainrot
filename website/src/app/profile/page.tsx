"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, LogOut, Sparkles } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import UserAvatar from "@/components/ui/user-avatar";
import Navbar from "@/components/ui/navbar";

import styles from "./profile.module.css";

type ChatSummary = {
  id: string;
  title: string;
  updated_at: string;
  last_source_label: string | null;
  total_runs: number;
  total_exported: number;
  total_failed: number;
};

type ChatListResponse = {
  items: ChatSummary[];
};

type LibraryState = "loading" | "ready" | "error";

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Recently";
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return "Recently";
  }
}

export default function ProfilePage() {
  const auth = useAuth();
  const [libraryState, setLibraryState] = useState<LibraryState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [chats, setChats] = useState<ChatSummary[]>([]);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      setChats([]);
      setLibraryState("ready");
      setError(null);
      return;
    }

    const controller = new AbortController();

    async function loadChats() {
      setLibraryState("loading");
      setError(null);
      try {
        const response = await fetch("/api/brainrot/chats", {
          cache: "no-store",
          signal: controller.signal,
        });
        const payload = (await response.json()) as ChatListResponse & { detail?: string };
        if (!response.ok) {
          throw new Error(payload.detail ?? "Failed to load your account activity.");
        }
        if (!controller.signal.aborted) {
          setChats(payload.items);
          setLibraryState("ready");
        }
      } catch (nextError) {
        if (controller.signal.aborted) {
          return;
        }
        setLibraryState("error");
        setError(nextError instanceof Error ? nextError.message : "Failed to load your account activity.");
      }
    }

    void loadChats();

    return () => controller.abort();
  }, [auth.isAuthenticated]);

  const stats = useMemo(() => {
    const totalShorts = chats.reduce((sum, chat) => sum + chat.total_exported, 0);
    const totalRuns = chats.reduce((sum, chat) => sum + chat.total_runs, 0);
    const totalFailed = chats.reduce((sum, chat) => sum + chat.total_failed, 0);

    return [
      { label: "Saved shorts", value: totalShorts, accent: "Your rendered MP4s in the personal library" },
      { label: "Generation runs", value: totalRuns, accent: "Total backend generation attempts on your account" },
      { label: "Active chats", value: chats.length, accent: "Distinct source threads saved under this profile" },
      { label: "Failed runs", value: totalFailed, accent: "Runs that still need another pass or retry" },
    ];
  }, [chats]);

  const providerLabel = useMemo(() => {
    const providers = auth.user?.app_metadata?.providers;
    if (Array.isArray(providers) && providers.length > 0) {
      return providers.join(", ");
    }
    return auth.isAuthenticated ? "google" : "guest";
  }, [auth.isAuthenticated, auth.user?.app_metadata?.providers]);

  const recentChats = chats.slice(0, 4);

  return (
    <main className={styles.page}>
      <Navbar />

      <section className={styles.shell}>
        <div className={styles.hero}>
          <div className={styles.identity}>
            <UserAvatar name={auth.displayName} avatarUrl={auth.avatarUrl} size={84} />
            <div className={styles.identityCopy}>
              <p className={styles.eyebrow}>{auth.isAuthenticated ? "Google account" : "Guest mode"}</p>
              <h1 className={styles.title}>{auth.isAuthenticated ? auth.displayName : "Keep exploring as a guest"}</h1>
              <p className={styles.subtitle}>
                {auth.isAuthenticated
                  ? auth.user?.email ?? "Signed in"
                  : "Sign in with Google if you want a personal library and account-level history."}
              </p>
            </div>
          </div>

          <div className={styles.heroActions}>
            {auth.isAuthenticated ? (
              <>
                <Link href="/shorts" className={styles.primaryAction}>
                  Open your library
                  <ArrowRight size={14} />
                </Link>
                <button type="button" className={styles.secondaryAction} onClick={() => void auth.signOut()}>
                  <LogOut size={14} />
                  Log out
                </button>
              </>
            ) : (
              <>
                <button type="button" className={styles.primaryAction} onClick={() => void auth.signInWithGoogle("/profile")}>
                  Sign in with Google
                  <ArrowRight size={14} />
                </button>
                <Link href="/shorts" className={styles.secondaryAction}>
                  Browse general library
                </Link>
              </>
            )}
          </div>
        </div>

        {auth.isAuthenticated ? (
          <>
            <section className={styles.grid}>
              {stats.map(stat => (
                <article key={stat.label} className={styles.statCard}>
                  <p className={styles.statLabel}>{stat.label}</p>
                  <p className={styles.statValue}>{stat.value}</p>
                  <p className={styles.statAccent}>{stat.accent}</p>
                </article>
              ))}
            </section>

            <section className={styles.columns}>
              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelEyebrow}>Account</p>
                    <h2 className={styles.panelTitle}>Profile details</h2>
                  </div>
                  <span className={styles.providerBadge}>{providerLabel}</span>
                </div>

                <dl className={styles.metaList}>
                  <div className={styles.metaRow}>
                    <dt>Name</dt>
                    <dd>{auth.displayName}</dd>
                  </div>
                  <div className={styles.metaRow}>
                    <dt>Email</dt>
                    <dd>{auth.user?.email ?? "Hidden"}</dd>
                  </div>
                  <div className={styles.metaRow}>
                    <dt>Member since</dt>
                    <dd>{formatDate(auth.user?.created_at)}</dd>
                  </div>
                  <div className={styles.metaRow}>
                    <dt>Library scope</dt>
                    <dd>Personal</dd>
                  </div>
                </dl>
              </article>

              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelEyebrow}>Recent activity</p>
                    <h2 className={styles.panelTitle}>Latest saved chats</h2>
                  </div>
                  <Sparkles size={16} color="#6d5bff" />
                </div>

                {libraryState === "loading" ? (
                  <p className={styles.panelCopy}>Loading your latest saved generations.</p>
                ) : libraryState === "error" ? (
                  <p className={styles.panelCopy}>{error}</p>
                ) : recentChats.length > 0 ? (
                  <div className={styles.activityList}>
                    {recentChats.map(chat => (
                      <Link key={chat.id} href={`/shorts?chat=${chat.id}`} className={styles.activityItem}>
                        <div>
                          <p className={styles.activityTitle}>{chat.title}</p>
                          <p className={styles.activityMeta}>
                            {chat.last_source_label ?? "Source"} · {formatDate(chat.updated_at)}
                          </p>
                        </div>
                        <span className={styles.activityCount}>{chat.total_exported} saved</span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className={styles.panelCopy}>Your personal library is empty right now. Generate your first batch from chat.</p>
                )}
              </article>
            </section>
          </>
        ) : (
          <section className={styles.guestPanel}>
            <p className={styles.panelEyebrow}>Why sign in</p>
            <h2 className={styles.panelTitle}>Turn guest browsing into a personal library.</h2>
            <p className={styles.panelCopy}>
              Guests can still use Drafter, but signing in keeps your shorts, generations, and future account insights under
              your own profile instead of the shared general library.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}
