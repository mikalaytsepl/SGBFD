import os
import shutil

DATASET_ROOT_PATH = "/home/miko/diploma_thing/Datasets/HR_128"

if __name__ == "__main__":
    if not os.path.exists(DATASET_ROOT_PATH) or os.path.isdir(DATASET_ROOT_PATH) is False:
        raise FileNotFoundError(f"Dataset root path '{DATASET_ROOT_PATH}' does not exist or is not a directory.")

    output_dataset_path = "/home/miko/diploma_thing/Datasets/HR_128_normalized"
    if not os.path.exists(output_dataset_path):
        os.makedirs(output_dataset_path)

    for file in os.listdir(DATASET_ROOT_PATH):

        identity_prefix = file.split("_")[0]
        pose_prefix = file.split("_")[3]
        smile_prefix = file.split("_")[2]
        
        identity_folder_path = os.path.join(output_dataset_path, identity_prefix)

        if not os.path.exists(identity_folder_path): 
            os.makedirs(identity_folder_path)

        if pose_prefix == "051" and smile_prefix == "01":
            source_file_path = os.path.join(DATASET_ROOT_PATH, file)
            dest_file_path = os.path.join(identity_folder_path, file)
            shutil.copy2(source_file_path, dest_file_path)