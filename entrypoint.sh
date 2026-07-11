#!/usr/bin/env bash
set -e

: "${DISCORD_BOT_TOKEN:?DISCORD_BOT_TOKEN is required}"

exec "$@"
