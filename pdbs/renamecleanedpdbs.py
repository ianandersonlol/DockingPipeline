import os

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
            # Construct the old and new file paths
            old_file_path = os.path.join(dir_path, file)
            new_file_name = file.replace('_A.pdb', '.pdb')
            new_file_path = os.path.join(dir_path, new_file_name)
            
            # Rename the file
            os.rename(old_file_path, new_file_path)

print("Renaming complete. '_A' removed from relevant .pdb files.")

