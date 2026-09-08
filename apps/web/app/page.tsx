const statusRows = [
  ["FD-101", "Carlos Silva", "Em deslocamento", "18 min"],
  ["FD-107", "Marcos Lima", "Aguardando na obra", "42 min"],
  ["FD-103", "Rafael Santos", "Descarregando", "15 min"],
  ["FD-112", "João Oliveira", "Retorno", "28 min"],
];

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">Frota<span>D</span></div>
        <div className="tagline">Plataforma operacional de frotas</div>
        <nav>
          {['Dashboard', 'Jornada', 'Entregas', 'Abastecimentos', 'Manutenção', 'Formulários', 'Veículos', 'Motoristas', 'Relatórios'].map((item, i) => (
            <div className={i === 0 ? 'nav active' : 'nav'} key={item}>{item}</div>
          ))}
        </nav>
      </aside>

      <section className="content">
        <header>
          <div>
            <h1>Dashboard Operacional</h1>
            <p>Panorama da operação em tempo real.</p>
          </div>
          <span className="pill">Tema: Azul confiável</span>
        </header>

        <div className="kpis">
          <Kpi label="Veículos em operação" value="28" helper="de 34 na frota" />
          <Kpi label="L/m³ médio do dia" value="2,48" helper="meta 3,00" />
          <Kpi label="Espera média na obra" value="22 min" helper="-18% vs. ontem" />
          <Kpi label="Entregas concluídas" value="152" helper="784 m³" />
        </div>

        <div className="grid">
          <section className="panel">
            <h2>Status operacionais ao vivo</h2>
            <p className="muted">Período iniciado e sem fim = status ativo.</p>
            <div className="status-list">
              {statusRows.map(([vehicle, driver, status, elapsed]) => (
                <div className="status-row" key={vehicle}>
                  <div><strong>{status}</strong><span>{vehicle} · {driver}</span></div>
                  <b>{elapsed}</b>
                </div>
              ))}
            </div>
          </section>

          <section className="panel efficiency">
            <h2>Eficiência do dia</h2>
            <div className="metric-big">2,48 <small>L/m³</small></div>
            <div className="bar"><span style={{ width: '76%' }} /></div>
            <p className="muted">Indicadores devem ser interpretados com contexto de rota, volume e espera.</p>
          </section>
        </div>
      </section>
    </main>
  );
}

function Kpi({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </div>
  );
}
