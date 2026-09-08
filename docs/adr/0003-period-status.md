# ADR 0003 — Campo PERIOD como fonte de status operacional

Status: Accepted

## Contexto

O ciclo de entrega possui etapas com início e fim. Enquanto uma etapa ainda não possui fim, ela representa naturalmente o estado atual.

## Decisão

Um PERIOD iniciado e não finalizado poderá projetar o status operacional atual da submissão/veículo.

## Consequências

- dashboard quase em tempo real sem telemetria obrigatória;
- servidor precisa controlar timestamps e concorrência;
- correções precisam ser auditadas;
- status depende da disciplina de registro, devendo haver UX e alertas adequados.
