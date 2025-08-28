import os
import pandas as pd
import shutil

# Set the directory where the script is running (you might want to adjust this)
base_dir = os.getcwd()

# Create a directory for the lowest energy pdbs if it doesn't exist
lowest_energies_dir = os.path.join(base_dir, "lowest_energies")
if not os.path.exists(lowest_energies_dir):
    os.makedirs(lowest_energies_dir)

# Loop through each directory in the base directory
for dirname in os.listdir(base_dir):
    if "_cleaned" in dirname:
        relax_results_path = os.path.join(base_dir, dirname, "relax_results")
        if os.path.exists(relax_results_path):
            lowest_score = float('inf')
            lowest_score_file = None
            
            # Loop through each file in the relax_results directory
            for filename in os.listdir(relax_results_path):
                if filename.endswith(".sc"):
                    # Read the score file
                    filepath = os.path.join(relax_results_path, filename)
                    try:
                        # Adjusted to skip the initial lines and to correctly parse the header
                        score_data = pd.read_csv(filepath, delim_whitespace=True, skiprows=1, header=None)
                        score_data.columns = score_data.iloc[0]  # Set the first row as header
                        score_data = score_data[1:]  # Remove the header row from the data
                        score_data['total_score'] = pd.to_numeric(score_data['total_score'], errors='coerce')  # Convert total_score to numeric, coercing errors

                        # Check for rows where total_score could not be converted
                        if score_data['total_score'].isnull().any():
                            print(f"Non-numeric total_score values found in {filepath}")

                        # Find the row with the lowest total_score
                        min_row = score_data.loc[score_data['total_score'].idxmin()]
                        if min_row['total_score'] < lowest_score:
                            lowest_score = min_row['total_score']
                            lowest_score_file = min_row['description'] + ".pdb"
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")
            
            # If a lowest score file was found, copy it to the lowest_energies directory
            if lowest_score_file:
                source_file = os.path.join(relax_results_path, lowest_score_file)
                dest_file = os.path.join(lowest_energies_dir, lowest_score_file)
                shutil.copy2(source_file, dest_file)
                print(f"Copied {lowest_score_file} to {lowest_energies_dir}")
            else:
                print(f"No valid .sc files found in {relax_results_path}")

# Print completion message
print("Script completed. All lowest energy PDBs are copied to 'lowest_energies'.")

