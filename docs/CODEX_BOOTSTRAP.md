# Guia de início no Codex

## Contexto obrigatório

Antes de implementar qualquer issue, peça ao Codex para ler:

1. `/AGENTS.md`
2. `/docs/PRODUCT.md`
3. `/docs/ARCHITECTURE.md`
4. `/docs/FORM_ENGINE.md`
5. `/docs/DATA_MODEL.md`
6. `/docs/BACKLOG.md`

## Primeira tarefa recomendada

Use um prompt semelhante a:

> Leia AGENTS.md e os documentos indicados. Implemente a fundação do backend do FrotaD para EPIC 0 e EPIC 1 sem avançar para telas complexas. Configure Alembic, crie migrations iniciais para tenancy, usuários/memberships, veículos e motoristas, adicione tenant context explícito e testes que provem isolamento entre duas empresas. Preserve as regras do AGENTS.md. Ao final, execute os testes e documente decisões.

## Segunda tarefa

> Implemente o Form Builder mínimo: Form, FormVersion e FormField; endpoints para criar draft, adicionar/reordenar campos, publicar uma versão e criar uma nova versão a partir de uma publicada. Uma versão publicada não pode ser alterada. Inclua testes.

## Terceira tarefa

> Implemente o Form Runner e o tipo PERIOD. Permita iniciar/finalizar períodos com timestamps de servidor. Um período iniciado sem fim deve aparecer como status ativo. Se o field config impedir concorrência, não permita dois períodos ativos no mesmo workflow. Crie testes de duração e concorrência.

## Quarta tarefa

> Implemente SUBFORM e cálculos seguros necessários aos templates FORM01/FORM02/FORM03: COUNT de filhos, SUM de campo filho, subtração e divisão com zero_behavior=null. Não use eval nem JavaScript arbitrário.

## Quinta tarefa

> Implemente o dashboard operacional mobile/desktop seguindo DESIGN_SYSTEM.md e DASHBOARDS.md. Priorize status ao vivo, espera na obra, viagens, volume, diesel e L/m³. Crie componentes baseados em tokens para permitir tema por cliente no futuro.

## Regra de execução

Peça ao Codex para fazer uma tarefa por vez e manter cada PR pequeno. Evite um prompt pedindo o SaaS inteiro em uma única execução.
