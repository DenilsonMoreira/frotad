"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, useSession } from "../../lib/session";
import AdminShell from "../components/admin-shell";

export default function AccountPage() {
  const router = useRouter();
  const { session, error: sessionError } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!session)
    return (
      <main>
        <p>{sessionError || "Verificando sessão…"}</p>
      </main>
    );
  return (
    <AdminShell session={session} title="Minha conta">
      <section className="panel management auth-card">
        <h2>Alterar senha</h2>
        <p className="muted">
          Depois da alteração, entre novamente. Todas as sessões anteriores
          serão encerradas.
        </p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            const fields = new FormData(event.currentTarget);
            if (fields.get("new_password") !== fields.get("confirm")) {
              setError("As senhas não coincidem.");
              return;
            }
            fields.delete("confirm");
            setBusy(true);
            setError("");
            try {
              await api("auth/password", {
                method: "POST",
                body: JSON.stringify(Object.fromEntries(fields)),
              });
              router.replace("/login");
            } catch (cause) {
              setError((cause as Error).message);
              setBusy(false);
            }
          }}
        >
          <label>
            Senha atual
            <input
              type="password"
              name="current_password"
              required
              maxLength={128}
              autoComplete="current-password"
            />
          </label>
          <label>
            Nova senha
            <input
              type="password"
              name="new_password"
              required
              minLength={15}
              maxLength={128}
              autoComplete="new-password"
            />
          </label>
          <label>
            Confirmar nova senha
            <input
              type="password"
              name="confirm"
              required
              minLength={15}
              maxLength={128}
              autoComplete="new-password"
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button disabled={busy}>
            {busy ? "Alterando…" : "Alterar senha"}
          </button>
        </form>
      </section>
    </AdminShell>
  );
}
