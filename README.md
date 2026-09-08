# FrotaD

**FrotaD** é uma plataforma SaaS B2B de gestão operacional de frotas, inicialmente direcionada a concreteiras e caminhões betoneira.

O objetivo é digitalizar processos que hoje vivem em papel, planilhas, WhatsApp e conhecimento operacional disperso, transformando esses registros em acompanhamento em tempo real e indicadores úteis para motoristas, operação, manutenção e gestão.

## Visão do produto

O núcleo inicial do FrotaD combina:

- formulários/checklists totalmente configuráveis;
- jornada diária por veículo/motorista;
- ciclos/viagens e seus tempos operacionais;
- status ao vivo derivados de campos de período ainda abertos;
- entregas e volume em m³;
- abastecimentos e indicador L/m³;
- ocorrências e manutenção;
- evidências opcionais/obrigatórias conforme política do cliente;
- dashboards operacionais e executivos;
- trilha de auditoria.

### Regra central de status

Um campo `PERIOD` possui início e fim. Enquanto o início estiver preenchido e o fim estiver vazio, esse período representa um **status ativo**.

Exemplo:

```text
Deslocamento obra  07:28 → 08:41  concluído
Aguardando         08:41 → --:--  STATUS ATUAL
Descarregando      --:-- → --:--  ainda não iniciado
```

Isso permite transformar um formulário operacional em um painel de acompanhamento em tempo real sem exigir um sistema de rastreamento complexo no primeiro MVP.

## Arquitetura

```text
apps/web (Next.js)
        │
        ▼
apps/api (FastAPI)
        │
   ┌────┴──────────┐
   ▼               ▼
PostgreSQL       S3-compatible
   │
   ▼
Redis (jobs/cache, quando necessário)
```

A decisão inicial é um **monólito modular**, evitando microserviços prematuros.

## Stack de desenvolvimento

- Node.js 24 LTS
- Next.js 16.3.x
- React + TypeScript
- Python 3.14
- FastAPI
- SQLAlchemy 2
- PostgreSQL 17+
- Redis
- armazenamento S3-compatible (MinIO local)
- Docker Compose

## Estrutura

```text
.
├── AGENTS.md                 # regras para Codex/agentes
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── docker-compose.yml
├── .env.example
├── apps/
│   ├── api/                  # FastAPI
│   └── web/                  # Next.js
├── docs/
│   ├── PRODUCT.md
│   ├── MVP.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── FORM_ENGINE.md
│   ├── DASHBOARDS.md
│   ├── DESIGN_SYSTEM.md
│   ├── BACKLOG.md
│   ├── VALIDATION.md
│   └── adr/
└── .github/workflows/
```

## Rodando localmente

### Opção 1 — infraestrutura pelo Docker e aplicações localmente

```bash
cp .env.example .env
docker compose up -d postgres redis minio
```

Backend:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn frotad.main:app --reload
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

Acessos padrão:

- Web: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- MinIO console: http://localhost:9001

### Opção 2 — tudo pelo Docker

```bash
docker compose up --build
```

## Comandos úteis

```bash
make infra-up
make infra-down
make api-test
make web-lint
make check
```

## Primeiro recorte de implementação

A ordem sugerida está em [`docs/BACKLOG.md`](docs/BACKLOG.md). Em resumo:

1. tenancy + usuários + permissões;
2. veículos e motoristas;
3. motor de formulários versionado;
4. submissões de formulários;
5. tipo `PERIOD` e status em tempo real;
6. relacionamento FORM01 → FORM02/FORM03;
7. campos calculados simples;
8. dashboards operacionais;
9. anexos configuráveis;
10. ocorrências/manutenção.

## Documentação para Codex

O arquivo [`AGENTS.md`](AGENTS.md) define as regras de domínio e engenharia que agentes devem seguir. Antes de iniciar qualquer tarefa grande, consulte também:

- [`docs/PRODUCT.md`](docs/PRODUCT.md)
- [`docs/FORM_ENGINE.md`](docs/FORM_ENGINE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/CODEX_BOOTSTRAP.md`](docs/CODEX_BOOTSTRAP.md)

## Status

Projeto em fase inicial de produto/MVP. As hipóteses comerciais e operacionais ainda precisam ser validadas em piloto real.

## Fundação implementada

Consulte [ADR 001](docs/ADR-001-foundation.md) para API autenticada, migrations, bootstrap administrativo e testes. Formulários e telas do starter ainda são esboços.
