import os
import bz2
import shutil

path_to_traverse = "/home/miko/diploma_thing/Datasets/ferret/colorferet/dvd2/data/images"


output_dataset_path = "/home/miko/diploma_thing/Datasets/filtered_dataset__ferret_5"

threshold = 5


def count_fab(files: list[str]) -> int:
    return sum(
        name.endswith("_fa.ppm.bz2") or name.endswith("_fb.ppm.bz2")
        for name in files
    )


# decompressing image and saving it into dataset 
def extract_bz2_to_ppm(src_path: str, dst_path: str):
    with bz2.open(src_path, "rb") as f_in:
        with open(dst_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


# check if output dir exists
os.makedirs(output_dataset_path, exist_ok=True)

imgdirs = os.listdir(path_to_traverse)

for imgdir in imgdirs:
    full_dir_path = os.path.join(path_to_traverse, imgdir)

    if not os.path.isdir(full_dir_path):
        continue

    files = os.listdir(full_dir_path)

    if count_fab(files) >= threshold:
        print(f"Processing {imgdir}")

        # Create the same idenity in the filtered dataset
        target_dir = os.path.join(output_dataset_path, imgdir)
        os.makedirs(target_dir, exist_ok=True)

        for name in files:
            if name.endswith("_fa.ppm.bz2") or name.endswith("_fb.ppm.bz2"):
                src_file = os.path.join(full_dir_path, name)

                # extract and leave just ppm
                dst_filename = name.replace(".bz2", "")
                dst_file = os.path.join(target_dir, dst_filename)

                extract_bz2_to_ppm(src_file, dst_file)
                