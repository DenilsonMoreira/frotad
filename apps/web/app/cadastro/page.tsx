import Link from "next/link";
import CompanyForm from "../components/company-form";

export default function RegisterPage() {
  return (
    <main className="auth-page wide">
      <Link className="brand" href="/login">
        Frota<span>D</span>
      </Link>
      <section className="panel auth-card">
        <p className="eyebrow">COMECE SUA OPERAÇÃO</p>
        <h1>Cadastre sua empresa</h1>
        <p className="muted">
          O responsável será o primeiro administrador da empresa e poderá
          cadastrar a equipe.
        </p>
        <CompanyForm />
        <p className="footnote">
          Já possui conta? <Link href="/login">Entrar</Link>
        </p>
      </section>
    </main>
  );
}
