#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import time
import re
from pathlib import Path

class PipelineRunner:
    def __init__(self, method_dir, dry_run=False):
        self.method_dir = Path(method_dir).resolve()
        self.dry_run = dry_run
        self.job_ids = {}
        
        if not self.method_dir.exists():
            raise ValueError(f"Method directory {self.method_dir} does not exist!")
        
        # Create logs directory
        self.logs_dir = self.method_dir / 'logs'
        if not dry_run:
            self.logs_dir.mkdir(exist_ok=True)
        
        print(f"Pipeline runner initialized for: {self.method_dir}")
        print(f"Logs will be saved to: {self.logs_dir}")
        if dry_run:
            print("DRY RUN MODE - No jobs will be submitted")
    
    def run_local_command(self, script_path, description):
        """Run a command locally (for quick scripts)"""
        full_path = self.method_dir / script_path
        print(f"\n=== {description} ===")
        print(f"Running: {script_path}")
        
        if self.dry_run:
            print(f"[DRY RUN] Would run: python {full_path}")
            return True
        
        if not full_path.exists():
            print(f"Warning: {full_path} not found, skipping...")
            return False
        
        try:
            if script_path.endswith('.py'):
                result = subprocess.run(['python', str(full_path)], 
                                      cwd=self.method_dir, 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=600)  # 10 minute timeout for local scripts
            elif script_path.endswith('.sh'):
                result = subprocess.run(['bash', str(full_path)], 
                                      cwd=self.method_dir, 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=600)
            else:
                print(f"Unknown script type: {script_path}")
                return False
            
            if result.returncode == 0:
                print(f"✓ {description} completed successfully")
                if result.stdout.strip():
                    print(f"Output: {result.stdout.strip()}")
                return True
            else:
                print(f"✗ {description} failed with return code {result.returncode}")
                if result.stderr.strip():
                    print(f"Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ {description} timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"✗ {description} failed with exception: {e}")
            return False
    
    def submit_slurm_job(self, script_path, job_name, description, depends_on=None, 
                        time_limit="3-00:00:00", memory="16GB", cpus=4):
        """Submit a SLURM job and return job ID"""
        full_path = self.method_dir / script_path
        print(f"\n=== {description} ===")
        print(f"Submitting SLURM job: {script_path}")
        
        if not full_path.exists():
            print(f"Warning: {full_path} not found, skipping...")
            return None
        
        # Create SLURM script
        slurm_script_content = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --time={time_limit}
#SBATCH --ntasks={cpus}
#SBATCH --mem={memory}
#SBATCH --partition=low
#SBATCH --output=logs/{job_name}_%j.out
#SBATCH --error=logs/{job_name}_%j.err
"""
        
        # Add dependency if specified
        if depends_on:
            if isinstance(depends_on, list):
                dep_string = ":".join(depends_on)
                slurm_script_content += f"#SBATCH --dependency=afterok:{dep_string}\n"
            else:
                slurm_script_content += f"#SBATCH --dependency=afterok:{depends_on}\n"
        
        slurm_script_content += f"\ncd {self.method_dir}\n"
        
        # Add the actual command
        if script_path.endswith('.py'):
            slurm_script_content += "module load conda/latest\n"
            slurm_script_content += f"python {script_path}\n"
        elif script_path.endswith('.sh'):
            slurm_script_content += f"bash {script_path}\n"
        else:
            slurm_script_content += f"{script_path}\n"
        
        # Write temporary SLURM script
        temp_script = self.method_dir / f"{job_name}_submit.sh"
        with open(temp_script, 'w') as f:
            f.write(slurm_script_content)
        
        if self.dry_run:
            print(f"[DRY RUN] Would submit job with dependency: {depends_on}")
            print(f"[DRY RUN] SLURM script would be:")
            print(slurm_script_content)
            return f"FAKE_JOB_ID_{job_name}"
        
        try:
            # Submit the job
            result = subprocess.run(['sbatch', str(temp_script)], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.method_dir)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output
                job_id_match = re.search(r'Submitted batch job (\d+)', result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"✓ Job submitted successfully: Job ID {job_id}")
                    self.job_ids[job_name] = job_id
                    return job_id
                else:
                    print(f"✗ Could not extract job ID from: {result.stdout}")
                    return None
            else:
                print(f"✗ Job submission failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"✗ Job submission failed with exception: {e}")
            return None
        finally:
            # Clean up temporary script
            if temp_script.exists():
                temp_script.unlink()
    
    def read_relax_job_ids(self):
        """Read relaxation job IDs from the file created by bulkrelax.py"""
        job_ids_file = self.method_dir / 'relax_job_ids.txt'
        
        if not job_ids_file.exists():
            print(f"Warning: Relax job IDs file not found: {job_ids_file}")
            return []
        
        try:
            with open(job_ids_file, 'r') as f:
                job_ids = [line.strip() for line in f if line.strip()]
                print(f"Found {len(job_ids)} relaxation job IDs: {job_ids}")
                return job_ids
        except Exception as e:
            print(f"Error reading relax job IDs file: {e}")
            return []
    
    def read_docking_job_ids(self):
        """Read docking job IDs from the file created by runall.sh"""
        job_ids_file = self.method_dir / 'pdbs' / 'lowest_energies' / 'docking_job_ids.txt'
        
        if not job_ids_file.exists():
            print(f"Warning: Docking job IDs file not found: {job_ids_file}")
            return []
        
        try:
            with open(job_ids_file, 'r') as f:
                job_ids = [line.strip() for line in f if line.strip()]
                print(f"Found {len(job_ids)} docking job IDs: {job_ids}")
                return job_ids
        except Exception as e:
            print(f"Error reading docking job IDs file: {e}")
            return []
    
    def submit_relax_dependent_job(self, script_path, job_name, description, relax_job_id,
                                 time_limit="3-00:00:00", memory="16GB", cpus=4):
        """Submit a job that depends on relaxation jobs (reads IDs from file)"""
        print(f"\n=== {description} ===")
        print(f"Creating job that waits for relaxation jobs to complete: {script_path}")
        
        full_path = self.method_dir / script_path
        if not full_path.exists():
            print(f"Warning: {full_path} not found, skipping...")
            return None
        
        # Create a wrapper script that waits for relax jobs, then runs the actual script
        wrapper_script_content = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --time={time_limit}
#SBATCH --ntasks={cpus}
#SBATCH --mem={memory}
#SBATCH --partition=low
#SBATCH --output=logs/{job_name}_%j.out
#SBATCH --error=logs/{job_name}_%j.err
#SBATCH --dependency=afterok:{relax_job_id}

cd {self.method_dir}

# Wait for relax job IDs file to be created
echo "Waiting for relax job IDs file..."
timeout=300  # 5 minutes timeout
elapsed=0
while [ ! -f "relax_job_ids.txt" ] && [ $elapsed -lt $timeout ]; do
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ ! -f "relax_job_ids.txt" ]; then
    echo "Error: relax_job_ids.txt not created within timeout"
    exit 1
fi

# Read job IDs and wait for them
echo "Reading relaxation job IDs..."
relax_jobs=$(cat relax_job_ids.txt | tr '\\n' ':' | sed 's/:$//')
if [ -z "$relax_jobs" ]; then
    echo "No relaxation job IDs found"
    exit 1
fi

echo "Waiting for relaxation jobs to complete: $relax_jobs"

# Submit a dependency job that waits for all relaxation jobs
cat > temp_wait_script.sh << EOF
#!/bin/bash
#SBATCH --job-name={job_name}_wait
#SBATCH --time=1:00:00
#SBATCH --partition=low
#SBATCH --output=logs/{job_name}_wait_%j.out
#SBATCH --error=logs/{job_name}_wait_%j.err
#SBATCH --dependency=afterok:$relax_jobs

cd {self.method_dir}
"""

        if script_path.endswith('.py'):
            wrapper_script_content += "module load conda/latest\n"
            wrapper_script_content += f"python {script_path}\n"
        elif script_path.endswith('.sh'):
            wrapper_script_content += f"bash {script_path}\n"
        else:
            wrapper_script_content += f"{script_path}\n"
            
        wrapper_script_content += """
EOF

# Submit the waiting job
sbatch temp_wait_script.sh
rm temp_wait_script.sh
"""

        # Write temporary wrapper script
        temp_script = self.method_dir / f"{job_name}_wrapper.sh"
        with open(temp_script, 'w') as f:
            f.write(wrapper_script_content)
        
        if self.dry_run:
            print(f"[DRY RUN] Would submit wrapper job that waits for relaxation")
            print(f"[DRY RUN] Wrapper script would be:")
            print(wrapper_script_content)
            return f"FAKE_WRAPPER_JOB_ID_{job_name}"
        
        try:
            # Submit the wrapper job
            result = subprocess.run(['sbatch', str(temp_script)], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.method_dir)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output
                job_id_match = re.search(r'Submitted batch job (\d+)', result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"✓ Wrapper job submitted successfully: Job ID {job_id}")
                    self.job_ids[job_name] = job_id
                    return job_id
                else:
                    print(f"✗ Could not extract job ID from: {result.stdout}")
                    return None
            else:
                print(f"✗ Wrapper job submission failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"✗ Wrapper job submission failed with exception: {e}")
            return None
        finally:
            # Clean up temporary script
            if temp_script.exists():
                temp_script.unlink()
    
    def submit_docking_dependent_job(self, script_path, job_name, description, docking_job_id,
                                   time_limit="1:00:00", memory="8GB", cpus=1):
        """Submit a job that depends on docking jobs (reads IDs from file)"""
        print(f"\n=== {description} ===")
        print(f"Creating job that waits for docking jobs to complete: {script_path}")
        
        full_path = self.method_dir / script_path
        if not full_path.exists():
            print(f"Warning: {full_path} not found, skipping...")
            return None
        
        # Create a wrapper script that waits for docking jobs, then runs the actual script
        wrapper_script_content = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --time={time_limit}
#SBATCH --ntasks={cpus}
#SBATCH --mem={memory}
#SBATCH --partition=low
#SBATCH --output=logs/{job_name}_%j.out
#SBATCH --error=logs/{job_name}_%j.err
#SBATCH --dependency=afterok:{docking_job_id}

cd {self.method_dir}/pdbs/lowest_energies

# Wait for docking job IDs file to be created
echo "Waiting for docking job IDs file..."
timeout=300  # 5 minutes timeout
elapsed=0
while [ ! -f "docking_job_ids.txt" ] && [ $elapsed -lt $timeout ]; do
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ ! -f "docking_job_ids.txt" ]; then
    echo "Error: docking_job_ids.txt not created within timeout"
    exit 1
fi

# Read job IDs and wait for them
echo "Reading docking job IDs..."
docking_jobs=$(cat docking_job_ids.txt | tr '\\n' ':' | sed 's/:$//')
if [ -z "$docking_jobs" ]; then
    echo "No docking job IDs found"
    exit 1
fi

echo "Waiting for docking jobs to complete: $docking_jobs"

# Submit a dependency job that waits for all docking jobs
cat > temp_wait_script.sh << EOF
#!/bin/bash
#SBATCH --job-name={job_name}_wait
#SBATCH --time={time_limit}
#SBATCH --partition=low
#SBATCH --output=logs/{job_name}_wait_%j.out
#SBATCH --error=logs/{job_name}_wait_%j.err
#SBATCH --dependency=afterok:$docking_jobs

cd {self.method_dir}/pdbs/lowest_energies
module load conda/latest
python gettop5.py
EOF

# Submit the waiting job
sbatch temp_wait_script.sh
rm temp_wait_script.sh
"""

        # Write temporary wrapper script
        temp_script = self.method_dir / f"{job_name}_wrapper.sh"
        with open(temp_script, 'w') as f:
            f.write(wrapper_script_content)
        
        if self.dry_run:
            print(f"[DRY RUN] Would submit wrapper job that waits for docking")
            print(f"[DRY RUN] Wrapper script would be:")
            print(wrapper_script_content)
            return f"FAKE_DOCKING_WRAPPER_JOB_ID_{job_name}"
        
        try:
            # Submit the wrapper job
            result = subprocess.run(['sbatch', str(temp_script)], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.method_dir)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output
                job_id_match = re.search(r'Submitted batch job (\d+)', result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"✓ Docking wrapper job submitted successfully: Job ID {job_id}")
                    self.job_ids[job_name] = job_id
                    return job_id
                else:
                    print(f"✗ Could not extract job ID from: {result.stdout}")
                    return None
            else:
                print(f"✗ Docking wrapper job submission failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"✗ Docking wrapper job submission failed with exception: {e}")
            return None
        finally:
            # Clean up temporary script
            if temp_script.exists():
                temp_script.unlink()
    
    def wait_for_completion(self, description="pipeline"):
        """Wait for all submitted jobs to complete"""
        if not self.job_ids or self.dry_run:
            return
        
        print(f"\n=== Monitoring {description} ===")
        print(f"Waiting for {len(self.job_ids)} jobs to complete...")
        print(f"Job IDs: {list(self.job_ids.values())}")
        
        while True:
            try:
                # Check job status
                result = subprocess.run(['squeue', '-u', os.getenv('USER'), '-h'], 
                                      capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"Warning: Could not check job status: {result.stderr}")
                    time.sleep(60)
                    continue
                
                running_jobs = result.stdout.strip().split('\n') if result.stdout.strip() else []
                running_job_ids = set()
                
                for line in running_jobs:
                    if line.strip():
                        job_id = line.split()[0]
                        running_job_ids.add(job_id)
                
                # Check which of our jobs are still running
                our_running_jobs = []
                for job_name, job_id in self.job_ids.items():
                    if job_id in running_job_ids:
                        our_running_jobs.append(f"{job_name}({job_id})")
                
                if not our_running_jobs:
                    print("✓ All jobs completed!")
                    break
                else:
                    print(f"Still running: {', '.join(our_running_jobs)}")
                    time.sleep(60)  # Check every minute
                    
            except KeyboardInterrupt:
                print("\nMonitoring interrupted by user")
                break
            except Exception as e:
                print(f"Error checking job status: {e}")
                time.sleep(60)
    
    def run_full_pipeline(self):
        """Run the complete structure prediction pipeline"""
        print(f"\n🚀 Starting full pipeline for {self.method_dir.name}")
        
        # Phase 1: Quick local organization steps
        print("\n" + "="*60)
        print("PHASE 1: Structure Organization (Local)")
        print("="*60)
        
        success = True
        success &= self.run_local_command('pdbs/organizepdbs.py', 'Organizing PDB files')
        
        if not success:
            print("❌ Phase 1 failed. Stopping pipeline.")
            return False
        
        # Phase 2: Cleaning (can be heavy, submit as job)
        print("\n" + "="*60)
        print("PHASE 2: PDB Cleaning (SLURM)")
        print("="*60)
        
        clean_job = self.submit_slurm_job(
            'pdbs/cleanpdbs.sh',
            f'{self.method_dir.name}_clean',
            'Cleaning PDB files with Rosetta',
            time_limit="2:00:00",
            memory="8GB",
            cpus=1
        )
        
        if not clean_job:
            print("❌ Phase 2 job submission failed. Stopping pipeline.")
            return False
        
        # Phase 3: Organize cleaned files (depends on cleaning)
        organize_cleaned_job = self.submit_slurm_job(
            'pdbs/organizecleanedpdbs.py',
            f'{self.method_dir.name}_orgclean',
            'Organizing cleaned PDB files',
            depends_on=clean_job,
            time_limit="30:00",
            memory="4GB",
            cpus=1
        )
        
        # Phase 4: Bulk relax (depends on organized cleaned files)
        print("\n" + "="*60)
        print("PHASE 3: Structure Relaxation (SLURM)")
        print("="*60)
        
        relax_job = self.submit_slurm_job(
            'pdbs/bulkrelax.py',
            f'{self.method_dir.name}_relax',
            'Submitting Rosetta relaxation jobs',
            depends_on=organize_cleaned_job,
            time_limit="1:00:00",
            memory="4GB",
            cpus=1
        )
        
        # Phase 5: Organize energies (depends on all relax jobs completing)
        organize_energies_job = self.submit_relax_dependent_job(
            'pdbs/organizeenergies.py',
            f'{self.method_dir.name}_orgenergy',
            'Organizing relaxation energy results (waits for all relaxation jobs)',
            relax_job,
            time_limit="1:00:00",
            memory="8GB",
            cpus=1
        )
        
        # Phase 6: Ligand placement (depends on energy organization)
        print("\n" + "="*60)
        print("PHASE 4: Ligand Placement (SLURM)")
        print("="*60)
        
        ligand_job = self.submit_slurm_job(
            'pdbs/lowest_energies/placeligands.py',
            f'{self.method_dir.name}_ligand',
            'Adding ligands to structures with PyMOL',
            depends_on=organize_energies_job,
            time_limit="2:00:00",
            memory="16GB",
            cpus=1
        )
        
        # Phase 7: Docking setup (depends on ligand placement)
        print("\n" + "="*60)
        print("PHASE 5: Docking Pipeline (SLURM)")
        print("="*60)
        
        setup_job = self.submit_slurm_job(
            'pdbs/lowest_energies/getscripts.py',
            f'{self.method_dir.name}_setup',
            'Setting up docking scripts',
            depends_on=ligand_job,
            time_limit="30:00",
            memory="4GB",
            cpus=1
        )
        
        # Create results folders
        mkdir_job = self.submit_slurm_job(
            'pdbs/lowest_energies/makeresultsfolder.sh',
            f'{self.method_dir.name}_mkdir',
            'Creating results directories',
            depends_on=setup_job,
            time_limit="10:00",
            memory="2GB",
            cpus=1
        )
        
        # Run all docking jobs
        docking_job = self.submit_slurm_job(
            'pdbs/lowest_energies/runall.sh',
            f'{self.method_dir.name}_dock',
            'Submitting all docking jobs',
            depends_on=mkdir_job,
            time_limit="30:00",
            memory="4GB",
            cpus=1
        )
        
        # Phase 8: Final analysis (depends on all docking completing)
        final_job = self.submit_docking_dependent_job(
            'pdbs/lowest_energies/gettop5.py',
            f'{self.method_dir.name}_top5',
            'Extracting top 5 docking results (waits for all docking jobs)',
            docking_job,
            time_limit="1:00:00",
            memory="8GB",
            cpus=1
        )
        
        print("\n" + "="*60)
        print("🎯 PIPELINE SUBMITTED SUCCESSFULLY!")
        print("="*60)
        print(f"Method: {self.method_dir.name}")
        print(f"Total jobs submitted: {len(self.job_ids)}")
        print("\nJob Summary:")
        for job_name, job_id in self.job_ids.items():
            print(f"  {job_name}: {job_id}")
        
        print(f"\nMonitor progress with:")
        print(f"  squeue -u {os.getenv('USER')}")
        print(f"  watch -n 30 'squeue -u {os.getenv('USER')}'")
        
        return True
    
    def monitor_pipeline(self):
        """Monitor currently running pipeline"""
        self.wait_for_completion("pipeline")

def main():
    parser = argparse.ArgumentParser(description='Run the complete structure prediction and docking pipeline')
    parser.add_argument('method_dir', help='Path to method directory (e.g., Methods/ESMFold)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be run without actually submitting jobs')
    parser.add_argument('--monitor-only', action='store_true',
                       help='Only monitor currently running jobs (do not submit new ones)')
    
    args = parser.parse_args()
    
    try:
        runner = PipelineRunner(args.method_dir, dry_run=args.dry_run)
        
        if args.monitor_only:
            runner.monitor_pipeline()
        else:
            success = runner.run_full_pipeline()
            if not success:
                sys.exit(1)
                
            if not args.dry_run:
                print(f"\n🔍 Starting pipeline monitoring...")
                runner.wait_for_completion()
                print(f"\n✅ Pipeline completed for {args.method_dir}!")
        
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()