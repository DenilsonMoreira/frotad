# API Guidelines

- prefix: `/api/v1`
- JSON UTF-8
- UUIDs externally
- RFC3339 timestamps with timezone
- pagination via cursor when listing grows
- idempotency keys for high-risk repeated mobile writes when implemented
- validation errors must identify field/path
- never expose internal stack traces
- tenant resolved from auth context

Example health endpoint:

`GET /api/v1/health`
