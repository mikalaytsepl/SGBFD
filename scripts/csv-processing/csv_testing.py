import json
import pandas as pd


class OFIQEval:

    @staticmethod
    def _trim_filename_path(path: str) -> str:
        """Keep only dataset/identity/file from a longer relative path."""
        parts = [part for part in str(path).split("/") if part not in ("", ".")]
        if len(parts) >= 3:
            return "/".join(parts[-3:])
        return "/".join(parts)

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        # Read the raw OFIQ output
        self.df = pd.read_csv(csv_path, header=0, delimiter=";")

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

    def export_top_k_json(
        self, output_json_path: str = "selected_probes.json", k: int = 3
    ) -> dict:
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

        # Save to JSON for downstream scripts
        with open(output_json_path, "w") as f:
            json.dump(result_dict, f, indent=4)

        return result_dict


test_eval = OFIQEval("/home/miko/diploma_thing/OFIQ/Docker/dataset-eval-out/filtered_dataset_ferret_3.csv")
test_eval.export_top_k_json(k=3, output_json_path="testing.json")