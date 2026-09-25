# ADR 0009 — Editor visual do Form Builder

## Decisão

Administradores da empresa (`OWNER` e `ADMIN`) podem acessar `/formularios`. O administrador do sistema também pode gerenciar definições após selecionar explicitamente uma empresa no painel global. A seleção grava somente o UUID em cookie HttpOnly; toda operação continua validada pelo backend contra a identidade autenticada e a empresa existente.

O editor usa os contratos existentes do Form Builder e não cria uma segunda representação no frontend. Ele permite:

- criar um formulário e seu primeiro rascunho;
- listar os formulários da empresa e abrir a versão mais recente;
- adicionar os 18 tipos do motor, com controles específicos para seleção, evidência, `PERIOD`, `SUBFORM` e `CALCULATED`;
- reordenar campos por controles acessíveis;
- publicar uma versão após confirmação;
- visualizar a versão publicada sem controles de alteração;
- criar uma nova versão editável a partir da publicada.

Campos calculados recebem a AST segura em JSON e são novamente validados pelo backend na inclusão e publicação. O frontend nunca executa a expressão. `SUBFORM` recebe o UUID de uma versão publicada; uma seleção visual entre versões será uma melhoria posterior. O editor não oferece exclusão ou alteração de campos porque os endpoints correspondentes ainda não existem; isso evita simular persistência.

## API

`GET /api/v1/forms?offset=0&limit=50` retorna, sob escopo de empresa, código, nome, estado e a versão mais recente de cada formulário. A leitura exige `forms:read`; a interface de edição exige `forms:write`. Nenhuma migration ou variável de ambiente foi adicionada.

O proxy Next.js libera somente os caminhos e métodos conhecidos de formulários. `POST /api/company-context` aceita UUID, valida `Origin` e grava o cookie de contexto. Informar outro tenant não concede acesso: a API resolve a identidade e autoriza o contexto em cada chamada.

## Validação

Os testes da API cobrem listagem com permissão e escopo já exercitado pelo contexto de tenant. O Playwright percorre criação, inclusão de `PERIOD` e `DECIMAL`, reordenação, publicação, imutabilidade visível e clonagem em desktop e 360 px. As regras de imutabilidade no banco e os demais tipos de campo permanecem cobertos pela suíte do Form Builder existente.
