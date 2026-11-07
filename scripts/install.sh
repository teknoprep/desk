#!/usr/bin/env bash
# Install everything in the kit, without questions.
#
#   ./scripts/install.sh             install every component
#   ./scripts/install.sh --dry-run   show what would change
#
# For a picker instead, run ./desk with no arguments.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/desk" install all --yes "$@"
