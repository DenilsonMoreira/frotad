# ADR 001 — Fundação e isolamento

Status: aceito. Data: 2026-09-08.

## Escopo da fase 1

EPIC 0 e EPIC 1: configuração, CI, migrations, identidade e tenant context.
Veículos e motoristas têm persistência e consultas paginadas; CRUD e histórico
continuam no EPIC 2. Os modelos de formulários do starter são rascunhos não
registrados no metadata ativo e serão migrados na fase própria.

## Decisões

- PostgreSQL 17 é o banco operacional. UUID nativo no PostgreSQL, com Uuid
  portátil para testes rápidos SQLite. CI usa PostgreSQL real.
- O header X-Company-ID seleciona a empresa, mas não concede acesso. O Bearer
  token identifica usuário ativo e uma membership ativa autoriza essa seleção.
  Nenhum company_id do corpo é usado para autorizar consultas.
- Tokens opacos de 256 bits, hash SHA-256 no banco, expiração e revogação.
  Bootstrap é comando administrativo com acesso direto ao banco; não há endpoint
  público de cadastro ou login. O token inicial dura oito horas. Login/SSO e
  gestão de convites ficam para uma próxima entrega antes do piloto público.
- TenantContext imutável é parâmetro obrigatório dos serviços de consulta.
  Capability fleet:read é concedida a todos os papéis exceto DRIVER.
  DRIVER aguarda implementação de operação atribuída. Membership de filial
  restringe veículos à filial e bloqueia motoristas até existir vínculo de filial.
- Chaves estrangeiras compostas impedem veículo/membership em filial de outra
  empresa e motorista vinculado a usuário sem membership na mesma empresa.
- Exclusões de referências são restritas quando há dependentes. Desativação é
  preferível à remoção de identidade com histórico operacional.
- Logs JSON contêm request ID gerado pelo servidor, método, status e duração.
  Headers, tokens e payloads não são registrados. Erros públicos têm o formato
  error.code / error.request_id; detalhes internos não são expostos.
- Datas operacionais usam UTC; timezone é configuração de empresa/filial.
- Form Builder, Runner, PERIOD persistido e dashboards não fazem parte desta fase.

## API

GET /api/v1/health é público.
GET /api/v1/vehicles e /api/v1/drivers aceitam offset >= 0 e limit de 1 a 100.
GET /api/v1/vehicles/{id} e /api/v1/drivers/{id} retornam 404 para IDs externos.
Rotas de frota exigem Authorization: Bearer TOKEN e X-Company-ID: UUID.
401: credencial inválida; 403: membership/permissão; 422: entrada inválida.

## Execução (Prompt de Comando)

Na raiz:

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e "./apps/api[dev]"
docker compose up -d postgres
cd apps\api
..\..\.venv\Scripts\alembic upgrade head
..\..\.venv\Scripts\python -m frotad.bootstrap --company "Empresa" --slug empresa --name "Administrador" --email admin@example.com
..\..\.venv\Scripts\uvicorn frotad.main:app --reload
```

Guarde o token mostrado uma única vez. Não o coloque em commits.
DATABASE_URL pode substituir o PostgreSQL local padrão do .env.example.
O Compose aplica migrations antes de iniciar a API.

## Testes

Execute pytest a partir de apps/api. Sem TEST_DATABASE_URL usa SQLite temporário.
Para PostgreSQL use um banco exclusivo de testes: a suíte cria e remove tabelas.
Nunca aponte TEST_DATABASE_URL para um banco operacional.
A suíte verifica acesso bilateral, IDs externos, troca de tenant, ausência de
credenciais, revogação, expiração, inatividade, papéis, filial, constraints,
paginação e upgrade/downgrade/upgrade sem divergência de metadata.
Frontend mantém as referências do starter; CI usa Node 24, npm ci, lint,
typecheck e build. Não há suíte de testes frontend no starter.

A criação da membership OWNER pelo bootstrap grava audit_events na mesma transação. Eventos são inseridos sem endpoints de edição ou remoção. Não há alteração de papéis pela API nesta fase.

Validação local: 20 casos backend (isolamento, auditoria e migrations) em SQLite e PostgreSQL 17; Ruff, lint frontend, TypeScript e build aprovados. O Node local é 22; CI valida a versão 24 exigida pelo projeto.
