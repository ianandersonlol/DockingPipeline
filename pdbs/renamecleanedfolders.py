import os

# Get the current working directory
cwd = os.getcwd()

# List all items in the current directory
items = os.listdir(cwd)

# Iterate over the items
for item in items:
    # Check if the item is a directory and if '_A' is in its name
    if os.path.isdir(item) and '_A' in item:
        # Construct the new directory name by replacing '_A' with '_cleaned'
        new_name = item.replace('_A', '_cleaned')
        
        # Rename the directory
        os.rename(item, new_name)

print("All applicable directories have been renamed.")

