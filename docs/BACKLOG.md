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
- [x] preview/editor visual básico

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
- [x] board em tempo real/polling inicial

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

- [x] status ao vivo
- [x] espera em obra
- [x] entregas/viagens
- [x] volume m³
- [x] diesel
- [x] L/m³
- [x] tendência diária

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

## EPIC 11 — Acesso e administração

- [x] login com e-mail/senha e logout
- [x] cadastro de empresa e administrador responsável
- [x] administrador do sistema separado do administrador da empresa
- [x] cadastro e ativação/desativação de usuários por empresa
- [x] criação/publicação de formulários restrita a administradores
- [x] troca de senha pelo usuário
- [ ] recuperação e verificação de e-mail
- [x] editor visual de formulários para administradores
