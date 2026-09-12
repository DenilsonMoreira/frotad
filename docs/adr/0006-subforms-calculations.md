# ADR 0006 — SUBFORM e cálculos seguros

Status: aceito. Fase 4.

## Relações e histórico

Um campo SUBFORM recebe config.form_version_id, UUID de uma versão já publicada
na mesma empresa. Publicar o pai preserva esse vínculo no schema_hash. Publicar
uma nova versão do formulário filho não altera o pai nem filhos futuros criados
por aquele schema. Esta fase suporta um nível pai/filho, suficiente para a jornada
FORM01 com ciclos FORM02 e abastecimentos FORM03. Subforms aninhados são recusados.

Migration 2fa3d7f56571 cria submission_relations com empresa, pai, filho, versão do
pai, campo da relação e request_key. FKs compostas impedem vínculos entre empresas
ou com campos de outra versão. Cada filho tem um único pai. Não há endpoint para
anexar, mover ou excluir submissões existentes; filhos são criados pela operação
SUBFORM e herdam veículo, motorista, filial e fuso do pai.

POST /api/v1/submissions/{parent_id}/subforms/{field_id}/children

```json
{"request_key":"00000000-0000-4000-8000-000000000001"}
```

Use um UUID novo por criação lógica; repetições com o mesmo UUID retornam o mesmo
filho. Reutilizar a chave em outro campo retorna 409. A autorização exige escrita
no pai: motorista pode criar filhos da sua operação atribuída sem receber permissão
de criar operações gerais. Limite de 1.000 filhos por pai.

O pai é bloqueado antes de criar filho ou enviar. Isso serializa duas criações com
a mesma chave e impede corrida entre criação e finalização. Criação e vínculo são
atômicos, incluindo auditoria submission.child_created.

## Fórmulas

CALCULATED recebe config.expression como árvore JSON. Operações permitidas:
const, ref, add, subtract, multiply, divide, count_children e sum_children.
Não há eval, JavaScript, SQL arbitrário, chamadas de função ou expressões em texto.
Chaves desconhecidas, referências inválidas e ciclos são recusados. Limites:
128 nós e profundidade 12 por expressão, cadeia de dependências até 32 campos.

Exemplos de config.expression:

```json
{"op":"subtract","left":{"ref":"km_fim"},"right":{"ref":"km_inicio"}}
```

```json
{"op":"count_children","form_code":"FORM02"}
```

```json
{"op":"sum_children","form_code":"FORM02","field_key":"volume_m3"}
```

```json
{"op":"sum_children","form_code":"FORM03","field_key":"liters"}
```

```json
{"op":"divide","left":{"ref":"diesel"},"right":{"ref":"volume"},"zero_behavior":"null"}
```

COUNT/SUM só incluem filhos SUBMITTED vinculados ao pai; filhos em draft ou ciclos
sem vínculo não contam. COUNT sem filhos é zero. SUM ignora respostas nulas e é
zero sem valores. Uma entrada aritmética ausente propaga null. Divisão por zero
sempre retorna null; outro zero_behavior é rejeitado. Referências e SUM só aceitam
campos INTEGER, DECIMAL ou CALCULATED. Um código filho só pode ser vinculado por
um campo SUBFORM no mesmo pai para evitar agregações ambíguas.

Operações usam Decimal, precisão intermediária 38 e arredondamento ROUND_HALF_UP
para quatro casas em cada campo calculado. Valores devem caber em Numeric(18,4).
Constantes aceitam inteiro ou string decimal; floats e valores não finitos são
rejeitados. Overflow retorna erro e desfaz a gravação da resposta que o causou.

## Estado calculado

GET da submissão inclui children (campo, ID e status) e respostas calculadas.
Enquanto DRAFT os valores são recalculados. Enviar o pai exige todos os filhos
SUBMITTED; SUBFORM obrigatório exige ao menos um filho e CALCULATED obrigatório
exige resultado não nulo. Resultados são gravados como FormAnswer.value_decimal
na mesma transação de envio, inclusive respostas calculadas nulas. Leituras após
o envio usam esse snapshot, preservando o significado histórico.

CALCULATED e SUBFORM não aceitam PUT no endpoint de respostas. Depois do envio
não é possível criar novos filhos ou alterar os dados pela API. Acesso direto
SQL administrativo continua fora do contrato de gravação operacional.

## Validação e escopo

Testes cobrem FORM01/FORM02/FORM03 completos, isolamento, FKs, vínculo com versão
publicada, agregação só de filhos enviados, precisão, divisão por zero, overflow,
input malicioso, ciclos, autorização de motorista, auditoria, idempotência e
concorrência real PostgreSQL entre criação e envio.

Execute alembic upgrade head; sem novas variáveis. UI, dashboard, anexos e duração
como expressão calculada ficam fora desta entrega. Durações PERIOD continuam
expostas pelo Runner da fase 3. Os templates concreteira são demonstrados nos
testes; não existe ainda endpoint de instalação automática de templates.
