# ADR 0004 — Form Builder mínimo e versões imutáveis

Status: aceito. Fase 2.

## Modelo e consistência

Migration 67c3592ae6c6 adiciona forms, form_versions e form_fields.
Form.code é único por empresa; versão é sequencial por formulário; existe no
máximo um draft aberto por formulário. Campo tem key única dentro da versão.
Configuração usa JSONB no PostgreSQL e JSON nos testes SQLite.
Versão guarda nome/descrição próprios, autor, published_at UTC e schema_hash.
O hash SHA-256 cobre nome, descrição e campos ordenados com configuração.

Publicar exige pelo menos um campo. Publicar novamente retorna 409. Criar uma
nova versão exige origem publicada e copia profundamente campos/configuração,
com novos IDs; o original e seu hash são preservados. O formulário continua
PUBLISHED enquanto uma nova versão está em draft.

Escritas bloqueiam a raiz Form e depois a versão com SELECT FOR UPDATE.
Isso serializa publicação, adição, reordenação e clonagem no PostgreSQL.
Índice parcial impede drafts duplicados mesmo fora da API. Triggers impedem
UPDATE/DELETE em versões publicadas e INSERT/UPDATE/DELETE em seus campos.
Os triggers de campos também bloqueiam a versão durante a verificação.
SQLite tem triggers equivalentes, mas não substitui o teste de concorrência PG.
Os triggers podem ser removidos por um administrador do banco; as garantias
pressupõem que a aplicação não possua permissões de alterar schema em produção.

## Tenant e autorização

Toda consulta de versão passa por Form.company_id e TenantContext.
OWNER, ADMIN e MANAGER podem editar. VIEWER pode consultar versões.
Formulários são definições da empresa, compartilhadas entre suas filiais;
restrições de operação/motorista serão aplicadas nas submissões.
Criação, publicação, clonagem, adição e reordenação geram AuditEvent na mesma
transação. Requisições rejeitadas não deixam alterações parciais.

## API

Todas as rotas abaixo exigem Bearer token e X-Company-ID:

- POST /api/v1/forms — code, name, description opcional; retorna draft versão 1.
- GET /api/v1/form-versions/{id} — versão e campos ordenados.
- POST /api/v1/form-versions/{id}/fields — key, label, field_type, required, config.
- PUT /api/v1/form-versions/{id}/field-order — field_ids com todos os IDs, sem repetição.
- POST /api/v1/form-versions/{id}/publish — publica e gera hash.
- POST /api/v1/form-versions/{id}/clone — cria próximo draft a partir da publicada.

Exemplo de configuração PERIOD:

```json
{"status_key":"WAITING_AT_SITE","status_label":"Aguardando na obra","allow_concurrent":false}
```

Configurações desconhecidas são rejeitadas. Seleções exigem options não vazias
e únicas; FILE/PHOTO aceitam policy. Campos simples aceitam config vazio.
CALCULATED e SUBFORM permanecem reservados até a fase 4; nenhuma fórmula é
executada. Máximo de 200 campos por versão. Não há tela de builder, archive,
edição/remoção de campo ou runner nesta entrega. Os sketches antigos do runner
foram movidos para models/runner_draft.py e não fazem parte do metadata ativo.

## Operação e testes

Execute alembic upgrade head em apps/api. Nenhuma nova variável de ambiente.
O PR depende da fase 1; sua base é feat/backend-foundation enquanto o PR #1
aguarda revisão. Não foi feito merge automático.

Testes cobrem ciclo completo, integridade histórica, isolamento por empresa,
permissões, códigos e campos duplicados, configuração, reordenação atômica,
auditoria, triggers SQL diretos, duas clonagens concorrentes e publicação
concorrente com adição de campo. CI executa PostgreSQL 17 e valida frontend.
