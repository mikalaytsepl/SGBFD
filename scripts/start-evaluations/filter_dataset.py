import os
import shutil
import cv2

from frontal_detector import get_frontality


def filter_dataset(
    datapath: str,
    outputpath: str,
    threshold: int,
    quantity_per_identity: int,
    max_deviation: int
):
    identities = os.listdir(datapath)

    for identity in identities:
        identity_path = os.path.join(datapath, identity)

        if not os.path.isdir(identity_path):
            continue

        probes = os.listdir(identity_path)

        # skip identities with too few total images
        if len(probes) < threshold:
            continue

        frontal_candidates = []

        for probe in probes:
            img_path = os.path.join(identity_path, probe)

            img = cv2.imread(img_path)

            if img is None:
                print(f"Failed to load: {img_path}")
                continue

            result = get_frontality(img, max_deviation)

            if result is None:
                continue

            frontal_candidates.append({
                "file": probe,
                "score": result["score"],
                "yaw": result["yaw"],
                "pitch": result["pitch"],
                "roll": result["roll"]
            })

        # identity must have enough frontal images
        if len(frontal_candidates) < quantity_per_identity:
            continue

        # sort by best frontal score
        frontal_candidates.sort(key=lambda x: x["score"])

        # take top k best frontal images
        selected = frontal_candidates[:quantity_per_identity]

        # create output identity directory
        identity_dir = os.path.join(outputpath, identity)
        os.makedirs(identity_dir, exist_ok=True)

        for item in selected:
            src = os.path.join(identity_path, item["file"])
            dst = os.path.join(identity_dir, item["file"])

            shutil.copy2(src, dst)

        print(
            f"{identity}: selected {len(selected)} images "
            f"(best score: {selected[0]['score']:.2f})"
        )


filter_dataset(
    datapath="Datasets/HR_128_normalized/",
    outputpath="Datasets/HR_128_normalized_filtered_5/",
    threshold=5,
    quantity_per_identity=5,
    max_deviation=30
)