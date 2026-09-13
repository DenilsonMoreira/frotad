// Test-only upstream. Never imported by application code.
import { createServer } from "node:http";
const company = "11111111-1111-1111-1111-111111111111";
const sessions = new Map();
createServer(async (req, res) => {
  const send = (status, data) => {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(data === undefined ? undefined : JSON.stringify(data));
  };
  if (req.url === "/health") return send(200, {});
  let raw = "";
  for await (const part of req) raw += part;
  const payload = raw ? JSON.parse(raw) : {};
  if (req.url === "/api/v1/auth/login" || req.url === "/api/v1/auth/register") {
    if (payload.password !== "Frase de teste segura 123")
      return send(401, { error: { code: "invalid_credentials" } });
    const system = payload.email === "system@example.test";
    const token = crypto.randomUUID();
    const session = {
      company_id: system ? null : company,
      company_name: system ? null : "Empresa teste",
      is_system_admin: system,
      user: {
        id: crypto.randomUUID(),
        name: "Administrador teste",
        email: payload.email,
        role: system ? null : "OWNER",
        active: true,
      },
    };
    sessions.set(token, session);
    return send(200, {
      ...session,
      access_token: token,
      expires_at: new Date(Date.now() + 3600000).toISOString(),
    });
  }
  const token = req.headers.authorization?.replace("Bearer ", "");
  const session = sessions.get(token);
  if (!session) return send(401, { error: { code: "invalid_credentials" } });
  if (req.url === "/api/v1/auth/me") return send(200, session);
  if (req.url === "/api/v1/auth/logout") {
    sessions.delete(token);
    return send(204);
  }
  if (req.url.startsWith("/api/v1/system/companies")) {
    if (!session.is_system_admin)
      return send(403, { error: { code: "system_admin_required" } });
    return send(
      req.method === "POST" ? 201 : 200,
      req.method === "POST"
        ? { id: company, name: payload.company_name }
        : [
            {
              id: company,
              name: "Empresa teste",
              slug: "empresa-teste",
              timezone: "America/Fortaleza",
            },
          ],
    );
  }
  if (req.headers["x-company-id"] !== company)
    return send(403, { error: { code: "membership_required" } });
  if (req.url.startsWith("/api/v1/users"))
    return send(
      req.method === "POST" ? 201 : 200,
      req.method === "POST"
        ? { id: crypto.randomUUID(), ...payload, password: undefined }
        : [session.user],
    );
  if (req.url.startsWith("/api/v1/dashboard")) {
    const metrics = {
      day: "2026-09-13",
      missing_measurements: 0,
      trips: 0,
      volume_m3: "0",
      diesel_liters: "0",
      liters_per_m3: null,
    };
    return send(200, {
      company: "Empresa teste",
      timezone: "America/Fortaleza",
      server_time: "2026-09-13T12:00:00Z",
      metrics,
      trend: [metrics],
      active: [],
      active_vehicles: 0,
      active_cycles: 0,
      waiting: 0,
      waiting_status: "WAITING_AT_SITE",
      target_liters_per_m3: null,
    });
  }
  return send(404, {});
}).listen(8101, "127.0.0.1");
