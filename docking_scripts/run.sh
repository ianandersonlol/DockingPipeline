#!/bin/bash
#SBATCH --job-name=dock4real
#SBATCH --output=logs
#SBATCH --mem 4G
#SBATCH --nodes 1
#SBATCH --time 3-0
#SBATCH --partition=low
#SBATCH --requeue
#SBATCH --array=1-10

/quobyte/jbsiegelgrp/software/Rosetta_314/rosetta/main/source/bin/rosetta_scripts.static.linuxgccrelease -database /quobyte/jbsiegelgrp/software/Rosetta_314/rosetta/main/database @flags -overwrite -parser:protocol docking_new.xml -s esm_lig.pdb -out:path:all results -nstruct 100 -suffix _${SLURM_ARRAY_TASK_ID}_${SLURM_PROCID} -score:weights ref2015_cst

