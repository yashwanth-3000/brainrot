"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Github, Menu, X } from "lucide-react";

const NAV_LINKS = [
  { label: "Chat", href: "/chat" },
  { label: "About", href: "/about" },
  { label: "Blog", href: "/blog" },
] as const;

type NavbarProps = {
  collapsed?: boolean;
  collapsedAlign?: "center" | "right";
};

export default function Navbar({ collapsed = false, collapsedAlign = "center" }: NavbarProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const collapsedRight = collapsedAlign === "right";

  const navStyle: React.CSSProperties = {
    backgroundColor: "rgba(18, 15, 30, 0.88)",
    backdropFilter: "blur(14px)",
    WebkitBackdropFilter: "blur(14px)",
    border: "1px solid rgba(255,255,255,0.1)",
    boxShadow: "0 12px 32px -12px rgba(10,8,20,0.55)",
  };

  const linkStyle = (active: boolean): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    borderRadius: "999px",
    padding: "4px 12px",
    fontSize: "10px",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.18em",
    textDecoration: "none",
    color: active ? "#f0ecff" : "#9e9ab8",
    backgroundColor: active ? "rgba(109,91,255,0.22)" : "transparent",
    transition: "color 0.2s, background 0.2s",
  });

  if (collapsed) {
    return (
      <header style={{ pointerEvents: "none", position: "fixed", inset: collapsedRight ? undefined : "0 0 auto 0", right: collapsedRight ? 16 : undefined, top: 16, zIndex: 50, padding: collapsedRight ? undefined : "0 16px", display: "flex", justifyContent: collapsedRight ? "flex-end" : "center" }}>
        <div style={{ pointerEvents: "auto", position: "relative", display: "flex", flexDirection: "column", alignItems: collapsedRight ? "flex-end" : "center" }}>
          {collapsedRight ? (
            <button
              type="button"
              onClick={() => setMenuOpen(o => !o)}
              style={{ ...navStyle, pointerEvents: "auto", width: 44, height: 44, borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "#e8e4ff", cursor: "pointer" }}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
            >
              {menuOpen ? <X size={14} /> : <Menu size={14} />}
            </button>
          ) : (
            <nav style={{ ...navStyle, pointerEvents: "auto", display: "flex", width: 300, maxWidth: "calc(100vw - 2rem)", alignItems: "center", justifyContent: "space-between", borderRadius: 28, padding: "8px 16px" }}>
              <Link href="/" style={{ fontSize: 18, color: "#f0ecff", textDecoration: "none", fontFamily: "var(--font-display, serif)", fontWeight: 400, letterSpacing: "-0.04em", opacity: 1, transition: "opacity 0.2s" }}>
                Draftr
              </Link>
              <button type="button" onClick={() => setMenuOpen(o => !o)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.14)", borderRadius: "50%", padding: 8, color: "#e8e4ff", cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                {menuOpen ? <X size={14} /> : <Menu size={14} />}
              </button>
            </nav>
          )}

          {menuOpen && (
            <div style={{ ...navStyle, pointerEvents: "auto", marginTop: 8, display: "flex", flexDirection: "column", gap: 4, width: collapsedRight ? 220 : 300, maxWidth: "calc(100vw - 2rem)", borderRadius: 16, padding: 8, position: collapsedRight ? "absolute" : "relative", top: collapsedRight ? "calc(100% + 8px)" : undefined, right: collapsedRight ? 0 : undefined, backgroundColor: "rgba(18,15,30,0.96)" }}>
              {collapsedRight && (
                <Link href="/" onClick={() => setMenuOpen(false)} style={{ borderRadius: 12, padding: "8px 12px", fontSize: 16, color: "#f0ecff", textDecoration: "none", fontFamily: "var(--font-display, serif)", fontWeight: 400, letterSpacing: "-0.03em" }}>Draftr</Link>
              )}
              {NAV_LINKS.map(item => (
                <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)} style={{ borderRadius: 12, padding: "8px 12px", fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.18em", textDecoration: "none", color: pathname === item.href ? "#f0ecff" : "#9e9ab8", backgroundColor: pathname === item.href ? "rgba(109,91,255,0.22)" : "transparent" }}>
                  {item.label}
                </Link>
              ))}
              <a href="https://github.com/yashwanth-3000/draftr" target="_blank" rel="noopener noreferrer" onClick={() => setMenuOpen(false)} style={{ marginTop: 4, display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 12, padding: "8px 12px", fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.18em", color: "#9e9ab8", textDecoration: "none" }}>
                <Github size={12} /> GitHub
              </a>
            </div>
          )}
        </div>
      </header>
    );
  }

  return (
    <header style={{ pointerEvents: "none", position: "fixed", inset: "0 0 auto 0", top: 12, zIndex: 50, padding: "0 16px" }}>
      <nav style={{ ...navStyle, pointerEvents: "auto", margin: "0 auto", display: "flex", width: "fit-content", alignItems: "center", gap: 4, borderRadius: 999, padding: "6px 12px" }}>
        <Link href="/" style={{ marginRight: 8, fontSize: 15, color: "#f0ecff", textDecoration: "none", fontFamily: "var(--font-display, serif)", fontWeight: 400, letterSpacing: "-0.04em", transition: "opacity 0.2s" }}>
          Draftr
        </Link>

        {NAV_LINKS.map(item => (
          <Link key={item.href} href={item.href} style={linkStyle(pathname === item.href)}>
            {item.label}
          </Link>
        ))}

        <span style={{ margin: "0 4px", height: 12, width: 1, background: "rgba(255,255,255,0.15)", display: "inline-block" }} />

        <a href="https://github.com/yashwanth-3000/draftr" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", padding: 6, color: "#9e9ab8", textDecoration: "none" }} aria-label="GitHub">
          <Github size={13} />
        </a>
      </nav>
    </header>
  );
}
