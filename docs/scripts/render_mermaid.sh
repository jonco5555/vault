#!/bin/bash

# Usage: ./convert_md_to_png.sh input_folder output_folder
# Example: ./convert_md_to_png.sh ./mermaid_md ./diagrams_png

INPUT_DIR="$1"
OUTPUT_DIR="$2"

# Check arguments
if [[ -z "$INPUT_DIR" || -z "$OUTPUT_DIR" ]]; then
  echo "Usage: $0 <input_folder> <output_folder>"
  exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Loop over all .md files in the input folder
for md_file in "$INPUT_DIR"/*.md; do
  # Skip if no files match
  [[ -e "$md_file" ]] || continue

  # Get the base filename without extension
  base_name=$(basename "$md_file" .md)

  # Set output PNG path
  output_file="$OUTPUT_DIR/${base_name}.png"

  # Run Mermaid CLI to generate PNG
  mmdc -i "$md_file" -o "$output_file"

  echo "Converted $md_file → $output_file"
done
