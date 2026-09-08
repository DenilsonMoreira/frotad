# ADR 0001 — Monólito modular

Status: Accepted

## Contexto

O produto ainda está buscando fit e possui regras de domínio em rápida evolução.

## Decisão

Usar API FastAPI em monólito modular e frontend Next.js separado.

## Consequências

- desenvolvimento e deploy simples;
- transações consistentes mais fáceis;
- menor custo operacional;
- fronteiras de módulos devem ser preservadas para evitar "big ball of mud";
- serviços poderão ser extraídos posteriormente com evidência de necessidade.
