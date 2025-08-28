#!/bin/bash

#SBATCH --partition=gpu-a100
#SBATCH --account=genome-center-grp
#SBATCH --time=72:00:00
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --ntasks=8
#SBATCH --output=output.txt
#SBATCH --error=error.txt

if [ $# -lt 2 ]; then
    echo "Usage: $0 <fasta_file_path> <output_directory>"
    exit 1
fi

# Activate the conda environment
export TORCH_HOME=/quobyte/jbsiegelgrp/aian/.cache/torch

# Activate the conda environment
. "/quobyte/jbsiegelgrp/software/anaconda3/etc/profile.d/conda.sh"
conda activate /quobyte/jbsiegelgrp/aian/.conda/envs/esmfold

# Run the Python script with the FASTA file path and output directory as arguments
python /quobyte/jbsiegelgrp/aian/scripts/esmfold.py "$1" "$2"
