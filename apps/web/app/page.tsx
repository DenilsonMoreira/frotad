"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

type Metrics = {
  day: string;
  missing_measurements: number;
  trips: number;
  volume_m3: string;
  diesel_liters: string;
  liters_per_m3: string | null;
};
type Operation = {
  period_id: string;
  submission_id: string;
  vehicle: string;
  driver: string;
  status_key: string;
  status_label: string;
  started_at: string;
  elapsed_seconds: number;
};
type Dashboard = {
  company: string;
  timezone: string;
  server_time: string;
  metrics: Metrics;
  trend: Metrics[];
  active: Operation[];
  active_vehicles: number;
  active_cycles: number;
  waiting: number;
  waiting_status: string;
  target_liters_per_m3: string | null;
};
const number = (value: string | number | null) =>
  value === null
    ? "—"
    : new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(
        Number(value),
      );
const duration = (seconds: number) =>
  `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)
    .toString()
    .padStart(2, "0")}min`;

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

export default function DashboardPage() {
  const [credentials, setCredentials] = useState<{
    company: string;
    token: string;
  } | null>(null);
  const [data, setData] = useState<Dashboard | null>(null);
  const [day, setDay] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    if (!credentials) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/dashboard${day ? `?day=${day}` : ""}`,
        {
          headers: {
            Authorization: `Bearer ${credentials.token}`,
            "X-Company-ID": credentials.company,
          },
          cache: "no-store",
          signal: controller.signal,
        },
      );
      if (!response.ok)
        throw new Error(
          response.status === 401
            ? "Token inválido ou expirado. Desconecte e informe um novo token."
            : response.status === 403
              ? "Seu acesso não permite consultar esta operação."
              : "Não foi possível atualizar o dashboard. Tente novamente.",
        );
      const result: Dashboard = await response.json();
      if (!controller.signal.aborted) {
        setData(result);
        setError("");
      }
    } catch (cause) {
      if (!controller.signal.aborted)
        setError(cause instanceof Error ? cause.message : "Falha de conexão.");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [credentials, day]);
  useEffect(() => {
    const initial = window.setTimeout(() => {
      void refresh();
    }, 0);
    const interval = window.setInterval(() => {
      void refresh();
    }, 30000);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
      request.current?.abort();
    };
  }, [refresh]);
  const visible =
    data?.active.filter(
      (row) =>
        (!status || row.status_key === status) &&
        `${row.vehicle} ${row.driver} ${row.status_label}`
          .toLocaleLowerCase("pt-BR")
          .includes(query.toLocaleLowerCase("pt-BR")),
    ) ?? [];
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href="/">
          Frota<span>D</span>
        </Link>
        <p>Plataforma operacional de frotas</p>
        <nav aria-label="Navegação principal">
          <a href="#operation">◉ Operação ao vivo</a>
          <a href="#efficiency">▥ Eficiência e diesel</a>
        </nav>
        <div className="sidebar-footer">
          Dados de hoje.
          <br />
          Decisões para amanhã.<small>Tema: Azul confiável</small>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">FROTAD / VISÃO OPERACIONAL</p>
            <h1>Controle da operação</h1>
            <p className="muted">
              Acompanhe os movimentos da frota e os resultados do dia.
            </p>
          </div>
          {credentials && (
            <button
              className="secondary"
              onClick={() => {
                request.current?.abort();
                setCredentials(null);
                setData(null);
                setError("");
                setDay("");
              }}
            >
              Desconectar
            </button>
          )}
        </header>
        {!credentials ? (
          <section className="connect panel">
            <div>
              <p className="eyebrow">ACESSO AO PILOTO</p>
              <h2>Conecte sua empresa</h2>
              <p>
                Use o identificador da empresa e o token fornecidos pelo
                administrador.
              </p>
              <p className="muted">
                O token fica apenas na memória desta página. Ao recarregar,
                conecte novamente.
              </p>
            </div>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                setCredentials({
                  company: String(form.get("company")).trim(),
                  token: String(form.get("token")).trim(),
                });
                event.currentTarget.reset();
              }}
            >
              <label>
                Identificador da empresa
                <input
                  name="company"
                  required
                  pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                  placeholder="UUID da empresa"
                  autoComplete="off"
                />
              </label>
              <label>
                Token de acesso
                <input
                  name="token"
                  type="password"
                  required
                  autoComplete="off"
                />
              </label>
              <button type="submit">Acessar operação →</button>
            </form>
          </section>
        ) : (
          <>
            <div className="toolbar">
              <div>
                <strong>{data?.company ?? "Conectando…"}</strong>
                <p className="muted" role="status">
                  {loading
                    ? "Atualizando…"
                    : data
                      ? `Atualizado às ${new Date(data.server_time).toLocaleTimeString("pt-BR", { timeZone: data.timezone })} · a cada 30 segundos`
                      : "Aguardando dados"}
                </p>
              </div>
              <label>
                Data dos resultados
                <input
                  type="date"
                  value={day || data?.metrics.day || ""}
                  onChange={(e) => {
                    setData(null);
                    setDay(e.target.value);
                  }}
                />
              </label>
              <button
                className="secondary"
                disabled={loading}
                onClick={() => void refresh()}
              >
                Atualizar
              </button>
            </div>
            {error && (
              <div className="error" role="alert">
                {error}{" "}
                {data &&
                  "Os dados abaixo são da última atualização; os tempos podem estar desatualizados."}
              </div>
            )}
            {data && (
              <>
                <section id="operation">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">AGORA · {data.timezone}</p>
                      <h2>Operação ao vivo</h2>
                    </div>
                    <span className="badge">
                      {error
                        ? "Atualização interrompida"
                        : "Horário do servidor"}
                    </span>
                  </div>
                  <div className="metrics">
                    <Metric
                      label="Veículos em operação"
                      value={number(data.active_vehicles)}
                      detail="Com período ativo"
                    />
                    <Metric
                      label="Ciclos em andamento"
                      value={number(data.active_cycles)}
                      detail="Com etapa iniciada"
                    />
                    <Metric
                      label="Espera na obra"
                      value={number(data.waiting)}
                      detail="Períodos de espera ativos"
                    />
                  </div>
                  <div className="panel">
                    <div className="filters">
                      <label>
                        Buscar na operação
                        <input
                          type="search"
                          placeholder="Veículo, motorista ou status"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                        />
                      </label>
                      <label>
                        Status
                        <select
                          value={status}
                          onChange={(e) => setStatus(e.target.value)}
                        >
                          <option value="">Todos os status</option>
                          {Array.from(
                            new Map(
                              data.active.map((row) => [
                                row.status_key,
                                row.status_label,
                              ]),
                            ).entries(),
                          ).map(([key, label]) => (
                            <option key={key} value={key}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <div className="board">
                      {visible.map((row) => (
                        <article
                          className={`operation ${row.status_key === data.waiting_status ? "waiting" : ""}`}
                          key={row.period_id}
                        >
                          <span className="status-label">
                            ● {row.status_label}
                          </span>
                          <h3>{row.vehicle}</h3>
                          <p>{row.driver}</p>
                          <p className="muted">
                            Ciclo {row.submission_id.slice(0, 8)}
                          </p>
                          <div className="operation-time">
                            <small>
                              Início{" "}
                              {new Date(row.started_at).toLocaleString(
                                "pt-BR",
                                {
                                  timeZone: data.timezone,
                                  day: "2-digit",
                                  month: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </small>
                            <strong>{duration(row.elapsed_seconds)}</strong>
                          </div>
                        </article>
                      ))}
                    </div>
                    {!visible.length && (
                      <p className="empty">
                        {data.active.length
                          ? "Nenhuma operação corresponde aos filtros."
                          : "Nenhum período ativo. Os próximos inícios aparecerão aqui."}
                      </p>
                    )}
                    <p className="footnote">
                      Períodos iniciados sem horário de fim permanecem ativos,
                      inclusive os de dias anteriores. Durações atualizadas pelo
                      servidor.
                    </p>
                  </div>
                </section>
                <section id="efficiency">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">RESULTADOS DO DIA</p>
                      <h2>Eficiência e diesel</h2>
                    </div>
                    <span className="muted">
                      {data.metrics.day.split("-").reverse().join("/")}
                    </span>
                  </div>
                  <div className="metrics four">
                    <Metric
                      label="Viagens concluídas"
                      value={number(data.metrics.trips)}
                      detail="Ciclos enviados"
                    />
                    <Metric
                      label="Volume entregue"
                      value={`${number(data.metrics.volume_m3)} m³`}
                      detail="Volume dos ciclos enviados"
                    />
                    <Metric
                      label="Diesel abastecido"
                      value={`${number(data.metrics.diesel_liters)} L`}
                      detail="Abastecimentos enviados"
                    />
                    <Metric
                      label="Consumo por volume"
                      value={number(data.metrics.liters_per_m3)}
                      detail={`L/m³ · referência ${number(data.target_liters_per_m3)}`}
                    />
                  </div>
                  <div className="panel">
                    {data.metrics.missing_measurements > 0 && (
                      <p role="status" className="error">
                        {data.metrics.missing_measurements} medições ausentes.
                        Totais parciais; L/m³ indisponível.
                      </p>
                    )}
                    <h3>Últimos 7 dias</h3>
                    <p className="muted">
                      Totais por data de envio, no fuso da empresa ou unidade.
                    </p>
                    <div className="table-scroll">
                      <table>
                        <caption className="sr-only">
                          Evolução diária de viagens, volume, diesel e consumo
                          por volume
                        </caption>
                        <thead>
                          <tr>
                            <th>Data</th>
                            <th>Viagens</th>
                            <th>Volume (m³)</th>
                            <th>Diesel (L)</th>
                            <th>L/m³</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.trend.map((row) => (
                            <tr key={row.day}>
                              <th scope="row">
                                {row.day
                                  .slice(5)
                                  .split("-")
                                  .reverse()
                                  .join("/")}
                              </th>
                              <td>{number(row.trips)}</td>
                              <td>{number(row.volume_m3)}</td>
                              <td>{number(row.diesel_liters)}</td>
                              <td>{number(row.liters_per_m3)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="footnote">
                      L/m³ = diesel total ÷ volume total. Sem volume positivo, o
                      índice não é calculado. Abastecimento e consumo efetivo
                      podem ocorrer em dias diferentes. Rota, carga e espera
                      influenciam o resultado.
                    </p>
                  </div>
                </section>
              </>
            )}
          </>
        )}
        <footer>FrotaD · Informação que move a operação.</footer>
      </main>
    </div>
  );
}
