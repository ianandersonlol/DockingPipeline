import os

# Path to the directory containing the .pdb files
directory_path = "/share/siegellab/aian/RotationProject/NewMarch2024/pdbs"

# Loop over all files in the directory
for filename in os.listdir(directory_path):
    # Check if the current file is a .pdb file
    if filename.endswith(".pdb"):
        # Generate the new filename:
        # 1. Split the filename on "_1", keeping the part before it
        # 2. Convert to lowercase
        new_filename = filename.split("_1")[0].lower() + ".pdb"
        
        # Full path for the current file and the new file
        old_file_path = os.path.join(directory_path, filename)
        new_file_path = os.path.join(directory_path, new_filename)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)
        print(f"Renamed '{filename}' to '{new_filename}'")

print("Finished processing files.")
