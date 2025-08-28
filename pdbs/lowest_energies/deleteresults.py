import os
import shutil

def delete_results_folders(base_directory):
    for root, dirs, files in os.walk(base_directory):
        for dir_name in dirs:
            if dir_name == 'results':
                results_dir_path = os.path.join(root, dir_name)
                response = input(f"Do you want to delete the folder: {results_dir_path}? (y/n): ")
                if response.lower() == 'y':
                    shutil.rmtree(results_dir_path)
                    print(f"Deleted: {results_dir_path}")
                else:
                    print(f"Skipped: {results_dir_path}")

# Get the current directory
base_directory = os.getcwd()
delete_results_folders(base_directory)

