from dataclasses import dataclass
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


@dataclass
class VisionReceiptExtractionPrompt:
    template: str = """
       You are an expert at information extraction from images of receipts.

       Given this of a receipt, extract the following information:
       - The name and address of the vendor
       - The names and costs of each of the items that were purchased
       - The date and time that the receipt was issued. This must be formatted like 'MM/DD/YY HH:MM'
       - The subtotal (i.e. the total cost before tax)
       - The tax rate
       - The total cost after tax

       Do not guess. If some information is missing just return "N/A" in the relevant field.
       If you determine that the image is not of a receipt, just set all the fields in the formatting instructions to "N/A". 
       
       You must obey the output format under all circumstances. Please follow the formatting instructions exactly.
       Do not return any additional comments or explanation. 
       """


@dataclass
class TextReceiptExtractionPrompt:
    system: str = """
       You are an expert at information extraction from images of receipts.

       Given this of a receipt, extract the following information:
       - The name and address of the vendor
       - The names and costs of each of the items that were purchased
       - The date and time that the receipt was issued. This must be formatted like 'MM/DD/YY HH:MM'
       - The subtotal (i.e. the total cost before tax)
       - The tax rate
       - The total cost after tax

       Do not guess. If some information is missing just return "N/A" in the relevant field.

       Please follow the formatting instructions exactly and do not return any additional comments or explanation
       """

    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system,
            ),
            MessagesPlaceholder("examples"),
            ("human", "{input}"),
        ]
    )
