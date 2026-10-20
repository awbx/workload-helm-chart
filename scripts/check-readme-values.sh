#!/usr/bin/env bash
# Fails when a value in values.yaml has no row in the README values tables.
# A value counts as documented when it, or one of its parent keys, is the
# first cell of a table row (pass-through maps are documented as one row).
set -euo pipefail
cd "$(dirname "$0")/.."

documented=$(grep -oE '^\| `[^`]+`' README.md | sed -E 's/^\| `([^`]+)`/\1/' | sort -u)

missing=0
while read -r key; do
  probe=$key
  found=false
  while :; do
    if grep -qxF "$probe" <<<"$documented"; then found=true; break; fi
    [[ $probe == *.* ]] || break
    probe=${probe%.*}
  done
  if ! $found; then
    echo "undocumented value: $key"
    missing=1
  fi
done < <(yq '.. | select(tag != "!!map" or length == 0) | path | select(map(tag == "!!str") | all) | join(".")' charts/workload/values.yaml | sort -u)

exit $missing
