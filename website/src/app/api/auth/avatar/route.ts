import { NextRequest, NextResponse } from "next/server";

const ALLOWED_AVATAR_HOSTS = [
  "googleusercontent.com",
  "gstatic.com",
];

function isAllowedAvatarHost(hostname: string) {
  const lowered = hostname.toLowerCase();
  return ALLOWED_AVATAR_HOSTS.some(host => lowered === host || lowered.endsWith(`.${host}`));
}

export async function GET(request: NextRequest) {
  const source = request.nextUrl.searchParams.get("src");
  if (!source) {
    return NextResponse.json({ detail: "Missing avatar source." }, { status: 400 });
  }

  let url: URL;
  try {
    url = new URL(source);
  } catch {
    return NextResponse.json({ detail: "Invalid avatar source." }, { status: 400 });
  }

  if (!["https:", "http:"].includes(url.protocol) || !isAllowedAvatarHost(url.hostname)) {
    return NextResponse.json({ detail: "Avatar host is not allowed." }, { status: 400 });
  }

  const upstream = await fetch(url, {
    headers: {
      "user-agent": "DraftrAvatarProxy/1.0",
      accept: "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    },
    cache: "force-cache",
  });

  if (!upstream.ok) {
    return NextResponse.json({ detail: "Failed to load avatar." }, { status: 502 });
  }

  const contentType = upstream.headers.get("content-type") ?? "image/png";
  const buffer = await upstream.arrayBuffer();

  return new NextResponse(buffer, {
    status: 200,
    headers: {
      "content-type": contentType,
      "cache-control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
