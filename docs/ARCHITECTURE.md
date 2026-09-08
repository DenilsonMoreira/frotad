# Arquitetura

## Estratégia

Monólito modular com frontend separado. Evita complexidade prematura e mantém fronteiras claras para futura extração de serviços.

## Componentes

```text
Browser/PWA
   │
   ▼
Next.js Web
   │ HTTPS/JSON
   ▼
FastAPI API
   ├── Identity/Tenancy
   ├── Fleet
   ├── Forms
   ├── Operations
   ├── Maintenance
   ├── Files
   ├── Analytics
   └── Audit
       │
       ├── PostgreSQL
       ├── Redis
       └── S3-compatible storage
```

## Módulos

### Identity/Tenancy

Companies, branches, users, memberships, roles and permissions.

### Fleet

Vehicles, drivers, assignments and vehicle state history.

### Forms

Definitions, versions, fields, validation, formulas, relations and submissions.

### Operations

Operational projections derived from forms: active periods, journeys, delivery cycles and current status.

### Maintenance

Preventive plans, occurrences and work orders. P1.

### Analytics

Read models/queries for dashboards. Do not force dashboard-heavy queries through generic form-answer joins forever; introduce projections/materialized read models as volume grows.

## Event strategy

Start with transactional writes and an outbox table for important asynchronous side effects. Avoid introducing Kafka in MVP.

Potential events:

- `form.submitted`
- `period.started`
- `period.ended`
- `vehicle.status_changed`
- `delivery.completed`
- `fuel.recorded`
- `maintenance.due`

## Time

- persist UTC timestamps;
- company/unit timezone is configuration;
- display localized values;
- server time is authoritative for operational timing.

## Observability

Production baseline:

- structured logs;
- request ID / correlation ID;
- error tracking;
- API metrics;
- DB slow query visibility;
- audit log distinct from application log.
