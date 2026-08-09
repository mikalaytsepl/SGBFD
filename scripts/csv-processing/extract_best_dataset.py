import json
import argparse 
import os
import shutil

parser = argparse.ArgumentParser(description="Extract top K best images per identity from OFIQ CSV output.")
parser.add_argument("--input_json_path", type=str, help="Path to the OFIQ CSV output file.")
parser.add_argument("--output_dataset_path", type=str, help="Path to the output dataset directory.")
parser.add_argument("--dataset-root", type=str, help="Root path to the dataset for trimming file paths.")

for arg in ["input_json_path", "output_dataset_path", "dataset_root"]:
    if not getattr(parser.parse_args(), arg):
        parser.error(f"Argument --{arg} is required.")

args = parser.parse_args()

# data is in the form of dict of "identity: [list of file paths]"
with open(args.input_json_path, "r") as f:
    data = json.load(f)

first_identity = next(iter(data))
first_path = data[first_identity][0]
dataset_name = first_path.split("/")[0]
output_root = os.path.join(args.output_dataset_path, f"{dataset_name}_filtered")
os.makedirs(output_root, exist_ok=True)

for identity in data.keys():
    identity_output_path = os.path.join(output_root, identity)
    os.makedirs(identity_output_path, exist_ok=True)
    for file_path in data[identity]:
        # Trim the file path to keep only the dataset/identity/file part
        trimmed_path = "/".join(file_path.split("/")[-3:])
        # Copy the file to the new location
        source_path = os.path.join(args.dataset_root, trimmed_path)
        destination_path = os.path.join(identity_output_path, trimmed_path.split("/")[-1])
        shutil.copy2(source_path, destination_path)