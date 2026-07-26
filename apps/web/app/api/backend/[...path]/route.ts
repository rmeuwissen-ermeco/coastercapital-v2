import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { hasValidOrigin } from "@/lib/request-security";

const API_URL =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: Context) {
  const cookieStore = await cookies();
  const token = cookieStore.get("cc_admin_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }
  if (
    !["GET", "HEAD"].includes(request.method) &&
    !hasValidOrigin(request)
  ) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  const { path } = await context.params;
  const target = new URL(`${API_URL}/${path.join("/")}`);
  target.search = request.nextUrl.search;
  const response = await fetch(target, {
    method: request.method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
    cache: "no-store",
  });
  const body = await response.text();
  return new NextResponse(body || null, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
