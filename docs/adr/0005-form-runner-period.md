# ADR 0005 — Form Runner e PERIOD

Status: aceito. Fase 3.

## Modelo

Migration 080051a79ba7 adiciona form_submissions, form_answers e period_values.
Chaves estrangeiras compostas vinculam empresa, formulário, versão, campo,
veículo e motorista sem permitir misturar empresas ou versões. Índices únicos
nos pares de referências permitem validar esses vínculos no PostgreSQL e SQLite.

Uma submissão usa somente uma versão publicada. Guarda autor, início no servidor,
fuso da empresa/filial e os vínculos operacionais. Respostas de texto, inteiro,
decimal, boolean, data, hora, datetime e seleção são persistidas em colunas tipadas.
PERIOD possui tabela própria; não pode ser gravado pelo endpoint de respostas.

A resposta do Runner inclui o schema da versão utilizada. Isso permite ao motorista
preencher sua operação sem acesso ao catálogo global do Form Builder.

## Períodos e concorrência

Nesta fase, workflow significa uma submissão. Cada campo PERIOD pode ser iniciado
e encerrado uma vez por submissão. Repetir início de um período ativo ou fim de
um encerrado preserva os timestamps e não duplica auditoria. Reiniciar campo já
encerrado retorna 409; para outro ciclo crie outra submissão.

Comandos não aceitam timestamps de cliente. start_at/end_at são UTC do servidor.
PERIOD iniciado e sem fim retorna status ACTIVE, status_key configurado e duração
até server_time da resposta. Encerrado retorna CLOSED e duração final persistida.
Duração é inteira em segundos, truncada; inclui mudanças de dia e fuso corretamente.
Se o relógio do servidor retroceder antes do início, o encerramento é recusado.

Toda escrita bloqueia a linha da submissão com SELECT FOR UPDATE antes de consultar
ou modificar respostas/períodos. Dois pedidos simultâneos são serializados no
PostgreSQL. Só há concorrência quando todos os períodos envolvidos a permitem;
um campo exclusivo impede novos períodos ativos, mesmo que o novo permita.
Submissões diferentes podem operar simultaneamente.

## Finalização e permissões

Salvar resposta mantém DRAFT. Enviar exige campos obrigatórios preenchidos e
nenhum período ativo. Zero e false são respostas válidas. Após SUBMITTED a API
bloqueia alterações; reenviar retorna o registro existente. Correções auditadas
não fazem parte desta entrega.

OWNER/ADMIN/MANAGER/DISPATCHER criam operações. DRIVER lê e preenche apenas
operações atribuídas a um driver ativo vinculado ao seu usuário. A criação pelo
motorista aguarda o fluxo seguro de seleção/atribuição de veículo. VIEWER só lê.
Membership de filial restringe todas as operações à filial. Criação valida veículos,
motoristas e filiais na mesma empresa, e compatibilidade veículo/filial.

Auditoria transacional registra criação, respostas, envio e início/fim de períodos.
O schema publicado continua protegido pelos triggers da fase 2. Garantias contra
edição de submissões enviadas e concorrência de períodos são aplicadas pelo serviço;
acesso SQL administrativo direto não é uma API suportada para gravação operacional.

## API

Bearer token e X-Company-ID são obrigatórios:

- POST /api/v1/submissions: form_version_id e vehicle_id/driver_id/branch_id opcionais.
- GET /api/v1/submissions: offset/limit, com limite máximo de 100.
- GET /api/v1/submissions/{id}: schema, respostas, períodos e horário do servidor.
- PUT /api/v1/submissions/{id}/answers/{field_id}: {"value": ...}; null limpa resposta de draft.
- POST /api/v1/submissions/{id}/periods/{field_id}/start: corpo vazio ou {}.
- POST /api/v1/submissions/{id}/periods/{field_id}/finish: corpo vazio ou {}.
- POST /api/v1/submissions/{id}/submit: corpo vazio ou {}.

Decimal aceita string ou inteiro, até 14 dígitos inteiros e 4 decimais, sem float
binário, NaN ou infinito. DATETIME exige offset e é normalizado para UTC. TIME é
horário local sem offset; timezone da submissão preserva o contexto.

## Limites e próxima fase

Sem UI mobile ou fila offline nesta fase. Nenhuma captura de localização é simulada:
configuração que a solicite é recusada ao criar submissão. FILE/PHOTO, referências
de cliente/obra, CALCULATED e SUBFORM aguardam os respectivos módulos e retornam
erro explícito de tipo não suportado no Runner. Não há agregação ou tabela
materializada de status; a consulta retorna os períodos ativos diretamente.
Criação de submissão não possui ainda chave de idempotência; clientes não devem
repetir cegamente esse POST em caso de resposta perdida.

Execute alembic upgrade head. Sem novas variáveis de ambiente.
A suíte verifica fluxo completo, tipos, obrigatoriedade, duração, relógio servidor,
repetição de comandos, isolamento, referências, motorista/filial e concorrência
real no PostgreSQL. O PR depende de feat/form-builder e não faz merge automático.
