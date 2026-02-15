#!/usr/bin/env bash
# Wrapper script - calls scripts/setup.sh
exec "$(dirname "$0")/scripts/setup.sh" "$@"
