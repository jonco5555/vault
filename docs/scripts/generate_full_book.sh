#!/bin/bash
current_dir=$(basename "$PWD")
if [[ "$current_dir" != "vault" ]]; then
  echo "Error: Please run this script from the 'vault' base directory"
  exit 1
fi

./docs/scripts/render_mermaid.sh ./docs/assets/mermaid ./docs/assets

cat ./docs/index.md ./docs/design_implementation.md ./docs/advanced_details.md ./docs/evaluation.md ./docs/how_to_run.md > ./docs/vault_book.md
md-to-pdf ./docs/vault_book.md
rm ./docs/vault_book.md
