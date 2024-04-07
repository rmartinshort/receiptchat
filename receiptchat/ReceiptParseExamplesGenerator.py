from receiptchat.gdrive.GoogleDriveService import GoogleDriveService
from receiptchat.gdrive.GoogleDriveLoader import GoogleDriveLoader
from receiptchat.openai.VisionReceiptExtractor import VisionRecieptExtractor
import os
import json
from typing import List
import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)


class ReceiptParseExamplesGenerator:

    EXAMPLES_PATH = os.path.join(
        os.path.dirname(__file__), "datasets", "example_extractions.json"
    )

    def __init__(self, secrets: dict):

        self.gdrive_service = GoogleDriveService().build()
        self.gdrive_loader = GoogleDriveLoader(self.gdrive_service)
        self.vision_extractor = VisionRecieptExtractor(
            self.gdrive_loader, api_key=secrets["OPENAI_API_KEY"]
        )

        # load the examples
        if os.path.exists(self.EXAMPLES_PATH):
            with open(self.EXAMPLES_PATH) as f:
                loaded_examples = json.load(f)

            self.loaded_examples = loaded_examples
            self.loaded_example_ids = set(
                [x["file_details"]["file_id"] for x in self.loaded_examples]
            )
        else:
            self.loaded_examples = []
            self.loaded_example_ids = set([])

    def find_new_files(self):

        files = self.gdrive_loader.search_for_files()
        new_files = [x for x in files if x["id"] not in self.loaded_example_ids]
        return new_files

    def vision_parse_new_files(self, files: List) -> List:

        collected_data = []
        if not files:
            logging.info("No additional files available to add to examples!")
            return collected_data

        for file in files:
            logging.info("Vision parse file {}".format(file))
            result, cb = self.vision_extractor.parse(file)
            collected_data.append(result)

        return collected_data

    def update_examples(self, n_update=10):

        # choose just the first n new receipts as examples
        files_to_parse = self.find_new_files()[:n_update]
        logging.info(
            "Selected the following files as examples: {}".format(files_to_parse)
        )

        parsed_data = self.vision_parse_new_files(files_to_parse)
        updated_examples = self.loaded_examples + parsed_data

        logging.info("Updated examples: {}".format(updated_examples))

        with open(self.EXAMPLES_PATH, "w") as final:
            json.dump(updated_examples, final)
