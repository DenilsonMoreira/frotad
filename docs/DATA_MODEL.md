# Modelo de dados inicial

This is a conceptual model; migrations are the implementation source of truth.

## Tenancy

### companies
- id UUID
- name
- slug
- timezone
- settings JSONB
- created_at

### branches
- id
- company_id
- name
- timezone override nullable

### users
- id
- name
- email
- status

### memberships
- company_id
- user_id
- role
- branch scope optional

## Fleet

### vehicles
- id
- company_id
- branch_id
- code / fleet_number
- plate
- model
- year
- status
- odometer_current

### drivers
- id
- company_id
- user_id nullable
- employee_code nullable
- active

## Form engine

### forms
- id
- company_id
- code (`FORM01` etc.)
- name
- description
- status

### form_versions
- id
- form_id
- version
- schema_hash
- published_at
- created_by

### form_fields
- id
- form_version_id
- key
- label
- field_type
- position
- required
- config JSONB

### form_submissions
- id
- company_id
- form_id
- form_version_id
- parent_submission_id nullable
- vehicle_id nullable
- driver_id nullable
- branch_id nullable
- status
- started_at
- submitted_at
- created_by

### form_answers
Keep typed columns to preserve analytics capability:
- id
- submission_id
- field_id
- value_text
- value_integer
- value_decimal
- value_boolean
- value_date
- value_datetime
- value_json

### period_values
Use a dedicated table instead of hiding periods in JSON:
- id
- answer_id
- company_id
- start_at
- end_at nullable
- duration_seconds nullable/final
- status_key nullable

Active: `start_at IS NOT NULL AND end_at IS NULL`.

### submission_relations
- id
- company_id
- parent_submission_id
- child_submission_id
- relation_field_id

## Attachments

### attachments
- id
- company_id
- submission_id nullable
- answer_id nullable
- storage_key
- content_type
- size_bytes
- original_name
- checksum
- created_by

## Audit

### audit_events
- id
- company_id
- actor_user_id
- entity_type
- entity_id
- action
- before JSONB nullable
- after JSONB nullable
- occurred_at
- request_id

## Analytics/read models

As usage grows, maintain explicit operational projections such as:

### current_vehicle_operations
- company_id
- vehicle_id
- driver_id
- journey_submission_id
- cycle_submission_id
- active_status_key
- active_since
- jobsite_id
- updated_at

### daily_vehicle_metrics
- company_id
- branch_id
- vehicle_id
- date
- distance_km
- fuel_liters
- deliveries_count
- volume_m3
- liters_per_m3
- waiting_seconds
- cycle_seconds

These can be populated transactionally at first and moved to asynchronous projection later.
