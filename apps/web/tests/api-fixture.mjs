// Test-only upstream. Never imported by application code.
import { createServer } from "node:http";
const company = "11111111-1111-1111-1111-111111111111";
const sessions = new Map();
const forms = [];
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
  if (req.url === "/api/v1/forms" && req.method === "GET")
    return send(200, forms.filter((form) => !forms.some((other) =>
      other.form_id === form.form_id && other.version > form.version,
    )).map((form) => ({
      id: form.form_id, code: form.code, name: form.name, description: form.description,
      status: form.published_at ? "PUBLISHED" : "DRAFT", latest_version_id: form.id,
      latest_version: form.version, latest_published_at: form.published_at,
    })));
  if (req.url === "/api/v1/forms" && req.method === "POST") {
    const form = { id: crypto.randomUUID(), form_id: crypto.randomUUID(), version: 1,
      name: payload.name, description: payload.description || null, code: payload.code,
      published_at: null, schema_hash: null, fields: [] };
    forms.push(form);
    return send(201, form);
  }
  const versionMatch = req.url.match(/^\/api\/v1\/form-versions\/([0-9a-f-]+)(?:\/(fields|field-order|publish|clone))?$/);
  if (versionMatch) {
    const form = forms.find((item) => item.id === versionMatch[1]);
    if (!form) return send(404, { error: { code: "not_found" } });
    const action = versionMatch[2];
    if (!action) return send(200, form);
    if (action === "fields") {
      form.fields.push({ id: crypto.randomUUID(), position: form.fields.length, ...payload });
      return send(201, form);
    }
    if (action === "field-order") {
      form.fields.sort((a, b) => payload.field_ids.indexOf(a.id) - payload.field_ids.indexOf(b.id));
      form.fields.forEach((field, index) => field.position = index);
      return send(200, form);
    }
    if (action === "publish") {
      form.published_at = new Date().toISOString(); form.schema_hash = "test-hash";
      return send(200, form);
    }
    if (action === "clone") {
      const clone = { ...form, id: crypto.randomUUID(), version: form.version + 1,
        published_at: null, schema_hash: null,
        fields: form.fields.map((field) => ({ ...field, id: crypto.randomUUID() })) };
      forms.push(clone);
      return send(201, clone);
    }
  }
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
