# Testes

## Backend

- pytest
- unit tests for formula/status rules
- integration tests with PostgreSQL for tenancy and persistence rules

## Frontend

- typecheck
- lint
- component tests when interaction complexity justifies
- e2e for the critical driver journey before pilot

## Critical scenarios

1. Start period → status active.
2. Finish period → duration frozen and status progresses.
3. Cannot start conflicting period when workflow disallows concurrency.
4. FORM01 count updates from child FORM02 submissions.
5. L/m³ calculation handles zero/no volume safely.
6. Published version remains stable after form edit.
7. Company A cannot read Company B data.
