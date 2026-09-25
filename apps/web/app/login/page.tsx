"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { api, Session } from "../../lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <main className="auth-page">
      <Link className="brand" href="/login">
        Frota<span>D</span>
      </Link>
      <section className="panel auth-card">
        <p className="eyebrow">BEM-VINDO AO FROTAD</p>
        <h1>Acesse sua conta</h1>
        <p className="muted">
          Sua empresa, sua equipe e a operação em um só lugar.
        </p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            setBusy(true);
            setError("");
            const data = new FormData(event.currentTarget);
            try {
              const session: Session = await api("auth/login", {
                method: "POST",
                body: JSON.stringify(Object.fromEntries(data)),
              });
              router.replace(session.is_system_admin ? "/admin" : "/");
            } catch (cause) {
              setError((cause as Error).message);
              setBusy(false);
            }
          }}
        >
          <label>
            E-mail
            <input
              type="email"
              name="email"
              required
              maxLength={254}
              autoComplete="username"
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              name="password"
              required
              maxLength={128}
              autoComplete="current-password"
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
        </form>
        <p className="footnote">
          Ainda não cadastrou sua empresa?{" "}
          <Link href="/cadastro">Cadastrar empresa</Link>
        </p>
        <p className="footnote">
          Esqueceu a senha? A recuperação automática ainda não está disponível
          neste piloto.
        </p>
      </section>
    </main>
  );
}
