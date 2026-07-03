import { NextRequest, NextResponse } from "next/server";
import { execute } from "@/lib/db";

export const dynamic = "force-dynamic";

function isEmail(e: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e);
}

// Capture demand signal: email + which tier/feature they want. No account needed.
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}) as any);
    const email = String(body?.email ?? "").trim().toLowerCase().slice(0, 200);
    const interest = String(body?.interest ?? "general").slice(0, 40);
    const note = String(body?.note ?? "").slice(0, 500);
    const source = String(body?.source ?? "").slice(0, 200);

    if (!isEmail(email)) {
      return NextResponse.json({ error: "Please enter a valid email." }, { status: 400 });
    }

    await execute(
      `INSERT INTO waitlist (email, interest, note, source, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      [email, interest, note, source, new Date().toISOString()],
    );

    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
  }
}
