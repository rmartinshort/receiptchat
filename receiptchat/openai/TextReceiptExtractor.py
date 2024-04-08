import os
import json
from langchain_openai import ChatOpenAI
from receiptchat.openai.TextReceiptExtractionChain import TextReceiptExtractionChain
from receiptchat.data_transformations.FileBytesToImage import (
    JpegBytesToImage,
    PDFBytesToImage,
)
import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)


class TextReceiptExtractor:

    EXAMPLES_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "datasets",
        "example_extractions.json",
    )

    def __init__(
        self,
        gdrive_service,
        api_key: str,
        temperature: int = 0,
        model: str = "gpt-3.5-turbo",
    ) -> None:
        self.llm = ChatOpenAI(api_key=api_key, temperature=temperature, model=model)
        self.examples = self._load_examples()
        self.extractor = TextReceiptExtractionChain(self.llm, self.examples)
        self.input_parsers = {".jpeg": JpegBytesToImage(), ".pdf": PDFBytesToImage()}
        self.gdrive_service = gdrive_service

    def _load_examples(self):

        if not os.path.exists(self.EXAMPLES_PATH):
            logging.warning(
                "The examples file {} must exist in order to run TextReceiptExtractor".format(
                    self.EXAMPLES_PATH
                )
            )
            return []

        with open(self.EXAMPLES_PATH) as f:
            loaded_examples = json.load(f)

        loaded_examples = [
            {"input": x["file_details"]["extracted_text"], "output": x}
            for x in loaded_examples
        ]

        return loaded_examples

    def download_file_from_gdrive(self, file_details: dict) -> dict:
        name, extension = os.path.splitext(file_details["name"])
        downloaded_bytes = self.gdrive_service.download_file(file_details["id"])
        return {
            "filename": name,
            "bytes": downloaded_bytes,
            "extension": extension,
            "id": file_details["id"],
        }

    def prepare_data_for_llm(self, downloaded_data: dict) -> dict:
        converter = self.input_parsers[downloaded_data["extension"]]
        extracted_text = converter.convert_bytes_to_text(downloaded_data["bytes"])

        return {"extracted_text": extracted_text}

    def call_llm(self, prepared_data: dict) -> dict:
        res, cb = self.extractor.run_and_count_tokens(
            {"input": prepared_data["extracted_text"]}
        )

        return res, cb

    def parse(self, gdrive_file_details: dict) -> dict:
        file_data = self.download_file_from_gdrive(gdrive_file_details)
        image_data = self.prepare_data_for_llm(file_data)
        parsed_result, cb = self.call_llm(image_data)
        parsed_result = parsed_result.dict()

        parsed_result["file_details"] = {
            "file_name": file_data["filename"],
            "file_type": file_data["extension"],
            "file_id": file_data["id"],
            "extracted_text": image_data["extracted_text"],
        }
        return parsed_result, cb
