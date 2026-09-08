# AGENTS.md — FrotaD

This repository is the source of truth for the **FrotaD** SaaS.

FrotaD is a B2B operational fleet platform, initially validated with ready-mix concrete fleets and concrete mixer trucks. The product must remain configurable enough to serve other fleet-heavy operations later.

## 1. Product principles

1. **Operational truth before decoration.** Prefer reliable events, timestamps, auditability and useful calculations over visual complexity.
2. **Configurable workflows.** Checklists and operational forms are customer-configurable. Do not hard-code a customer's exact form into the domain model unless it represents a reusable first-class entity.
3. **Templates, not lock-in.** FrotaD may ship templates for concrete fleets, but customers can create or customize their own forms.
4. **One input, many uses.** Data collected once should feed dashboards, maintenance triggers, fuel efficiency, delivery evidence and operational analytics whenever valid.
5. **Mobile-first for drivers; desktop-first for managers.** Driver flows must be fast, forgiving and usable in poor connectivity. Management screens prioritize visibility and analysis.
6. **Do not punish users with misleading rankings.** Fuel and productivity metrics are contextual. Never imply driver fault when route, traffic, vehicle, customer wait, load size or operational constraints can explain the result.
7. **Evidence is configurable.** Photos/attachments can be disabled, optional, required, or required only under a configured condition.
8. **Historical records are immutable in meaning.** Published form versions and submitted answers must remain interpretable exactly as they were at submission time.

## 2. Critical domain rule: period fields become live status

A field of type `PERIOD` contains a start timestamp and an optional end timestamp.

- If `start_at` exists and `end_at` is null, the period is **active**.
- An active period may represent the current operational status of the related submission, e.g. `AGUARDANDO_OBRA`, `DESCARREGANDO`, `DESLOCAMENTO_OBRA`.
- The elapsed duration is computed from `start_at` to current server time while active.
- Once `end_at` is set, duration becomes final.
- A workflow can define whether only one period field may be active at a time. For the concrete delivery-cycle template, default to one active step at a time.
- Never derive current status from client time alone. Persist server-side timestamps and retain timezone context.

This rule is fundamental to live operational dashboards.

## 3. Form engine boundaries

The MVP form engine supports:

- TEXT
- INTEGER
- DECIMAL
- DATE
- TIME
- DATETIME
- BOOLEAN
- SINGLE_SELECT
- MULTI_SELECT
- VEHICLE_REFERENCE
- DRIVER_REFERENCE
- CUSTOMER_REFERENCE
- JOBSITE_REFERENCE
- FILE / PHOTO
- PERIOD
- CALCULATED
- SUBFORM

Initial calculations:

- arithmetic: `+`, `-`, `*`, `/`
- `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`
- duration between timestamps
- child form aggregation such as `COUNT(FORM02)` and `SUM(FORM02.volume_m3)`

Do **not** implement arbitrary code execution, JavaScript expressions, SQL formulas or unrestricted spreadsheet syntax.

## 4. Example templates

### FORM01 — Jornada diária

Typical fields:

- motorista → DRIVER_REFERENCE
- nº carro → VEHICLE_REFERENCE or INTEGER if customer insists
- dia → DATE
- placa → derived from vehicle or validated TEXT
- km início → INTEGER
- km fim → INTEGER
- km rodados → CALCULATED (`km_fim - km_inicio`)
- abastecimentos → SUBFORM(FORM03)
- viagens → CALCULATED (`COUNT(FORM02)`)
- volume entregue → CALCULATED (`SUM(FORM02.volume_m3)`)
- diesel reposto → CALCULATED (`SUM(FORM03.liters)`)
- L/m³ → CALCULATED (`diesel_reposto / volume_entregue`)

### FORM02 — Ciclo de entrega

Typical period fields:

- deslocamento obra → PERIOD
- aguardando → PERIOD
- descarregando → PERIOD
- deslocamento empresa → PERIOD
- ciclo completo → CALCULATED from cycle boundaries or sum of configured period durations

Additional useful fields:

- nota fiscal / remessa
- volume m³
- cliente
- obra

FORM02 is usually a child of FORM01. `FORM01.viagens = COUNT(FORM02)`.

### FORM03 — Abastecimento

Typical fields:

- data/hora
- veículo
- motorista
- hodômetro
- litros
- preço por litro (optional)
- total (optional/calculated)
- attachment according to tenant policy

## 5. Multi-tenancy

Every customer-owned record must be tenant scoped.

- `company_id` is mandatory on customer-owned root entities.
- Never accept tenant identity solely from request body.
- Resolve tenant from authenticated membership/context.
- Repository/service queries must enforce tenant scope.
- Cross-tenant access is a P0 security defect.

## 6. Roles and permissions

Initial roles:

- `OWNER`
- `ADMIN`
- `MANAGER`
- `DISPATCHER`
- `MAINTENANCE`
- `DRIVER`
- `VIEWER`

Permissions should be capability-based internally even if UI exposes roles.

Drivers should only access records relevant to their assigned/current operation unless explicitly granted broader visibility.

## 7. Auditability

Audit at minimum:

- form creation/publication/archive
- form submission and correction
- period start/end/correction
- maintenance status changes
- vehicle status changes
- attachment add/remove
- permission/role changes
- commission rule changes
- manual override of calculated or imported operational data

Prefer append-only audit events.

## 8. Attachments and evidence

Attachment policy is configurable by company/unit/process:

- `DISABLED`
- `OPTIONAL`
- `REQUIRED`
- `REQUIRED_ON_ISSUE`

Do not assume NF/DANFE images are mandatory. Future integrations may provide structured invoice/XML data instead.

## 9. Engineering stack

- Monorepo
- Web: Next.js 16.3.x, React, TypeScript
- API: Python 3.14, FastAPI, SQLAlchemy 2, Pydantic 2
- Database: PostgreSQL
- Cache/jobs: Redis (only when needed)
- Object storage: S3-compatible
- Local development: Docker Compose

Keep architecture modular-monolith until demonstrated scale/organizational need justifies services.

## 10. Backend conventions

- Separate transport (`api`) from domain/service logic.
- Do not put business rules directly inside route handlers.
- SQLAlchemy models are persistence structures, not API contracts.
- Use Pydantic schemas for requests/responses.
- All timestamps stored in UTC.
- Use timezone-aware datetimes.
- Prefer UUIDs for externally visible entity identifiers.
- Money uses integer cents or `Decimal`, never float.
- Volume/fuel metrics use `Decimal` with explicit precision.
- Avoid database JSON for core analytics fields. JSONB is acceptable for form field configuration and flexible answer metadata.

## 11. Frontend conventions

- Server Components by default where suitable; Client Components only for interaction/state/browser APIs.
- Driver workflows must be responsive at 360px width.
- Minimum touch target ~44px.
- Forms must survive intermittent connectivity. Offline submission queue is planned, but do not fake offline safety before it is implemented.
- Use semantic status labels in addition to color.
- Theme colors come from CSS variables/tokens; never scatter customer brand hex values throughout components.

## 12. Testing priorities

P0 automated tests:

1. tenant isolation
2. period active/closed semantics
3. duration calculations
4. form version immutability
5. calculated field correctness and divide-by-zero behavior
6. parent/child submission aggregations
7. permissions
8. audit event creation

## 13. Change discipline for coding agents

Before changing code:

1. Read this file and the relevant docs in `/docs`.
2. Identify the domain rule being changed.
3. Prefer the smallest coherent change.
4. Add/update tests for business rules.
5. Do not silently rename persisted fields or enum values.
6. Schema changes require a migration.
7. If a requirement conflicts with these principles, document the decision in an ADR.

Before finishing a task:

- run backend tests
- run frontend lint/typecheck/tests that exist
- summarize schema/API changes
- identify any migration or environment variable changes
- update relevant docs when behavior changed

## 14. MVP success condition

A manager should be able to answer, quickly:

- What is each active vehicle doing now?
- Which vehicles are waiting at a customer/jobsite and for how long?
- How many deliveries/m³ were completed?
- What is fuel efficiency (L/m³) against the configured reference?
- Which operational records are missing or anomalous?
- What maintenance or operational issues need attention?

A driver should be able to record a cycle with minimal typing.
