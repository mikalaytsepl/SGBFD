import os
import bz2
import shutil
import cv2
import numpy as np

output_dataset_path = "/home/miko/diploma_thing/Datasets/filtered_dataset__ferret_3"

threshold = 3


def count_fab(files: list[str]) -> int:
    return sum(
        name.endswith("_fa.ppm.bz2") or name.endswith("_fb.ppm.bz2")
        for name in files
    )


# decompressing image and saving it into dataset 
def extract_bz2_to_jpg(src_path: str, dst_path: str):
    # Open the compressed PPM file and read the decompressed image bytes into memory.
    with bz2.open(src_path, "rb") as f_in:
        ppm_bytes = f_in.read()

    # OpenCV cannot decode directly from a bz2 stream, so convert the bytes
    # into a NumPy buffer first and then let OpenCV parse the PPM image data.
    img_array = np.frombuffer(ppm_bytes, dtype=np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # Bail out early if the bytes do not form a valid image.
    if image is None:
        raise ValueError(f"Failed to decode image: {src_path}")

    # Save the decoded image as JPG in the target folder.
    cv2.imwrite(dst_path, image)



# check if output dir exists, create if doesn't 
os.makedirs(output_dataset_path, exist_ok=True)

for i in range (1,3,1):
    path_to_traverse = f"/home/miko/diploma_thing/Datasets/ferret/colorferet/dvd{i}/data/images"
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
                    dst_filename = name.replace(".ppm.bz2", ".jpg")
                    dst_file = os.path.join(target_dir, dst_filename)

                    extract_bz2_to_jpg(src_file, dst_file)
                    