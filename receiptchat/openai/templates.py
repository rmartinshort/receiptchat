from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List


class ReceiptItem(BaseModel):
    """Information about a single item on a receipt"""

    item_name: str = Field("The name of the purchased item")
    item_cost: str = Field("The cost of the item")


class ReceiptInformation(BaseModel):
    """Information extracted from a receipt"""

    vendor_name: str = Field(
        description="The name of the company who issued the reciept"
    )
    vendor_address: str = Field(
        description="The street address of the company who issued the reciept"
    )
    datetime: str = Field(
        description="The date and time that the receipt was printed in MM/DD/YY HH:MM format"
    )
    items_purchased: List[ReceiptItem] = Field(description="List of purchased items")
    subtotal: str = Field(description="The total cost before tax was applied")
    tax_rate: str = Field(description="The tax rate applied")
    total_after_tax: str = Field(description="The total cost after tax")
