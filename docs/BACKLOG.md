# Backlog inicial

## EPIC 0 — Fundação

- [x] configurar monorepo e CI
- [x] configurar PostgreSQL/migrations
- [x] settings/env
- [x] logging estruturado
- [x] padrão de erros API

## EPIC 1 — Tenancy e identidade

- [x] company
- [x] branch
- [x] user
- [x] membership
- [x] role/permission
- [x] tenant context
- [x] testes de isolamento

## EPIC 2 — Frota

- [ ] CRUD veículo
- [ ] CRUD motorista
- [ ] vínculo motorista/usuário
- [ ] histórico de status do veículo

## EPIC 3 — Form Builder

- [x] forms
- [x] draft/version
- [x] fields
- [x] validation config (tipos básicos, PERIOD, seleções, evidências, cálculos e SUBFORM)
- [x] publish
- [ ] archive
- [ ] preview

## EPIC 4 — Form Runner

- [x] criar submissão
- [x] salvar draft
- [x] enviar
- [x] respostas tipadas
- [x] validações
- [ ] mobile UX

## EPIC 5 — PERIOD / tempo real

- [x] start period
- [x] finish period
- [x] elapsed duration
- [x] consulta de status ativo por submissão (projeção materializada futura)
- [x] impedir concorrência quando configurado
- [ ] correções auditadas
- [ ] board em tempo real/polling inicial

## EPIC 6 — Relações e cálculos

- [x] SUBFORM
- [x] parent/child submissions
- [x] COUNT children
- [x] SUM child field
- [x] arithmetic calculations
- [x] divide-by-zero policy

## EPIC 7 — Templates concreteira

- [ ] FORM01 Jornada diária
- [ ] FORM02 Ciclo de entrega
- [ ] FORM03 Abastecimento
- [ ] template checklist pré-operação

## EPIC 8 — Dashboards piloto

- [ ] status ao vivo
- [ ] espera em obra
- [ ] entregas/viagens
- [ ] volume m³
- [ ] diesel
- [ ] L/m³
- [ ] tendência diária

## EPIC 9 — Evidências

- [ ] S3 upload
- [ ] attachment policies
- [ ] foto opcional/obrigatória/desativada
- [ ] metadata e checksum

## EPIC 10 — Piloto

- [ ] importação CSV para cadastros
- [ ] feature flags
- [ ] feedback in-app simples
- [ ] telemetria de produto
- [ ] relatório de uso do piloto
