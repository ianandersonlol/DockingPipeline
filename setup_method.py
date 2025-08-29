#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
from pathlib import Path

def update_slurm_script(script_path, method_name):
    """Update SLURM script with proper partition and output naming"""
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Update partition to 'low'
    content = content.replace('#SBATCH --partition=gpu-a100', '#SBATCH --partition=low')
    
    # Update output naming to use SLURM variables
    content = content.replace('#SBATCH --output=output.txt', 
                             f'#SBATCH --output=output_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    content = content.replace('#SBATCH --error=error.txt', 
                             f'#SBATCH --error=error_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    content = content.replace('#SBATCH --output=log.txt', 
                             f'#SBATCH --output=log_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    
    # Update any hardcoded output files in scripts to use SLURM variables and logs directory
    content = content.replace('output.txt', 
                             f'logs/output_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    content = content.replace('error.txt', 
                             f'logs/error_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    content = content.replace('#SBATCH --output=log.txt', 
                             f'#SBATCH --output=logs/log_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    content = content.replace('#SBATCH --output=logs', 
                             f'#SBATCH --output=logs/logs_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_PROCID}}.txt')
    
    # Update Rosetta paths to correct locations
    content = content.replace('/share/siegellab/software/kschu/Rosetta/tools/protein_tools/scripts/clean_pdb.py',
                             '/quobyte/jbsiegelgrp/software/Rosetta_314/rosetta/main/tools/protein_tools/scripts/clean_pdb.py')
    
    with open(script_path, 'w') as f:
        f.write(content)

def update_method_specific_naming(file_path, method_name):
    """Update method-specific naming in Python scripts"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update the output PDB naming from 'esm_lig.pdb' to '{method_name}_lig.pdb'
    content = content.replace("'esm_lig.pdb'", f"'{method_name.lower()}_lig.pdb'")
    content = content.replace('"esm_lig.pdb"', f'"{method_name.lower()}_lig.pdb"')
    
    # Update any other hardcoded method names
    content = content.replace('ESMFold', method_name)
    content = content.replace('esmfold', method_name.lower())
    content = content.replace('esm_', f'{method_name.lower()}_')
    
    with open(file_path, 'w') as f:
        f.write(content)

def update_bulkrelax_for_job_tracking(file_path):
    """Modify bulkrelax.py to track spawned job IDs"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add job ID tracking functionality
    new_content = '''import os
import subprocess
import re

initial_working_dir = os.getcwd()
spawned_jobs = []  # Track all job IDs we spawn

for path, subdirs, files in os.walk(initial_working_dir):
    # Check if "_cleaned" is in the folder name
    if "_cleaned" in path:
        for name in files:
            # Check for .pdb files (not specifically ending with "_A.pdb")
            if name.endswith(".pdb"):
                filename = os.fsdecode(name)
                print('Generating Files for: ' + filename)
                submit_script_path = os.path.join(path, 'submit.sh')
                with open(submit_script_path, 'w') as submit_script:
                    submit_script.write('#!/bin/bash -l\\n')
                    submit_script.write('#SBATCH -J ' + filename + '\\n')
                    submit_script.write('#SBATCH -t 3000\\n')
                    submit_script.write('#SBATCH -n 4\\n')
                    submit_script.write('#SBATCH --mem 16GB\\n')
                    submit_script.write('#SBATCH -p low\\n')  # Updated to low partition
                    submit_script.write('#SBATCH --output=../../../logs/relax_' + filename + '_${SLURM_ARRAY_TASK_ID}_${SLURM_PROCID}.out\\n')
                    submit_script.write('#SBATCH --error=../../../logs/relax_' + filename + '_${SLURM_ARRAY_TASK_ID}_${SLURM_PROCID}.err\\n')
                    submit_script.write('#SBATCH --array=1-4\\n\\n')
                    submit_script.write('module load conda/latest\\n')
                    submit_script.write('/quobyte/jbsiegelgrp/software/Rosetta_314/rosetta/main/source/bin/relax.static.linuxgccrelease -database /quobyte/jbsiegelgrp/software/Rosetta_314/rosetta/main/database -overwrite -nstruct 50 -ex1 -ex2 -use_input_sc -flip_HNQ -no_optH false -user_tag ${SLURM_ARRAY_TASK_ID}_${SLURM_PROCID} -out:suffix _${SLURM_ARRAY_TASK_ID}_${SLURM_PROCID} -relax:constrain_relax_to_start_coords -relax:coord_constrain_sidechains -relax:ramp_constraints false -in:file:s ' + filename + ' -out:path:all relax_results\\n')

                # Change directory to where submit.sh is located
                os.chdir(path)

                # Submit the job using sbatch and capture job ID
                try:
                    result = subprocess.run(['sbatch', submit_script_path], 
                                          cwd=path, 
                                          capture_output=True, 
                                          text=True)
                    if result.returncode == 0:
                        # Extract job ID from sbatch output
                        job_id_match = re.search(r'Submitted batch job (\\d+)', result.stdout)
                        if job_id_match:
                            job_id = job_id_match.group(1)
                            spawned_jobs.append(job_id)
                            print(f'Submitted relaxation job for {filename}: Job ID {job_id}')
                        else:
                            print(f'Warning: Could not extract job ID from: {result.stdout}')
                    else:
                        print(f'Error submitting job for {filename}: {result.stderr}')
                except Exception as e:
                    print(f'Exception submitting job for {filename}: {e}')

                new_output = os.path.join(path, 'relax_results')
                if not os.path.exists(new_output):
                    os.makedirs(new_output)
                    print('Results folder not found for ' + name + '...creating...')

                # Change directory to the initial working directory
                os.chdir(initial_working_dir)

# Write job IDs to file for pipeline dependency tracking
job_ids_file = os.path.join(initial_working_dir, 'relax_job_ids.txt')
with open(job_ids_file, 'w') as f:
    for job_id in spawned_jobs:
        f.write(f'{job_id}\\n')

print(f'Complete! Spawned {len(spawned_jobs)} relaxation jobs.')
print(f'Job IDs written to: {job_ids_file}')
if spawned_jobs:
    print(f'Job IDs: {", ".join(spawned_jobs)}')
'''
    
    with open(file_path, 'w') as f:
        f.write(new_content)

def update_runall_for_job_tracking(file_path):
    """Modify runall.sh to track spawned docking job IDs"""
    new_content = '''#!/bin/bash

# Track all spawned job IDs
spawned_jobs=()

# Find all run.sh files and iterate over them
find . -name "run.sh" -type f | while read -r script; do
  # Get the directory containing the run.sh file
  dir=$(dirname "$script")
  
  # Change to that directory
  cd "$dir" || continue
  
  # Submit the run.sh file using sbatch and capture job ID
  output=$(sbatch run.sh)
  if [[ $? -eq 0 ]]; then
    # Extract job ID from sbatch output
    if [[ $output =~ Submitted\ batch\ job\ ([0-9]+) ]]; then
      job_id="${BASH_REMATCH[1]}"
      echo "Submitted docking job in $dir: Job ID $job_id"
      echo "$job_id" >> "$(pwd)/../docking_job_ids.txt"
    else
      echo "Warning: Could not extract job ID from: $output"
    fi
  else
    echo "Error: Failed to submit job in $dir"
  fi
  
  # Go back to the original directory  
  cd - > /dev/null
done

# Count the jobs
job_count=$(wc -l < docking_job_ids.txt 2>/dev/null || echo "0")
echo "Complete! Spawned $job_count docking jobs."
echo "Job IDs written to: docking_job_ids.txt"
'''
    
    with open(file_path, 'w') as f:
        f.write(new_content)

def setup_method(method_name):
    """Set up a new method directory based on the DockingPipeline template"""
    
    # Paths
    template_dir = Path('DockingPipeline')
    methods_dir = Path('Methods')
    method_dir = methods_dir / method_name
    
    # Check if template exists
    if not template_dir.exists():
        print(f"Error: Template directory {template_dir} not found!")
        return False
    
    # Create Methods directory if it doesn't exist
    methods_dir.mkdir(exist_ok=True)
    
    # Check if method already exists
    if method_dir.exists():
        response = input(f"Method '{method_name}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return False
        shutil.rmtree(method_dir)
    
    # Create method directory
    method_dir.mkdir(parents=True)
    print(f"Created directory: {method_dir}")
    
    # Copy the core pipeline components  
    components_to_copy = ['pdbs', 'docking_scripts']
    
    for component in components_to_copy:
        src_path = template_dir / component
        dst_path = method_dir / component
        
        if src_path.exists():
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
                print(f"Copied directory: {src_path} -> {dst_path}")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"Copied file: {src_path} -> {dst_path}")
        else:
            print(f"Warning: Template component {src_path} not found")
    
    # Copy individual Python scripts from template root
    root_scripts = ['getfastas.py']
    for script in root_scripts:
        src_path = template_dir / script
        dst_path = method_dir / script
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"Copied script: {src_path} -> {dst_path}")
    
    # Find and update all files
    print(f"\nUpdating files for method '{method_name}'...")
    
    # Update SLURM scripts
    slurm_scripts = list(method_dir.rglob("*.sh"))
    for script in slurm_scripts:
        print(f"Updating SLURM script: {script}")
        update_slurm_script(script, method_name)
    
    # Update Python scripts for method-specific naming
    python_scripts = list(method_dir.rglob("*.py"))
    for script in python_scripts:
        print(f"Updating Python script: {script}")
        update_method_specific_naming(script, method_name)
    
    # Special handling for bulkrelax.py to add job tracking
    bulkrelax_path = method_dir / 'pdbs' / 'bulkrelax.py'
    if bulkrelax_path.exists():
        print(f"Updating bulkrelax.py for job ID tracking: {bulkrelax_path}")
        update_bulkrelax_for_job_tracking(bulkrelax_path)
    
    # Special handling for runall.sh to add job tracking
    runall_path = method_dir / 'pdbs' / 'lowest_energies' / 'runall.sh'
    if runall_path.exists():
        print(f"Updating runall.sh for job ID tracking: {runall_path}")
        update_runall_for_job_tracking(runall_path)
    
    # Create a README for the new method
    readme_content = f"""# {method_name} Method Pipeline

This directory contains the pipeline for processing {method_name} predictions.

## Structure:
- `pdbs/`: Scripts for organizing and processing PDB files
- `pdbs/lowest_energies/`: Scripts for extracting top-ranked structures and ligand placement

## Usage:
1. Place your {method_name} prediction PDB files in the appropriate directory
2. Run the organization scripts in `pdbs/`
3. Use `pdbs/lowest_energies/` scripts for final processing

## Key Files:
- `pdbs/organizepdbs.py`: Organize raw prediction files
- `pdbs/lowest_energies/placeligands.py`: Add ligands to predictions (outputs {method_name.lower()}_lig.pdb)
- `pdbs/lowest_energies/gettop5.py`: Extract top 5 predictions

Note: All SLURM scripts have been configured for the 'low' partition with proper job naming.
"""
    
    readme_path = method_dir / 'README.md'
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"\nSuccess! Method '{method_name}' has been set up in {method_dir}")
    print(f"Created README: {readme_path}")
    print("\nNext steps:")
    print(f"1. Create a custom execution script for running {method_name} predictions")
    print(f"2. Place your {method_name} prediction files in the appropriate directory")
    print(f"3. Run the processing pipeline using the scripts in {method_dir}/pdbs/")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Set up a new protein structure prediction method pipeline')
    parser.add_argument('method_name', help='Name of the method (e.g., ColabFold, ChainFold)')
    
    args = parser.parse_args()
    
    if not args.method_name:
        print("Error: Method name is required!")
        sys.exit(1)
    
    # Validate method name
    method_name = args.method_name.strip()
    if not method_name.replace('_', '').replace('-', '').isalnum():
        print("Error: Method name should only contain letters, numbers, hyphens, and underscores")
        sys.exit(1)
    
    success = setup_method(method_name)
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()