from langchain.chains import TransformChain
from langchain_core.messages import HumanMessage
from langchain_core.runnables import chain
from langchain_core.output_parsers import JsonOutputParser
import base64
from langchain.callbacks import get_openai_callback
from receiptchat.openai.prompts import VisionReceiptExtractionPrompt
from receiptchat.openai.templates import ReceiptInformation


class VisionReceiptExtractionChain:

    def __init__(self, llm):
        self.llm = llm
        self.chain = self.set_up_chain()

    @staticmethod
    def load_image(path: dict) -> dict:
        """Load image from file and encode it as base64."""

        def encode_image(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")

        image_base64 = encode_image(path["image_path"])
        return {"image": image_base64}

    def set_up_chain(self):
        extraction_model = self.llm
        prompt = VisionReceiptExtractionPrompt()
        parser = JsonOutputParser(pydantic_object=ReceiptInformation)

        load_image_chain = TransformChain(
            input_variables=["image_path"],
            output_variables=["image"],
            transform=self.load_image,
        )

        @chain
        def receipt_model_chain(inputs: dict) -> dict:
            """Invoke model with image and prompt."""
            msg = extraction_model.invoke(
                [
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt.template},
                            {"type": "text", "text": parser.get_format_instructions()},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{inputs['image']}"
                                },
                            },
                        ]
                    )
                ]
            )
            return msg.content

        return load_image_chain | receipt_model_chain | JsonOutputParser()

    def run_and_count_tokens(self, input_dict: dict):
        with get_openai_callback() as cb:
            result = self.chain.invoke(input_dict)

        return result, cb
