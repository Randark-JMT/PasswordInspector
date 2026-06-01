#!/usr/bin/env bash
# Generates a self-signed TLS certificate for local/internal use.
# Place in project root and run once before docker compose up.
set -euo pipefail

mkdir -p certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -subj "/CN=passwordinspector/O=Internal/C=CN"

echo "Certificates written to ./certs/"
