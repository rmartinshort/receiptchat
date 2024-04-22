from collections import defaultdict
import os
from typing import List
from PIL import ImageDraw
from receiptchat.data_transformations.FileBytesToImage import (
    PDFBytesToImage,
    JpegBytesToImage,
)
from receiptchat.openai.templates import ReceiptInformation, ReceiptItem


class TextractExtractor:
    """
    service = GoogleDriveService().build()
    loader = GoogleDriveLoader(service)
    session = boto3.Session()
    client = session.client('textract', region_name='us-west-2')
    textract_parser = TextractExtractor(client,loader)
    """

    LABEL_MAPPING = {
        "VENDOR_ADDRESS": "vendor_address",
        "VENDOR_NAME": "vendor_name",
        "TAX": "tax_rate",
        "TOTAL": "total_after_tax",
        "INVOICE_RECEIPT_DATE": "datetime",
    }

    def __init__(self, aws_client, gdrive_service):

        self.client = aws_client
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

    def process_expense_analysis(self, document_bytes, image=None) -> dict:

        # Analyze document
        # process using S3 object
        response = self.client.analyze_expense(Document={"Bytes": document_bytes})

        # show the extracted bounding boxes on the image
        if not isinstance(image, type(None)):
            plot_image = True
            width, height = image.size
            draw = ImageDraw.Draw(image)

            for expense_doc in response["ExpenseDocuments"]:

                # For draw bounding boxes
                for line_item_group in expense_doc["LineItemGroups"]:
                    for line_items in line_item_group["LineItems"]:
                        for expense_fields in line_items["LineItemExpenseFields"]:
                            for key, val in expense_fields["ValueDetection"].items():
                                if "Geometry" in key:
                                    self.draw_bounding_box(
                                        key, val, width, height, draw
                                    )

                for label in expense_doc["SummaryFields"]:
                    if "LabelDetection" in label:
                        for key, val in label["LabelDetection"].items():
                            self.draw_bounding_box(key, val, width, height, draw)

            # Display the image
            image.show()

        return response

    def prepare_data_for_model(
        self, downloaded_data: dict, extract_image: bool
    ) -> dict:
        converter = self.input_parsers[downloaded_data["extension"]]
        extracted_text = converter.convert_bytes_to_text(downloaded_data["bytes"])
        if extract_image:
            extracted_image = converter.convert_bytes_to_jpeg(downloaded_data["bytes"])
        else:
            extracted_image = None

        return {
            "extracted_text": extracted_text,
            "extracted_image": extracted_image,
            "bytes": downloaded_data["bytes"],
        }

    def call_textract(self, prepared_data: dict) -> dict:

        res = self.process_expense_analysis(
            document_bytes=prepared_data["bytes"],
            image=prepared_data["extracted_image"],
        )

        summaries = self.extract_summaries(res)
        items = self.extract_items(res)
        summaries["items_purchased"] = items
        summaries["subtotal"] = "N/A"
        summaries = ReceiptInformation(**summaries)

        return summaries

    def parse(self, gdrive_file_details: dict, extract_image: bool = True) -> tuple:
        file_data = self.download_file_from_gdrive(gdrive_file_details)
        image_data = self.prepare_data_for_model(file_data, extract_image=extract_image)
        parsed_result = self.call_textract(image_data)
        parsed_result = parsed_result.dict()

        parsed_result["file_details"] = {
            "file_name": file_data["filename"],
            "file_type": file_data["extension"],
            "file_id": file_data["id"],
            "extracted_text": image_data["extracted_text"],
        }
        return parsed_result

    def extract_summaries(self, result: dict) -> dict:

        # may be multiple entries per entity, could sort by confidence score
        summary_results = defaultdict(str)
        desired_summaries = set(self.LABEL_MAPPING.keys())
        confidences = {x: 0 for x in self.LABEL_MAPPING.keys()}
        summaries = result["ExpenseDocuments"][0]["SummaryFields"]
        for x in summaries:
            summary = x["Type"]["Text"]
            confidence = x["Type"]["Confidence"]
            if (
                (summary in desired_summaries)
                and (summary not in summary_results)
                and (confidence > confidences[summary])
            ):
                confidences[summary] = confidence
                summary_results[self.LABEL_MAPPING[summary]] = x["ValueDetection"][
                    "Text"
                ]

        for x in desired_summaries:
            if self.LABEL_MAPPING[x] not in summary_results:
                summary_results[self.LABEL_MAPPING[x]] = "N/A"

        return summary_results

    @staticmethod
    def extract_items(result: dict) -> List:

        items = []
        line_item_groups = result["ExpenseDocuments"][0]["LineItemGroups"]
        for line_item_group in line_item_groups:

            all_items_in_group = line_item_group["LineItems"]
            for line_item in all_items_in_group:

                item_expenses = line_item["LineItemExpenseFields"]

                item_name = "N/A"
                item_price = "N/A"

                for element in item_expenses:
                    if element["Type"]["Text"] == "ITEM":
                        item_name = element["ValueDetection"]["Text"]
                    elif element["Type"]["Text"] == "PRICE":
                        item_price = element["ValueDetection"]["Text"]

                item = {"item_name": item_name, "item_cost": item_price}
                items.append(ReceiptItem(**item))

        return items

    @staticmethod
    def draw_bounding_box(key, val, width, height, draw):
        # If a key is Geometry, draw the bounding box info in it
        if "Geometry" in key:
            # Draw bounding box information
            box = val["BoundingBox"]
            left = width * box["Left"]
            top = height * box["Top"]
            draw.rectangle(
                [
                    left,
                    top,
                    left + (width * box["Width"]),
                    top + (height * box["Height"]),
                ],
                outline="black",
            )

    @staticmethod
    def print_labels_and_values(field):
        # Only if labels are detected and returned
        if "LabelDetection" in field:
            print(
                "Summary Label Detection - Confidence: {}".format(
                    str(field.get("LabelDetection")["Confidence"])
                )
                + ", "
                + "Summary Values: {}".format(str(field.get("LabelDetection")["Text"]))
            )
            print(field.get("LabelDetection")["Geometry"])
        else:
            print("Label Detection - No labels returned.")
        if "ValueDetection" in field:
            print(
                "Summary Value Detection - Confidence: {}".format(
                    str(field.get("ValueDetection")["Confidence"])
                )
                + ", "
                + "Summary Values: {}".format(str(field.get("ValueDetection")["Text"]))
            )
            print(field.get("ValueDetection")["Geometry"])
        else:
            print("Value Detection - No values returned")
