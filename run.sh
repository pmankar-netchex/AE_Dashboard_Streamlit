#!/usr/bin/env bash
# Wrapper script - calls scripts/run.sh
exec "$(dirname "$0")/scripts/run.sh" "$@"
