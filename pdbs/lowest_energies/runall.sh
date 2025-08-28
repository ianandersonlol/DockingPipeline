#!/bin/bash

# Find all run.sh files and iterate over them
find . -name "run.sh" -type f | while read -r script; do
  # Get the directory containing the run.sh file
  dir=$(dirname "$script")
  
  # Change to that directory
  cd "$dir" || continue
  
  # Submit the run.sh file using sbatch
  sbatch run.sh
  
  # Go back to the original directory
  cd - > /dev/null
done

