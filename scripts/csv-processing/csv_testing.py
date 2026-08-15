import json
import pandas as pd
import os
import shutil
import json

class OFIQEval:

    @staticmethod
    def _trim_filename_path(path: str) -> str:
        """Keep only dataset/identity/file from a longer relative path."""
        parts = [part for part in str(path).split("/") if part not in ("", ".")]
        if len(parts) >= 3:
            return "/".join(parts[-3:])
        return "/".join(parts)

    @staticmethod
    def _trim_dataset_name(filepath: str) -> str:
        # extracts the dataset name as it is always second from the start of the path, e.g. "./dataset-in/dataset_name/identity/file.jpg"
        parts = [part for part in str(filepath).split("/") if part not in ("", ".")]
        if len(parts) >= 2:
            return parts[1]
        else:
            ValueError(f"Invalid file path: {filepath}. Expected at least 2 segments in the path.")

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        # Read the raw OFIQ output
        self.df = pd.read_csv(csv_path, header=0, delimiter=";")

        # Extract the dataset name form the first file path in the CSV
        first_path = self.df["Filename"].iloc[0]
        self.dataset_name = self._trim_dataset_name(first_path)

        # 1. Extract the identity folder name using Regex from the Filename column
        # Looks for the directory segment right before the file name
        self.df["identity"] = self.df["Filename"].str.extract(r"/([^/]+)/[^/]+$")

        # 2. Compute the weighted Morph Score in-place
        self.df["morph_score"] = (
            0.50 * self.df["UnifiedQualityScore.scalar"]
            + 0.30 * self.df["HeadPoseYawFrontal.scalar"]
            + 0.20 * self.df["ExpressionNeutrality.scalar"]
        )

    def get_probes_for_identity(self, identity: str) -> pd.DataFrame:
        """Returns all probe records belonging to a single identity."""
        return self.df[self.df["identity"] == identity]

    def return_top_k(
        self, k: int = 3
    ) -> dict:
        self.k = k
        """Finds top K best images per identity and exports to a clean JSON structure."""
        # Sort entire dataset by identity and morph score descending
        sorted_df = self.df.sort_values(
            by=["identity", "morph_score"], ascending=[True, False]
        )

        # Grab top K rows for each identity group
        top_k_df = sorted_df.groupby("identity").head(k)

        # Structure as: { "00768": ["path/1.jpg", "path/2.jpg"], ... }
        result_dict = top_k_df.groupby("identity")["Filename"].apply(
            lambda series: [self._trim_filename_path(path) for path in series]
        ).to_dict()

        return result_dict

    def grab_subset(self, output_dataset_path:str, top_k_dict: dict, dataset_root:str):
        # derives top k images from identities in the dataset based on the returned top_k_dict and copies them to a new directory structure
        dest_path_name = f"{output_dataset_path}/{self.dataset_name}_top{self.k}"
        os.makedirs(dest_path_name, exist_ok=True) # create output for the dataset if haven't been done already
        for identity, filenames in top_k_dict.items():
            for filename in filenames:
                orig_path = os.path.join(dataset_root, filename)
                dest_path = os.path.join(dest_path_name, filename)

                # ensure nested destination dirs exist
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if not os.path.isfile(orig_path):
                    print(f"[WARN] Missing source: {orig_path}")
                    continue

                shutil.copy2(orig_path, dest_path)
                shutil.copy2(orig_path, dest_path)

test_eval = OFIQEval("/home/miko/diploma_thing/OFIQ/Docker/dataset-eval-out/filtered_dataset_ferret_3.csv")
filtering_result = test_eval.return_top_k(k=3)
test_eval.grab_subset("/home/miko/diploma_thing/OFIQ/Docker/dataset-eval-out", filtering_result, "/home/miko/diploma_thing/OFIQ/Docker/dataset-eval-in")