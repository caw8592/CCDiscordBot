#!/usr/bin/env bash
set -e

: "${TOKEN:?TOKEN is required}"

exec "$@"
