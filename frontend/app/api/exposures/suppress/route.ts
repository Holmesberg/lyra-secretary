import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

export const dynamic = "force-dynamic";

const EXPOSURE_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .trim()
    .replace(/\/$/, "");
}

export async function POST(request: NextRequest) {
  let exposureId = "";
  try {
    const body = await request.json();
    exposureId = typeof body?.exposure_id === "string" ? body.exposure_id : "";
  } catch {
    return NextResponse.json({ detail: "invalid_json" }, { status: 400 });
  }
  if (!EXPOSURE_ID_PATTERN.test(exposureId)) {
    return NextResponse.json({ detail: "invalid_exposure_id" }, { status: 400 });
  }

  const sessionToken = await getToken({
    req: request as any,
    secret: process.env.NEXTAUTH_SECRET,
  });
  const backendToken =
    (sessionToken as { backendToken?: string } | null)?.backendToken || "";
  if (!backendToken) {
    return NextResponse.json({ detail: "not_authenticated" }, { status: 401 });
  }

  try {
    const response = await fetch(
      `${apiBase()}/v1/exposures/${encodeURIComponent(exposureId)}/ack/suppress`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${backendToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          suppression_reason: "client_discarded_before_render",
        }),
        cache: "no-store",
      },
    );
    if (!response.ok) {
      return NextResponse.json(
        { detail: "backend_suppression_failed" },
        { status: response.status },
      );
    }
    return new NextResponse(null, { status: 204 });
  } catch {
    return NextResponse.json(
      { detail: "backend_suppression_unavailable" },
      { status: 503 },
    );
  }
}
