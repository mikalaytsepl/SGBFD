import pandas 
import re

class CSVTester:
    def __init__ (self, csv_path:str):
        self.csv_path = csv_path
        self.df = pandas.read_csv(csv_path,
                                  header=0,
                                  delimiter=";")

test = CSVTester("/home/miko/diploma_thing/Datasets/VGGFace2_filtered_5/bohdan.csv")

print(test.df["UnifiedQualityScore.scalar"].iloc[0])