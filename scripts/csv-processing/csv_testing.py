import json
import re
import pandas as pd


class OFIQEval:

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
        result_dict = (
            top_k_df.groupby("identity")["Filename"].apply(list).to_dict()
        )

        # Save to JSON for downstream scripts
        with open(output_json_path, "w") as f:
            json.dump(result_dict, f, indent=4)

        return result_dict

        