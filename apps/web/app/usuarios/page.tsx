"use client";
import { useCallback, useEffect, useState } from "react";
import { api, roleLabels, useSession } from "../../lib/session";
import AdminShell from "../components/admin-shell";

type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  active: boolean;
};
export default function UsersPage() {
  const { session, error: sessionError } = useSession();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const authorized =
    !!session && ["OWNER", "ADMIN"].includes(session.user.role ?? "");
  const load = useCallback(() => {
    if (authorized)
      void api(`users?offset=${offset}&limit=50`)
        .then(setUsers)
        .catch((cause) => setError(cause.message));
  }, [authorized, offset]);
  useEffect(() => {
    load();
  }, [load]);
  if (!session)
    return (
      <main>
        <p role="status">{sessionError || "Verificando sessão…"}</p>
      </main>
    );
  if (!authorized)
    return (
      <AdminShell session={session} title="Acesso restrito">
        <p>Somente administradores da empresa podem cadastrar usuários.</p>
      </AdminShell>
    );
  return (
    <AdminShell session={session} title="Usuários da empresa">
      <section className="panel management">
        <h2>Cadastrar usuário</h2>
        <p className="muted">
          O usuário terá acesso somente a {session.company_name}.
        </p>
        <form
          className="form-grid"
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            const form = event.currentTarget;
            setBusy(true);
            setError("");
            setMessage("");
            try {
              await api("users", {
                method: "POST",
                body: JSON.stringify(Object.fromEntries(new FormData(form))),
              });
              form.reset();
              setMessage(
                "Usuário cadastrado. Entregue a senha inicial diretamente ao usuário.",
              );
              load();
            } catch (cause) {
              setError((cause as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Nome
            <input name="name" required maxLength={200} />
          </label>
          <label>
            E-mail
            <input name="email" type="email" required maxLength={254} />
          </label>
          <label>
            Senha inicial
            <input
              name="password"
              type="password"
              minLength={15}
              maxLength={128}
              required
              autoComplete="new-password"
            />
            <small>
              15 a 128 caracteres. O usuário pode alterá-la em Minha conta.
            </small>
          </label>
          <label>
            Perfil
            <select name="role" defaultValue="VIEWER">
              {Object.entries(roleLabels)
                .filter(
                  ([key]) =>
                    key !== "OWNER" &&
                    (key !== "ADMIN" || session.user.role === "OWNER"),
                )
                .map(([key, label]) => (
                  <option value={key} key={key}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <p className="footnote full-width">
            Administradores criam e publicam formulários. Motoristas acessam
            somente suas operações atribuídas.
          </p>
          <button className="full-width" disabled={busy}>
            {busy ? "Salvando…" : "Cadastrar usuário"}
          </button>
        </form>
      </section>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <section className="panel management">
        <h2>Equipe cadastrada</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Perfil</th>
                <th>Status</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <th scope="row">{user.name}</th>
                  <td>{user.email}</td>
                  <td>{roleLabels[user.role]}</td>
                  <td>{user.active ? "Ativo" : "Inativo"}</td>
                  <td>
                    {user.id !== session.user.id &&
                      user.role !== "OWNER" &&
                      (user.role !== "ADMIN" ||
                        session.user.role === "OWNER") && (
                        <button
                          className="secondary"
                          disabled={busy}
                          onClick={async () => {
                            setBusy(true);
                            setError("");
                            try {
                              await api(`users/${user.id}`, {
                                method: "PATCH",
                                body: JSON.stringify({ active: !user.active }),
                              });
                              load();
                            } catch (cause) {
                              setError((cause as Error).message);
                            } finally {
                              setBusy(false);
                            }
                          }}
                        >
                          {user.active ? "Desativar" : "Ativar"}
                        </button>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
            disabled={users.length < 50}
            onClick={() => setOffset(offset + 50)}
          >
            Próxima
          </button>
        </div>
      </section>
    </AdminShell>
  );
}
