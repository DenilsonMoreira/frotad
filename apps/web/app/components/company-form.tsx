"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "../../lib/session";

export default function CompanyForm({
  system = false,
  onCreated,
}: {
  system?: boolean;
  onCreated?: () => void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  return (
    <form
      className="form-grid"
      onSubmit={async (event) => {
        event.preventDefault();
        if (busy) return;
        const form = event.currentTarget;
        const fields = new FormData(form);
        if (fields.get("password") !== fields.get("confirm")) {
          setError("As senhas não coincidem.");
          return;
        }
        fields.delete("confirm");
        setBusy(true);
        setError("");
        setSuccess("");
        try {
          await api(system ? "system/companies" : "auth/register", {
            method: "POST",
            body: JSON.stringify(Object.fromEntries(fields)),
          });
          if (system) {
            form.reset();
            setSuccess("Empresa e administrador cadastrados.");
            onCreated?.();
          } else router.replace("/");
        } catch (cause) {
          setError((cause as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <label>
        Nome da empresa
        <input
          name="company_name"
          required
          maxLength={200}
          autoComplete="organization"
        />
      </label>
      <label>
        Identificador da empresa
        <input
          name="company_slug"
          required
          minLength={3}
          maxLength={80}
          pattern="[a-z0-9]+(-[a-z0-9]+)*"
          placeholder="exemplo-concreto"
        />
        <small>Letras minúsculas, números e hífens.</small>
      </label>
      <label>
        Fuso horário
        <select name="timezone" defaultValue="America/Fortaleza">
          <option value="America/Fortaleza">Fortaleza (UTC−3)</option>
          <option value="America/Sao_Paulo">São Paulo</option>
          <option value="America/Manaus">Manaus</option>
          <option value="America/Rio_Branco">Rio Branco</option>
          <option value="America/Noronha">Fernando de Noronha</option>
        </select>
      </label>
      <label>
        Nome do administrador responsável
        <input name="name" required maxLength={200} autoComplete="name" />
      </label>
      <label>
        E-mail do administrador
        <input
          name="email"
          type="email"
          required
          maxLength={254}
          autoComplete="username"
        />
      </label>
      <label>
        Senha do administrador
        <input
          name="password"
          type="password"
          required
          minLength={15}
          maxLength={128}
          autoComplete="new-password"
        />
        <small>Use uma frase com 15 a 128 caracteres.</small>
      </label>
      <label>
        Confirmar senha
        <input
          name="confirm"
          type="password"
          required
          minLength={15}
          maxLength={128}
          autoComplete="new-password"
        />
      </label>
      {error && (
        <p className="error full-width" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p role="status" className="full-width">
          {success}
        </p>
      )}
      <button className="full-width" disabled={busy}>
        {busy ? "Cadastrando…" : "Cadastrar empresa"}
      </button>
    </form>
  );
}
