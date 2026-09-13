"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export type Session = {
  company_id: string | null;
  company_name: string | null;
  is_system_admin: boolean;
  user: {
    id: string;
    name: string;
    email: string;
    role: string | null;
    active: boolean;
  };
};
export const roleLabels: Record<string, string> = {
  OWNER: "Administrador responsável",
  ADMIN: "Administrador da empresa",
  MANAGER: "Gestor",
  DISPATCHER: "Operação",
  MAINTENANCE: "Manutenção",
  DRIVER: "Motorista",
  VIEWER: "Consulta",
};
export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch(`/api/backend/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const messages: Record<string, string> = {
      invalid_credentials:
        "E-mail ou senha inválidos. Após várias tentativas, aguarde 5 minutos.",
      registration_conflict:
        "Não foi possível cadastrar. Confira o e-mail e o identificador da empresa.",
      permission_denied: "Seu perfil não permite esta ação.",
      system_admin_required:
        "Esta área é exclusiva do administrador do sistema.",
      api_unavailable: "Serviço indisponível. Tente novamente.",
      protected_membership:
        "Este administrador não pode ser desativado por sua conta.",
    };
    throw new Error(
      messages[data.error?.code] ??
        (response.status === 422
          ? "Confira os campos. A senha de cadastro deve ter entre 15 e 128 caracteres."
          : "Não foi possível concluir a ação."),
    );
  }
  return response.status === 204 ? null : response.json();
}
export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const router = useRouter();
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/backend/auth/me", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }
        if (!response.ok)
          throw new Error(
            "Não foi possível verificar a sessão. Recarregue a página.",
          );
        const value = await response.json();
        if (!controller.signal.aborted) setSession(value);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(cause.message);
      });
    return () => controller.abort();
  }, [router]);
  return { session, error };
}
export async function logout() {
  const response = await fetch("/api/backend/auth/logout", { method: "POST" });
  if (!response.ok && response.status !== 401 && response.status !== 403)
    throw new Error("Não foi possível encerrar a sessão. Tente novamente.");
}
