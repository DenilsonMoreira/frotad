"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState } from "react";
import { api, useSession } from "../../../lib/session";
import AdminShell from "../../components/admin-shell";

type Field = { id: string; key: string; label: string; field_type: string; position: number; required: boolean; config: Record<string, unknown> };
type Version = { id: string; form_id: string; version: number; name: string; description: string | null; published_at: string | null; schema_hash: string | null; fields: Field[] };
const types: [string, string][] = [
  ["TEXT", "Texto"], ["INTEGER", "Número inteiro"], ["DECIMAL", "Número decimal"],
  ["DATE", "Data"], ["TIME", "Hora"], ["DATETIME", "Data e hora"], ["BOOLEAN", "Sim/Não"],
  ["SINGLE_SELECT", "Seleção única"], ["MULTI_SELECT", "Seleção múltipla"],
  ["VEHICLE_REFERENCE", "Veículo"], ["DRIVER_REFERENCE", "Motorista"],
  ["CUSTOMER_REFERENCE", "Cliente"], ["JOBSITE_REFERENCE", "Obra"],
  ["PHOTO", "Foto"], ["FILE", "Arquivo"], ["PERIOD", "Período/status"],
  ["CALCULATED", "Calculado"], ["SUBFORM", "Subformulário"],
];

export default function FormEditor({ params }: { params: Promise<{ versionId: string }> }) {
  const { versionId } = use(params);
  const router = useRouter();
  const { session, error: sessionError } = useSession();
  const [version, setVersion] = useState<Version | null>(null);
  const [kind, setKind] = useState("TEXT");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const allowed = !!session &&
    (session.is_system_admin || ["OWNER", "ADMIN"].includes(session.user.role ?? ""));
  const load = useCallback(() => {
    if (allowed && session?.company_id) {
      void api(`form-versions/${versionId}`).then(setVersion).catch((cause) => setError(cause.message));
    }
  }, [allowed, session, versionId]);
  useEffect(() => load(), [load]);

  if (!session || !version) return <main><p role="status">{sessionError || error || "Carregando formulário…"}</p></main>;
  if (!allowed) return <AdminShell session={session} title="Acesso restrito"><p>Somente administradores criam formulários.</p></AdminShell>;

  const move = async (index: number, direction: number) => {
    const ids = version.fields.map((field) => field.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setBusy(true); setError("");
    try {
      setVersion(await api(`form-versions/${version.id}/field-order`, {
        method: "PUT", body: JSON.stringify({ field_ids: ids }),
      }));
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  };

  return <AdminShell session={session} title={version.name}>
    <p><Link href="/formularios">← Voltar aos formulários</Link></p>
    <section className="panel management">
      <div className="section-heading"><div><p className="eyebrow">VERSÃO {version.version}</p><h2>{version.published_at ? "Versão publicada" : "Rascunho em edição"}</h2></div><span className="badge">{version.published_at ? "Imutável" : `${version.fields.length} campos`}</span></div>
      {version.description && <p>{version.description}</p>}
      {version.published_at ? <button disabled={busy} onClick={async () => {
        setBusy(true); setError("");
        try { const next = await api(`form-versions/${version.id}/clone`, { method: "POST", body: "{}" }); router.push(`/formularios/${next.id}`); }
        catch (cause) { setError((cause as Error).message); setBusy(false); }
      }}>Criar nova versão editável</button> : <button disabled={busy || !version.fields.length} onClick={async () => {
        if (!window.confirm("Publicar esta versão? Depois disso ela não poderá ser alterada.")) return;
        setBusy(true); setError("");
        try { setVersion(await api(`form-versions/${version.id}/publish`, { method: "POST", body: "{}" })); }
        catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
      }}>Publicar versão</button>}
    </section>
    {error && <p className="error" role="alert">{error}</p>}
    {!version.published_at && <FieldCreator kind={kind} setKind={setKind} busy={busy} onStart={() => { setBusy(true); setError(""); }} onError={(message) => { setError(message); setBusy(false); }} onCreated={(next) => { setVersion(next); setBusy(false); }} versionId={version.id} />}
    <section className="panel management"><h2>Campos da versão</h2><div className="field-list">
      {version.fields.map((field, index) => <article className="field-item" key={field.id}><div><strong>{index + 1}. {field.label}</strong><p>{field.key} · {types.find(([key]) => key === field.field_type)?.[1] ?? field.field_type}{field.required ? " · obrigatório" : ""}</p></div>{!version.published_at && <div><button className="secondary compact" aria-label={`Mover ${field.label} para cima`} disabled={busy || index === 0} onClick={() => void move(index, -1)}>↑</button><button className="secondary compact" aria-label={`Mover ${field.label} para baixo`} disabled={busy || index === version.fields.length - 1} onClick={() => void move(index, 1)}>↓</button></div>}</article>)}
    </div>{!version.fields.length && <p>Nenhum campo adicionado.</p>}</section>
  </AdminShell>;
}

function FieldCreator({ kind, setKind, busy, versionId, onStart, onError, onCreated }: { kind: string; setKind: (value: string) => void; busy: boolean; versionId: string; onStart: () => void; onError: (message: string) => void; onCreated: (version: Version) => void }) {
  return <section className="panel management"><h2>Adicionar campo</h2><form className="form-grid" onSubmit={async (event) => {
    event.preventDefault(); if (busy) return;
    const form = event.currentTarget; const values = Object.fromEntries(new FormData(form));
    let config: Record<string, unknown> = {};
    try {
      if (["SINGLE_SELECT", "MULTI_SELECT"].includes(kind)) config = { options: String(values.options).split("\n").map((value) => value.trim()).filter(Boolean) };
      if (["PHOTO", "FILE"].includes(kind)) config = { policy: values.policy };
      if (kind === "PERIOD") config = { status_key: values.status_key, status_label: values.status_label, allow_concurrent: values.allow_concurrent === "on", capture_location_on_start: false, capture_location_on_end: false };
      if (kind === "SUBFORM") config = { form_version_id: values.form_version_id };
      if (kind === "CALCULATED") config = { expression: JSON.parse(String(values.expression)) };
      onStart();
      const next = await api(`form-versions/${versionId}/fields`, { method: "POST", body: JSON.stringify({ key: values.key, label: values.label, field_type: kind, required: values.required === "on", config }) });
      form.reset(); setKind("TEXT"); onCreated(next);
    } catch (cause) { onError(cause instanceof SyntaxError ? "A expressão calculada não contém JSON válido." : (cause as Error).message); }
  }}>
    <label>Chave técnica<input name="key" required maxLength={80} pattern="[A-Za-z][A-Za-z0-9_]*" placeholder="volume_m3" /></label>
    <label>Rótulo<input name="label" required maxLength={200} placeholder="Volume entregue (m³)" /></label>
    <label>Tipo<select name="field_type" value={kind} onChange={(event) => setKind(event.target.value)}>{types.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    <label className="checkbox"><input type="checkbox" name="required" /> Obrigatório</label>
    {["SINGLE_SELECT", "MULTI_SELECT"].includes(kind) && <label className="full-width">Opções, uma por linha<textarea name="options" required /></label>}
    {["PHOTO", "FILE"].includes(kind) && <label>Política<select name="policy"><option value="OPTIONAL">Opcional</option><option value="REQUIRED">Obrigatório</option><option value="REQUIRED_ON_ISSUE">Obrigatório em ocorrência</option><option value="DISABLED">Desativado</option></select></label>}
    {kind === "PERIOD" && <><label>Chave do status<input name="status_key" required pattern="[A-Za-z][A-Za-z0-9_]*" placeholder="WAITING_AT_SITE" /></label><label>Nome do status<input name="status_label" required placeholder="Aguardando na obra" /></label><label className="checkbox"><input type="checkbox" name="allow_concurrent" /> Permitir períodos concorrentes</label></>}
    {kind === "SUBFORM" && <label className="full-width">ID da versão publicada vinculada<input name="form_version_id" required /></label>}
    {kind === "CALCULATED" && <label className="full-width">Expressão segura (JSON)<textarea name="expression" required placeholder={'{"op":"subtract","left":{"ref":"km_fim"},"right":{"ref":"km_inicio"}}'} /><small>O backend aceita apenas referências, constantes, aritmética e agregações seguras.</small></label>}
    <button className="full-width" disabled={busy}>{busy ? "Adicionando…" : "Adicionar campo"}</button>
  </form></section>;
}
