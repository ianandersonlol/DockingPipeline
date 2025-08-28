import os
import pandas as pd
import shutil

def process_directory(dirpath, top5_dir, combined_df):
    print(f"Processing directory: {dirpath}")
    
    results_dir = os.path.join(dirpath, 'results')
    if not os.path.exists(results_dir):
        print(f"Results directory not found in {dirpath}. Skipping this directory.")
        return
    
    filenames = [filename for filename in os.listdir(results_dir) if filename.endswith('.sc')]
    score_list = []

    for filename in filenames:
        print(f"Reading file: {filename}")
        file_path = os.path.join(results_dir, filename)
        df = pd.read_csv(file_path, sep='\s+')  # Use sep='\s+' to handle whitespace separation
        if 'SCORE:' in df.columns:
            del df['SCORE:']
        
        # Check if 'description' column exists to avoid KeyError
        if 'description' in df.columns:
            # Create the 'File Name' column using 'description' values
            df['File Name'] = df['description'].apply(lambda x: f"{x}.pdb")
        else:
            print(f"'description' column not found in {filename}. Skipping 'File Name' generation for this file.")
        
        score_list.append(df)

    if score_list:
        print(f"Combining dataframes for {dirpath}")
        # Concatenate all dataframes into one
        df2 = pd.concat(score_list, ignore_index=True)

        # Print the lowest all_cst value before filtering
        if not df2.empty:
            lowest_all_cst = df2['all_cst'].min()
            print(f"Lowest all_cst for {os.path.basename(dirpath)}: {lowest_all_cst}")
        else:
            print(f"No valid entries for {os.path.basename(dirpath)}")
            return

        protein_name = os.path.basename(dirpath)
        
        # Filter rows based on condition
        df_filtered = df2[df2['all_cst'] < 1]
        
        entries_for_csv = []
        
        # If there are entries that pass the threshold, take top 5 by total_score
        if not df_filtered.empty:
            # Sort the filtered dataframe by total_score
            df_top5 = df_filtered.sort_values('total_score').head(5)
            
            # Copy files for top 5
            for rank in range(len(df_top5)):
                original_file = df_top5.iloc[rank]['File Name']
                new_file_name = f"{protein_name}_rank{rank+1}.pdb"
                try:
                    shutil.copy2(os.path.join(results_dir, original_file), os.path.join(top5_dir, new_file_name))
                    print(f"Copied {original_file} to {new_file_name}")
                except FileNotFoundError:
                    print(f"File {original_file} not found in {results_dir}. Skipping this file.")
            
            # Add protein name and rank to the dataframe for CSV output
            df_top5['Protein'] = protein_name
            df_top5['Rank'] = range(1, len(df_top5) + 1)
            
            # Only keep the columns we want for the output
            df_slim = df_top5[['all_cst', 'total_score', 'File Name', 'Protein', 'Rank']]
            entries_for_csv.append(df_slim)
            
        else:
            # If no entries pass the threshold, just get the one with the lowest all_cst
            df_lowest = df2.loc[df2['all_cst'].idxmin()].to_frame().T
            df_lowest['Protein'] = protein_name
            df_lowest['Rank'] = 'Failed'  # Mark as failed to pass threshold
            
            # Only keep the columns we want for the output
            df_slim = df_lowest[['all_cst', 'total_score', 'File Name', 'Protein', 'Rank']]
            entries_for_csv.append(df_slim)
        
        if entries_for_csv:
            combined_df.append(pd.concat(entries_for_csv, ignore_index=True))
    else:
        print(f"No valid .sc files found in {dirpath}. Skipping this directory.")

# Main script
top5_dir = os.path.join(os.getcwd(), 'top5')
os.makedirs(top5_dir, exist_ok=True)

current_dir = os.getcwd()
subdirectories = [os.path.join(current_dir, sub_dir) for sub_dir in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, sub_dir))]

print(f"Found {len(subdirectories)} subdirectories to process.")

combined_df = []

for subdir in subdirectories:
    process_directory(subdir, top5_dir, combined_df)

if combined_df:
    combined_df = pd.concat(combined_df, ignore_index=True)
    # Rename columns for clarity
    combined_df.rename(columns={'all_cst': 'all_cst', 'total_score': 'energy', 'File Name': 'pdb_name'}, inplace=True)
    combined_df.to_csv(os.path.join(os.getcwd(), 'top5_combined.csv'), index=False)
    print("Combined CSV file created: top5_combined.csv")

print("Process completed.")
