# Motor de Formulários

## Objetivo

Permitir que o cliente modele seu processo sem depender de desenvolvimento customizado para cada formulário.

## Ciclo de vida

```text
DRAFT → PUBLISHED → ARCHIVED
```

Editar um formulário publicado cria uma nova versão em draft. Submissões antigas permanecem associadas à versão utilizada.

## Tipos de campo

- TEXT
- INTEGER
- DECIMAL
- DATE
- TIME
- DATETIME
- BOOLEAN
- SINGLE_SELECT
- MULTI_SELECT
- VEHICLE_REFERENCE
- DRIVER_REFERENCE
- CUSTOMER_REFERENCE
- JOBSITE_REFERENCE
- PHOTO
- FILE
- PERIOD
- CALCULATED
- SUBFORM

## PERIOD

Configuração exemplo:

```json
{
  "status_key": "WAITING_AT_SITE",
  "status_label": "Aguardando na obra",
  "allow_concurrent": false,
  "capture_location_on_start": false,
  "capture_location_on_end": false
}
```

Sem `end_at`, o período está ativo e pode alimentar o status atual.

## Cálculos

Representar fórmulas como AST segura ou DSL limitada, nunca `eval`.

Exemplo conceitual:

```json
{
  "op": "divide",
  "left": {"ref": "diesel_total"},
  "right": {"ref": "volume_total"},
  "zero_behavior": "null"
}
```

Agregação de filhos:

```json
{
  "op": "sum_children",
  "form_code": "FORM02",
  "field_key": "volume_m3"
}
```

## Regras condicionais

MVP pode suportar visibilidade simples:

```text
show(field_B) if field_A == value
```

Evitar motor de regras genérico demais inicialmente.

## Anexos

Política por campo/processo:

- DISABLED
- OPTIONAL
- REQUIRED
- REQUIRED_ON_ISSUE

## Templates iniciais

- Jornada diária
- Ciclo de entrega
- Abastecimento
- Checklist pré-operação
- Ocorrência (P1)
- Manutenção preventiva (P1)
