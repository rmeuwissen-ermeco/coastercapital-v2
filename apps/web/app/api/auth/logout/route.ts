import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete("cc_admin_session");
  return NextResponse.json({ ok: true });
}
