# Deployment

## Environments

- local
- staging
- production

## Initial production topology

- managed PostgreSQL
- containerized API
- Next.js web
- private S3 bucket
- Redis only if jobs/cache required
- reverse proxy/load balancer with TLS

Prefer simple managed infrastructure for pilot. Optimize only after measuring.

## Backups

- automated DB backups
- point-in-time recovery when supported
- object storage versioning/retention according to policy
- restore procedure tested periodically
