"use client";
import { useCallback, useEffect, useState } from "react";
import { api, useSession } from "../../lib/session";
import AdminShell from "../components/admin-shell";
import CompanyForm from "../components/company-form";

type Company = { id: string; name: string; slug: string; timezone: string };
export default function SystemPage() {
  const { session, error: sessionError } = useSession();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const load = useCallback(() => {
    if (session?.is_system_admin)
      void api(`system/companies?offset=${offset}&limit=50`)
        .then((value) => {
          setCompanies(value);
          setError("");
        })
        .catch((cause) => setError(cause.message));
  }, [session, offset]);
  useEffect(() => {
    load();
  }, [load]);
  if (!session)
    return (
      <main>
        <p role="status">{sessionError || "Verificando sessão…"}</p>
      </main>
    );
  if (!session.is_system_admin)
    return (
      <AdminShell session={session} title="Acesso restrito">
        <p>Somente o administrador do sistema pode gerenciar as empresas.</p>
      </AdminShell>
    );
  return (
    <AdminShell session={session} title="Empresas da plataforma">
      <section className="panel management">
        <h2>Nova empresa</h2>
        <p className="muted">
          Cadastre a empresa e seu administrador responsável.
        </p>
        <CompanyForm system onCreated={load} />
      </section>
      <section className="panel management">
        <h2>Empresas cadastradas</h2>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Empresa</th>
                <th>Identificador</th>
                <th>Fuso horário</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((company) => (
                <tr key={company.id}>
                  <th scope="row">{company.name}</th>
                  <td>{company.slug}</td>
                  <td>{company.timezone}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!companies.length && !error && <p>Nenhuma empresa nesta página.</p>}
        <div className="pagination">
          <button
            className="secondary"
            disabled={!offset}
            onClick={() => setOffset(offset - 50)}
          >
            Anterior
          </button>
          <button
            className="secondary"
            disabled={companies.length < 50}
            onClick={() => setOffset(offset + 50)}
          >
            Próxima
          </button>
        </div>
      </section>
    </AdminShell>
  );
}
