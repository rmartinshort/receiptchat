import logging

import pandas as pd
from typing import List
import numpy as np
import os

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)


class ReceiptDataBaseHandler:

    DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "datasets", "receipt_database.csv"
    )
    # DATABASE_PATH = "receipt_database.csv"

    def __init__(self, load_database_on_init: bool = True) -> None:

        self.load_database_on_init = load_database_on_init
        if load_database_on_init:
            try:
                self._load_database()
            except Exception as e:
                logging.warning(e)
                self.database = None
                self.receipt_ids = None

    def _load_database(self) -> None:

        self.database = pd.read_csv(self.DATABASE_PATH)
        self.receipt_ids = set(self.database["receipt_id"].unique().tolist())

    def find_new_ids(self, available_files: List) -> List:

        if not self.receipt_ids:
            logging.warning("No parsed receipt ids! Does the database exist?")
            return available_files

        new_files = []
        for file in available_files:
            if file["id"] not in self.receipt_ids:
                new_files.append(file)

        return new_files

    def convert_json_to_pandas(self, loaded_json: List) -> pd.DataFrame:

        collected_df = {
            "vendor": [],
            "date": [],
            "address": [],
            "item_name": [],
            "item_cost": [],
            "receipt_id": [],
            "receipt_name": [],
            "receipt_type": [],
        }
        for v in loaded_json:

            items = v["items_purchased"]
            items += [
                {"item_name": "tax_rate", "item_cost": v["tax_rate"]},
                {"item_name": "total", "item_cost": v["subtotal"]},
                {"item_name": "subtotal", "item_cost": v["total_after_tax"]},
            ]
            for item in items:
                collected_df["vendor"].append(self.coerce_string(v["vendor_name"]))
                collected_df["date"].append(self.coerce_string(v["datetime"]))
                collected_df["address"].append(self.coerce_string(v["vendor_address"]))
                collected_df["receipt_id"].append(v["file_details"]["file_id"])
                collected_df["receipt_name"].append(
                    self.coerce_string(v["file_details"]["file_name"])
                )
                collected_df["receipt_type"].append(
                    self.coerce_string(v["file_details"]["file_type"])
                )
                collected_df["item_name"].append(self.coerce_string(item["item_name"]))
                collected_df["item_cost"].append(self.coerce_value(item["item_cost"]))

        collected_df = pd.DataFrame(collected_df)
        collected_df = collected_df.astype(str)
        collected_df["item_cost"] = collected_df["item_cost"].astype(float)
        collected_df["date"] = pd.to_datetime(
            collected_df["date"], format="mixed", errors="coerce"
        )
        return collected_df

    def update_database(self, collected_df: pd.DataFrame) -> pd.DataFrame:

        if isinstance(self.database, pd.DataFrame):
            return pd.concat([self.database, collected_df])
        else:
            return collected_df

    def write_to_database(self, collected_df: pd.DataFrame) -> None:

        collected_df.to_csv(self.DATABASE_PATH, index=False)
        return None

    @staticmethod
    def coerce_value(value):

        valid_value = ""
        for v in value:
            if (v == ".") or (v.isdigit()):
                valid_value += v

        try:
            return float(valid_value)
        except:
            return np.nan

    @staticmethod
    def coerce_string(value):

        if value == "N/A":
            return np.nan
        else:
            return str(value).strip()
