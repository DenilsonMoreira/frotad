"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { logout, Session } from "../../lib/session";

export default function AdminShell({
  session,
  title,
  children,
}: {
  session: Session;
  title: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [error, setError] = useState("");
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href={session.is_system_admin ? "/admin" : "/"}>
          Frota<span>D</span>
        </Link>
        <p>
          {session.is_system_admin
            ? "Administração do sistema"
            : session.company_name}
        </p>
        <nav aria-label="Administração">
          {session.is_system_admin ? (
            <Link href="/admin">Empresas</Link>
          ) : (
            <>
              <Link href="/">Operação ao vivo</Link>
              {["OWNER", "ADMIN"].includes(session.user.role ?? "") && (
                <Link href="/usuarios">Usuários da empresa</Link>
              )}
            </>
          )}
          <Link href="/conta">Minha conta</Link>
        </nav>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">
              {session.is_system_admin
                ? "ADMINISTRADOR DO SISTEMA"
                : session.company_name}
            </p>
            <h1>{title}</h1>
            <p className="muted">{session.user.name}</p>
          </div>
          <button
            className="secondary"
            onClick={() =>
              void logout()
                .then(() => router.replace("/login"))
                .catch((cause) => setError(cause.message))
            }
          >
            Sair
          </button>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {children}
      </main>
    </div>
  );
}
