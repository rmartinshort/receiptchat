import pandas as pd

from receiptchat.gdrive.GoogleDriveService import GoogleDriveService
from receiptchat.gdrive.GoogleDriveLoader import GoogleDriveLoader
from receiptchat.openai.TextReceiptExtractor import TextReceiptExtractor
from receiptchat.openai.VisionReceiptExtractor import VisionRecieptExtractor
from receiptchat.data_transformations.ReceiptDatabaseHandler import (
    ReceiptDataBaseHandler,
)
from typing import List


class ReceiptParseDriver:

    def __init__(self, secrets: dict, load_database_on_init: bool =True):

        self.gdrive_service = GoogleDriveService().build()
        self.gdrive_loader = GoogleDriveLoader(self.gdrive_service)
        self.vision_extractor = VisionRecieptExtractor(
            self.gdrive_loader, api_key=secrets["OPENAI_API_KEY"]
        )
        self.text_extractor = TextReceiptExtractor(
            self.gdrive_loader, api_key=secrets["OPENAI_API_KEY"]
        )
        self.database_handler = ReceiptDataBaseHandler(
            load_database_on_init=load_database_on_init
        )

    def find_new_files(self):

        files = self.gdrive_loader.search_for_files()
        new_files = self.database_handler.find_new_ids(files)
        return new_files

    def text_parse_new_files(self, files: List) -> List:

        collected_data = []
        for file in files:
            result, cb = self.text_extractor.parse(file)
            collected_data.append(result)

        return collected_data

    def vision_parse_new_files(self, files: List) -> List:

        collected_data = []
        for file in files:
            result, cb = self.vision_extractor.parse(file)
            collected_data.append(result)

        return collected_data

    def json_to_pd(self, collected_data: List) -> pd.DataFrame:

        new_pd = self.database_handler.convert_json_to_pandas(collected_data)
        return new_pd

    def update_database(self, model="text", write_to_db=False):

        files_to_parse = self.find_new_files()

        if model == "text":
            parsed_data = self.text_parse_new_files(files_to_parse)
        elif model == "vision":
            parsed_data = self.vision_parse_new_files(files_to_parse)
        else:
            raise ValueError("model must be text or vision")

        new_pdf = self.json_to_pd(parsed_data)
        updated_pdf = self.database_handler.update_database(new_pdf)

        if write_to_db:
            self.database_handler.write_to_database(updated_pdf)
        return updated_pdf
