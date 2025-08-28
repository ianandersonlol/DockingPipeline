import os
import shutil

# Get the current working directory
cwd = os.getcwd()

# List all directories in the current directory
directories = [d for d in os.listdir(cwd) if os.path.isdir(d)]

# Iterate over the directories
for directory in directories:
    # Construct the directory path
    dir_path = os.path.join(cwd, directory)
    
    # List all files in the directory
    files = os.listdir(dir_path)
    
    # Loop through files to find .pdb files with '_A.pdb'
    for file in files:
        if file.endswith('_A.pdb'):
            # Construct the old file path
            old_file_path = os.path.join(dir_path, file)
            
            # Extract the name without '_A' and '.pdb'
            protein_name = file[:-6]
            
            # Create the new directory in the main directory named '[name of protein]_cleaned'
            new_folder_name = protein_name + '_cleaned'
            new_folder_path = os.path.join(cwd, new_folder_name)
            
            # Check if the folder already exists, if not, create it
            if not os.path.exists(new_folder_path):
                os.makedirs(new_folder_path)
            
            # Move the pdb file into the new folder
            new_file_path = os.path.join(new_folder_path, file)
            shutil.move(old_file_path, new_file_path)
            
            # Construct the final file path with the new name
            final_file_path = os.path.join(new_folder_path, protein_name + '.pdb')
            
            # Rename the file to drop the '_A'
            os.rename(new_file_path, final_file_path)

print("All applicable files have been moved to their respective '_cleaned' folders and renamed.")
