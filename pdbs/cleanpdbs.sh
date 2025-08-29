#!/bin/bash

module load conda/latest

echo "Starting the cleaning process..."

# Find all .pdb files in subdirectories
pdb_files=$(find . -type f -name "*.pdb")

# Check if any .pdb files are found
if [ -n "$pdb_files" ]; then
    echo "Found .pdb files:"
    echo "$pdb_files"
    # Loop through each .pdb file
    for pdb in $pdb_files; do
        echo "Processing file: $pdb"
        # Execute the clean_pdb.py script with the given pdb file and chain A
        python2 /share/siegellab/software/kschu/Rosetta/tools/protein_tools/scripts/clean_pdb.py "${pdb}" A
    done
else
    echo "No .pdb files found."
fi

echo "Cleaning process complete."

