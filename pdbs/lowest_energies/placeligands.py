#!/usr/bin/env python
import pymol
from pymol import cmd
import os
import glob

def align_and_add_ligands(protein1_path, protein2_path, output_pdb):
    protein1_basename = os.path.basename(protein1_path)
    protein1_name, _ = os.path.splitext(protein1_basename)
    
    protein2_basename = os.path.basename(protein2_path)
    protein2_name, _ = os.path.splitext(protein2_basename)
    
    print(f"Loading {protein1_path} as {protein1_name}")
    cmd.do(f"load {protein1_path}, {protein1_name}")
    
    print(f"Loading {protein2_path} as {protein2_name}")
    cmd.do(f"load {protein2_path}, {protein2_name}")
    
    print(f"Aligning {protein2_name} to {protein1_name}")
    cmd.do(f"super {protein2_name}, {protein1_name}")
    
    print(f"Selecting and removing chain A from {protein1_name}")
    cmd.do(f"select chainA, {protein1_name} and chain A")
    cmd.do("remove chainA")
    
    print(f"Saving aligned protein with ligands as {output_pdb}")
    cmd.do(f"save {output_pdb}")
    
    cmd.do("delete all")
    
    print(f"Processed {protein2_path} and saved as {output_pdb}")

    # Find and prepend the .header file content
    header_path = glob.glob(os.path.join(os.path.dirname(protein2_path), '*.header'))
    if header_path:
        header_path = header_path[0]  # Take the first .header file found
        with open(header_path, 'r') as header_file:
            header_contents = header_file.read()
        
        with open(output_pdb, 'r') as pdb_file:
            pdb_contents = pdb_file.read()
        
        with open(output_pdb, 'w') as output_file:
            output_file.write(header_contents + '\n' + pdb_contents)
        
        print(f"Header from {header_path} added to {output_pdb}")

def main():
    root_dir = os.getcwd()
    for subdir, _, files in os.walk(root_dir):
        model1_lig_path = os.path.join(subdir, 'model1_lig.pdb')
        if not os.path.isfile(model1_lig_path):
            print(f"model1_lig.pdb not found in {subdir}")
            continue
        
        folder_name = os.path.basename(subdir)
        for file in files:
            if file.startswith(folder_name) and file.endswith('.pdb'):
                input_pdb_path = os.path.join(subdir, file)
                output_pdb_path = os.path.join(subdir, 'esm_lig.pdb')
                align_and_add_ligands(input_pdb_path, model1_lig_path, output_pdb_path)
                print(f"Processed {input_pdb_path} and saved as {output_pdb_path}")

if __name__ == "__main__":
    pymol.finish_launching(['pymol', '-qc'])
    cmd.reinitialize()
    
    main()

