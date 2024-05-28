import os
from langchain_openai import ChatOpenAI
from receiptchat.openai.VisionReceiptExtractionChain import VisionReceiptExtractionChain
from receiptchat.data_transformations.FileBytesToImage import (
    JpegBytesToImage,
    PDFBytesToImage,
)
from tempfile import NamedTemporaryFile


class VisionRecieptExtractor:

    def __init__(
        self,
        gdrive_service,
        api_key: str,
        temperature: int = 0,
        model: str = "gpt-4-vision-preview",
    ) -> None:

        self.llm = ChatOpenAI(api_key=api_key, temperature=temperature, model=model)
        self.extractor = VisionReceiptExtractionChain(self.llm)
        self.input_parsers = {".jpeg": JpegBytesToImage(), ".pdf": PDFBytesToImage()}
        self.gdrive_service = gdrive_service

    def download_file_from_gdrive(self, file_details: dict) -> dict:

        name, extension = os.path.splitext(file_details["name"])
        downloaded_bytes = self.gdrive_service.download_file(file_details["id"])
        return {
            "filename": name,
            "bytes": downloaded_bytes,
            "extension": extension,
            "id": file_details["id"],
        }

    def prepare_data_for_llm(
        self, downloaded_data: dict, extract_raw_text: bool
    ) -> dict:

        converter = self.input_parsers[downloaded_data["extension"]]
        loaded_data = converter.convert_bytes_to_jpeg(downloaded_data["bytes"], dpi=50)
        if extract_raw_text:
            extracted_text = converter.convert_bytes_to_text(downloaded_data["bytes"])
        else:
            extracted_text = ""

        return {"image": loaded_data, "extracted_text": extracted_text}

    def call_llm(self, prepared_data: dict) -> tuple:

        with NamedTemporaryFile(suffix=".jpeg") as temp_file:
            prepared_data["image"].save(temp_file.name)
            res, cb = self.extractor.run_and_count_tokens(
                {"image_path": temp_file.name}
            )


        return res, cb

    def parse(self, gdrive_file_details: dict, extract_raw_text: bool = True) -> tuple:

        file_data = self.download_file_from_gdrive(gdrive_file_details)
        image_data = self.prepare_data_for_llm(file_data, extract_raw_text)
        parsed_result, cb = self.call_llm(image_data)

        parsed_result["file_details"] = {
            "file_name": file_data["filename"],
            "file_type": file_data["extension"],
            "file_id": file_data["id"],
            "extracted_text": image_data["extracted_text"],
        }
        return parsed_result, cb
