"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, KeyRound, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";
import Navbar from "@/components/ui/navbar";

import styles from "./login.module.css";

function resolveNextPath(next: string | null) {
  if (!next || !next.startsWith("/") || next.startsWith("/login")) {
    return "/shorts";
  }
  return next;
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginFallback() {
  return (
    <main className={styles.page}>
      <Navbar />
      <section className={styles.shell}>
        <div className={styles.card}>
          <p className={styles.eyebrow}>Account access</p>
          <h1 className={styles.title}>Loading login…</h1>
        </div>
      </section>
    </main>
  );
}

function LoginPageContent() {
  const auth = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = useMemo(() => resolveNextPath(searchParams.get("next")), [searchParams]);
  const authError = searchParams.get("auth") === "error";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false);

  const handleGuestContinue = () => {
    auth.skipLogin();
    router.push(nextPath);
  };

  const handlePasswordLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsPasswordSubmitting(true);
    setPasswordError(null);

    const result = await auth.signInWithPassword(email, password);

    setIsPasswordSubmitting(false);

    if (result) {
      setPasswordError(result);
      return;
    }

    router.push(nextPath);
  };

  return (
    <main className={styles.page}>
      <Navbar />

      <section className={styles.shell}>
        <div className={styles.card}>
          <div className={styles.hero}>
            <p className={styles.eyebrow}>{auth.isAuthenticated ? "Signed in" : "Account access"}</p>
            <h1 className={styles.title}>
              {auth.isAuthenticated ? `You’re already in, ${auth.displayName}.` : "Sign in when you want your own library."}
            </h1>
            <p className={styles.copy}>
              {auth.isAuthenticated
                ? "Open your personal profile or jump back into the app."
                : "Use Google to keep your own shorts, history, and future account insights. If you just want to explore, continue as a guest and use the shared library."}
            </p>
          </div>

          {authError ? (
            <div className={styles.errorCard}>
              Google sign-in did not complete. Try again, and if the issue persists, recheck the Supabase Google provider settings.
            </div>
          ) : null}

          {auth.isAuthenticated ? (
            <div className={styles.actions}>
              <Link href={nextPath} className={styles.primaryAction}>
                Continue
                <ArrowRight size={14} />
              </Link>
              <Link href="/profile" className={styles.secondaryAction}>
                Open profile
              </Link>
            </div>
          ) : (
            <div className={styles.actions}>
              <button type="button" className={styles.primaryAction} onClick={() => void auth.signInWithGoogle(nextPath)}>
                <ShieldCheck size={14} />
                Login with Google
              </button>
              <button type="button" className={styles.secondaryAction} onClick={handleGuestContinue}>
                Continue as guest
              </button>
            </div>
          )}

          {!auth.isAuthenticated ? (
            <form className={styles.passwordCard} onSubmit={handlePasswordLogin}>
              <div className={styles.passwordHeader}>
                <p className={styles.passwordEyebrow}>Test account login</p>
                <h2 className={styles.passwordTitle}>Use email and password for direct Supabase testing.</h2>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel} htmlFor="login-email">Email</label>
                <input
                  id="login-email"
                  type="email"
                  className={styles.fieldInput}
                  autoComplete="email"
                  placeholder="test-auth@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel} htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  className={styles.fieldInput}
                  autoComplete="current-password"
                  placeholder="Enter your test password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              {passwordError ? (
                <div className={styles.inlineError}>{passwordError}</div>
              ) : null}

              <button type="submit" className={styles.passwordSubmit} disabled={isPasswordSubmitting}>
                <KeyRound size={14} />
                {isPasswordSubmitting ? "Signing in..." : "Login with email"}
              </button>
            </form>
          ) : null}

          <div className={styles.footer}>
            <p className={styles.footerCopy}>
              {auth.isAuthenticated
                ? "Your future generations will keep saving to your own library."
                : "Guest mode still works. Signing in simply gives you your own library instead of the shared one."}
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
