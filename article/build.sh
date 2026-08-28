#!/bin/bash

OUTPUT_DIR="output"
CITATION_STYLES="./config/style.csl"
STYLES_URL="https://raw.githubusercontent.com/myshevchuk/dstu-csl/refs/heads/master/dstu-8302-2015.csl"

if [ ! -f "${CITATION_STYLES}" ]; then
  echo "Styles do not exist, downloading them..."
    curl -o "${CITATION_STYLES}" "${STYLES_URL}"
fi

for document in *.md; do
  echo "processing ${document}"
  pandoc --citeproc "${document}" -s -o "${OUTPUT_DIR}/${document%.md}.docx"
done
