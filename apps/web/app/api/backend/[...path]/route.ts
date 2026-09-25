import { NextRequest, NextResponse } from "next/server";

const allowed: Record<string, string[]> = {
  "auth/login": ["POST"],
  "auth/register": ["POST"],
  "auth/me": ["GET"],
  "auth/logout": ["POST"],
  "auth/password": ["POST"],
  dashboard: ["GET"],
  users: ["GET", "POST"],
  "system/companies": ["GET", "POST"],
};

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  const methods =
    allowed[path] ??
    (/^users\/[0-9a-f-]{36}$/.test(path)
      ? ["PATCH"]
      : path === "forms"
        ? ["GET", "POST"]
        : /^form-versions\/[0-9a-f-]{36}(\/(fields|field-order|publish|clone))?$/.test(path)
          ? path.endsWith("field-order") ? ["PUT"] : path.match(/\/(fields|publish|clone)$/) ? ["POST"] : ["GET"]
          : []);
  if (!methods.includes(request.method))
    return new NextResponse(null, { status: 404 });
  // NextURL canonicalizes loopback IPs; Host preserves the browser's actual origin.
  const expectedOrigin = process.env.APP_ORIGIN ?? `${request.nextUrl.protocol}//${request.headers.get("host")}`;
  if (
    request.method !== "GET" &&
    request.headers.get("origin") !== expectedOrigin
  ) {
    return NextResponse.json(
      { error: { code: "invalid_origin" } },
      { status: 403 },
    );
  }
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = request.cookies.get("frotad_session")?.value;
  const company = request.cookies.get("frotad_company")?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (company) headers.set("X-Company-ID", company);
  const body = request.method === "GET" ? undefined : await request.text();
  if (body && body.length > 16000)
    return new NextResponse(null, { status: 413 });
  try {
    const upstream = await fetch(
      `${process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/${path}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: body || undefined,
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      },
    );
    const data = upstream.status === 204 ? null : await upstream.json();
    const successfulLogin =
      upstream.ok && (path === "auth/login" || path === "auth/register");
    const accessToken = successfulLogin ? data.access_token : null;
    if (successfulLogin) delete data.access_token;
    const response =
      data === null
        ? new NextResponse(null, { status: upstream.status })
        : NextResponse.json(data, { status: upstream.status });
    response.headers.set("Cache-Control", "no-store");
    if (successfulLogin) {
      const options = {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict" as const,
        path: "/",
        expires: new Date(data.expires_at),
      };
      response.cookies.set("frotad_session", accessToken, options);
      if (data.company_id)
        response.cookies.set("frotad_company", data.company_id, options);
      else response.cookies.delete("frotad_company");
    }
    if (
      (path === "auth/logout" || path === "auth/password") &&
      (upstream.ok || upstream.status === 401)
    ) {
      response.cookies.delete("frotad_session");
      response.cookies.delete("frotad_company");
    }
    return response;
  } catch {
    return NextResponse.json(
      { error: { code: "api_unavailable" } },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH };
