#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up -d postgres redis minio

echo "Infrastructure started."
echo "Next: configure apps/api and apps/web according to README.md"
