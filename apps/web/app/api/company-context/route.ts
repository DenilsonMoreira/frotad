import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const expectedOrigin = process.env.APP_ORIGIN ?? `${request.nextUrl.protocol}//${request.headers.get("host")}`;
  if (request.headers.get("origin") !== expectedOrigin) return new NextResponse(null, { status: 403 });
  const { company_id: company } = await request.json();
  if (typeof company !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(company)) {
    return new NextResponse(null, { status: 422 });
  }
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set("frotad_company", company, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/",
  });
  return response;
}
