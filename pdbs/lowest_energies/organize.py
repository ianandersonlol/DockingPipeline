import os
import shutil

# Path to the directory containing the PDB files
pdb_dir = os.getcwd()

# Loop through each file in the pdb directory
for pdb_file in os.listdir(pdb_dir):
    if pdb_file.endswith(".pdb"):
        # Extract the first four characters as the protein name
        protein_name = pdb_file[:4]
        protein_dir = os.path.join(pdb_dir, protein_name)
        
        # Create a directory for the protein if it doesn't exist
        if not os.path.exists(protein_dir):
            os.makedirs(protein_dir)
        
        # Move the PDB file to the new directory
        shutil.move(os.path.join(pdb_dir, pdb_file), os.path.join(protein_dir, pdb_file))
        print(f"Moved {pdb_file} to {protein_dir}")

# Print completion message
print("All PDB files have been organized into their respective protein folders.")

