"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Github, Menu, X } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import UserAvatar from "@/components/ui/user-avatar";

const NAV_LINKS = [
  { label: "Chat", href: "/chat" },
  { label: "Shorts", href: "/shorts" },
  { label: "About", href: "/about" },
] as const;

type NavbarProps = {
  collapsed?: boolean;
  collapsedAlign?: "center" | "right";
};

export default function Navbar({ collapsed = false, collapsedAlign = "center" }: NavbarProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const auth = useAuth();
  const collapsedRight = collapsedAlign === "right";
  const compactDisplayName = auth.displayName.trim().split(/\s+/)[0] ?? auth.displayName;
  const loginHref = pathname === "/login" ? "/login" : `/login?next=${encodeURIComponent(pathname)}`;
  const showLoginAction = !auth.isAuthenticated && pathname !== "/login";

  const navStyle: React.CSSProperties = {
    background:
      "linear-gradient(135deg, rgba(24, 19, 38, 0.9), rgba(33, 25, 50, 0.82))",
    backdropFilter: "blur(18px)",
    WebkitBackdropFilter: "blur(18px)",
    border: "1px solid rgba(255,255,255,0.08)",
    boxShadow: "0 20px 38px -24px rgba(16, 12, 30, 0.72), inset 0 1px 0 rgba(255,255,255,0.06)",
  };

  const linkStyle = (active: boolean): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    borderRadius: "999px",
    padding: active ? "5px 11px" : "5px 10px",
    fontSize: "9px",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    textDecoration: "none",
    color: active ? "#f0ecff" : "#9e9ab8",
    backgroundColor: active ? "rgba(122,103,255,0.18)" : "transparent",
    transition: "color 0.2s, background 0.2s, transform 0.2s",
  });

  const authButtonStyle = (primary: boolean): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    borderRadius: 999,
    padding: "5px 11px",
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    textDecoration: "none",
    border: primary ? "1px solid rgba(109,91,255,0.32)" : "1px solid rgba(255,255,255,0.12)",
    background: primary ? "linear-gradient(135deg, rgba(109,91,255,0.42), rgba(82,53,239,0.22))" : "rgba(255,255,255,0.04)",
    color: primary ? "#f5f1ff" : "#c4bfdc",
    cursor: "pointer",
  });

  const profileLinkStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "0 2px",
    borderRadius: 0,
    textDecoration: "none",
    border: "none",
    background: "transparent",
    color: "#f0ecff",
    minWidth: 0,
  };

  const profileNameStyle: React.CSSProperties = {
    maxWidth: 78,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "#d7d1f0",
  };

  if (collapsed) {
    return (
      <header
        style={{
          pointerEvents: "none",
          position: "fixed",
          inset: collapsedRight ? undefined : "0 0 auto 0",
          right: collapsedRight ? 16 : undefined,
          top: 16,
          zIndex: 50,
          padding: collapsedRight ? undefined : "0 16px",
          display: "flex",
          justifyContent: collapsedRight ? "flex-end" : "center",
        }}
      >
        <div
          style={{
            pointerEvents: "auto",
            position: "relative",
            display: "flex",
            flexDirection: "column",
            alignItems: collapsedRight ? "flex-end" : "center",
          }}
        >
          {collapsedRight ? (
            <button
              type="button"
              onClick={() => setMenuOpen(open => !open)}
              style={{
                ...navStyle,
                width: 44,
                height: 44,
                borderRadius: "50%",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#e8e4ff",
                cursor: "pointer",
              }}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
            >
              {menuOpen ? <X size={14} /> : <Menu size={14} />}
            </button>
          ) : (
            <nav
              style={{
                ...navStyle,
                display: "flex",
                width: 300,
                maxWidth: "calc(100vw - 2rem)",
                alignItems: "center",
                justifyContent: "space-between",
                borderRadius: 28,
                padding: "8px 16px",
              }}
            >
              <Link
                href="/"
                style={{
                  fontSize: 18,
                  color: "#f0ecff",
                  textDecoration: "none",
                  fontFamily: "var(--font-display, serif)",
                  fontWeight: 400,
                  letterSpacing: "-0.04em",
                }}
              >
                Draftr
              </Link>
              <button
                type="button"
                onClick={() => setMenuOpen(open => !open)}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: "50%",
                  padding: 8,
                  color: "#e8e4ff",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {menuOpen ? <X size={14} /> : <Menu size={14} />}
              </button>
            </nav>
          )}

          {menuOpen ? (
            <div
              style={{
                ...navStyle,
                marginTop: 8,
                display: "flex",
                flexDirection: "column",
                gap: 4,
                width: collapsedRight ? 232 : 300,
                maxWidth: "calc(100vw - 2rem)",
                borderRadius: 16,
                padding: 8,
                position: collapsedRight ? "absolute" : "relative",
                top: collapsedRight ? "calc(100% + 8px)" : undefined,
                right: collapsedRight ? 0 : undefined,
                backgroundColor: "rgba(18,15,30,0.96)",
              }}
            >
              {collapsedRight ? (
                <Link
                  href="/"
                  onClick={() => setMenuOpen(false)}
                  style={{
                    borderRadius: 12,
                    padding: "8px 12px",
                    fontSize: 16,
                    color: "#f0ecff",
                    textDecoration: "none",
                    fontFamily: "var(--font-display, serif)",
                    fontWeight: 400,
                    letterSpacing: "-0.03em",
                  }}
                >
                  Draftr
                </Link>
              ) : null}

              {NAV_LINKS.map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    borderRadius: 12,
                    padding: "8px 12px",
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.18em",
                    textDecoration: "none",
                    color: pathname === item.href ? "#f0ecff" : "#9e9ab8",
                    backgroundColor: pathname === item.href ? "rgba(109,91,255,0.22)" : "transparent",
                  }}
                >
                  {item.label}
                </Link>
              ))}

              {auth.isAuthenticated ? (
                <Link
                  href="/profile"
                  onClick={() => setMenuOpen(false)}
                  style={{
                    marginTop: 4,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 12px",
                    borderRadius: 14,
                    textDecoration: "none",
                    color: "#f0ecff",
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <UserAvatar name={auth.displayName} avatarUrl={auth.avatarUrl} size={34} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {auth.displayName}
                    </div>
                    <div style={{ marginTop: 2, fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "#9e9ab8" }}>
                      Profile
                    </div>
                  </div>
                </Link>
              ) : showLoginAction ? (
                <Link
                  href={loginHref}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    ...authButtonStyle(true),
                    marginTop: 4,
                    padding: "8px 12px",
                  }}
                >
                  Login
                </Link>
              ) : null}

              <a
                href="https://github.com/yashwanth-3000/draftr"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMenuOpen(false)}
                style={{
                  marginTop: 4,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  borderRadius: 12,
                  padding: "8px 12px",
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.18em",
                  color: "#9e9ab8",
                  textDecoration: "none",
                }}
              >
                <Github size={12} /> GitHub
              </a>
            </div>
          ) : null}
        </div>
      </header>
    );
  }

  return (
    <header style={{ pointerEvents: "none", position: "fixed", inset: "0 0 auto 0", top: 9, zIndex: 50, padding: "0 14px" }}>
      <nav
        style={{
          ...navStyle,
          pointerEvents: "auto",
          margin: "0 auto",
          display: "flex",
          width: "fit-content",
          alignItems: "center",
          gap: 1,
          borderRadius: 999,
          minHeight: 42,
          padding: "3px 10px",
        }}
      >
        <Link
          href="/"
          style={{
            marginRight: 5,
            fontSize: 14,
            color: "#f0ecff",
            textDecoration: "none",
            fontFamily: "var(--font-display, serif)",
            fontWeight: 400,
            letterSpacing: "-0.04em",
          }}
        >
          Draftr
        </Link>

        {NAV_LINKS.map(item => (
          <Link key={item.href} href={item.href} style={linkStyle(pathname === item.href)}>
            {item.label}
          </Link>
        ))}

        <span style={{ margin: "0 3px", height: 9, width: 1, background: "rgba(255,255,255,0.12)", display: "inline-block" }} />

        <a
          href="https://github.com/yashwanth-3000/draftr"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "50%",
            width: 22,
            height: 22,
            color: "#9e9ab8",
            textDecoration: "none",
          }}
          aria-label="GitHub"
        >
          <Github size={10} />
        </a>

        <span style={{ margin: "0 3px", height: 9, width: 1, background: "rgba(255,255,255,0.12)", display: "inline-block" }} />

        {auth.isAuthenticated ? (
          <Link href="/profile" style={profileLinkStyle} aria-label="Profile" title="Profile">
            <span style={profileNameStyle}>{compactDisplayName}</span>
            <UserAvatar name={auth.displayName} avatarUrl={auth.avatarUrl} size={22} />
          </Link>
        ) : showLoginAction ? (
          <Link href={loginHref} style={authButtonStyle(true)}>
            Login
          </Link>
        ) : null}
      </nav>
    </header>
  );
}
