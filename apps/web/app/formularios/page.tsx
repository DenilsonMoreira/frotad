"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, useSession } from "../../lib/session";
import AdminShell from "../components/admin-shell";

type FormSummary = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
  latest_version_id: string;
  latest_version: number;
  latest_published_at: string | null;
};

export default function FormsPage() {
  const router = useRouter();
  const { session, error: sessionError } = useSession();
  const [forms, setForms] = useState<FormSummary[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const allowed = !!session &&
    (session.is_system_admin || ["OWNER", "ADMIN"].includes(session.user.role ?? ""));
  const load = useCallback(() => {
    if (allowed && session?.company_id) {
      void api("forms").then(setForms).catch((cause) => setError(cause.message));
    }
  }, [allowed, session]);
  useEffect(() => load(), [load]);

  if (!session) return <main><p role="status">{sessionError || "Verificando sessão…"}</p></main>;
  if (!allowed || !session.company_id) {
    return <AdminShell session={session} title="Acesso restrito">
      <p>Selecione uma empresa e use um perfil administrador para gerenciar formulários.</p>
    </AdminShell>;
  }
  return <AdminShell session={session} title="Formulários">
    <section className="panel management">
      <h2>Novo formulário</h2>
      <p className="muted">Crie a estrutura em rascunho. Ela estará disponível para preenchimento após a publicação.</p>
      <form className="form-grid" onSubmit={async (event) => {
        event.preventDefault();
        if (busy) return;
        setBusy(true); setError("");
        try {
          const version = await api("forms", {
            method: "POST",
            body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
          });
          router.push(`/formularios/${version.id}`);
        } catch (cause) {
          setError((cause as Error).message); setBusy(false);
        }
      }}>
        <label>Código<input name="code" required maxLength={50} pattern="[A-Za-z][A-Za-z0-9_]*" placeholder="CHECKLIST_DIARIO" /></label>
        <label>Nome<input name="name" required maxLength={200} /></label>
        <label className="full-width">Descrição<textarea name="description" maxLength={4000} /></label>
        <button className="full-width" disabled={busy}>{busy ? "Criando…" : "Criar rascunho"}</button>
      </form>
    </section>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="panel management">
      <h2>Formulários da empresa</h2>
      <div className="form-list">
        {forms.map((form) => <Link className="form-item" href={`/formularios/${form.latest_version_id}`} key={form.id}>
          <div><strong>{form.name}</strong><p>{form.code} · versão {form.latest_version}</p></div>
          <span className="badge">{form.latest_published_at ? "Publicado" : "Rascunho"}</span>
        </Link>)}
      </div>
      {!forms.length && !error && <p>Nenhum formulário cadastrado.</p>}
    </section>
  </AdminShell>;
}
