"use client";

import { useMemo, useState } from "react";

type UserAvatarProps = {
  name: string;
  avatarUrl?: string | null;
  size?: number;
};

function getInitials(name: string) {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) {
    return "D";
  }

  return parts.map(part => part[0]?.toUpperCase() ?? "").join("") || "D";
}

export default function UserAvatar({ name, avatarUrl, size = 36 }: UserAvatarProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const initials = useMemo(() => getInitials(name), [name]);
  const resolvedAvatarUrl = useMemo(() => {
    if (!avatarUrl) {
      return null;
    }
    if (avatarUrl.startsWith("/")) {
      return avatarUrl;
    }
    return `/api/auth/avatar?src=${encodeURIComponent(avatarUrl)}`;
  }, [avatarUrl]);
  const showImage = Boolean(resolvedAvatarUrl && !imageFailed);

  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        overflow: "hidden",
        flexShrink: 0,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        border: "1px solid rgba(255,255,255,0.16)",
        background: "linear-gradient(135deg, rgba(109,91,255,0.45), rgba(58,35,150,0.9))",
        color: "#f8f6ff",
        fontSize: Math.max(11, Math.round(size * 0.34)),
        fontWeight: 700,
        letterSpacing: "0.04em",
        boxShadow: "0 10px 24px -16px rgba(82,53,239,0.85)",
      }}
      aria-hidden="true"
    >
      {showImage ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={resolvedAvatarUrl ?? undefined}
          alt=""
          onError={() => setImageFailed(true)}
          referrerPolicy="no-referrer"
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        initials
      )}
    </span>
  );
}
