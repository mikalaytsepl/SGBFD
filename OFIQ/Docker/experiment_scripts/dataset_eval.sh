#!/bin/bash

# 1. Define input and output directory paths
INPUT_DIR="./dataset-in"
OUTPUT_DIR="./dataset-out"

declare -a DATASET_NAME

# Check how many datasets are inside the input directory
input_contents=($(ls "$INPUT_DIR"))
if (( ${#input_contents[@]} == 0 )); then 
    echo "FATAL: input directory empty." 1>&2
    exit 1
fi

if (( ${#input_contents[@]} > 1 )); then
    if [ -z "$DATASET_TO_USE" ]; then
        echo "FATAL: dataset not specified and number of datasets is more than 1, set DATASET_TO_USE variable." 1>&2
        exit 1 
    else
        DATASET_NAME="$DATASET_TO_USE"
    fi
else
    DATASET_NAME="${input_contents[0]}"
fi

# Ensure output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then 
    mkdir -p "$OUTPUT_DIR"
fi

echo "Evaluating dataset path: $INPUT_DIR/$DATASET_NAME"

# 2. Run OFIQ with valid variables
./install_x86_64_linux/Release/bin/OFIQSampleApp \
    -c ./data/ofiq_config.jaxn \
    -i "$INPUT_DIR/$DATASET_NAME/" \
    -o "$OUTPUT_DIR/${DATASET_NAME}.csv"