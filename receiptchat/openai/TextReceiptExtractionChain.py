import uuid
from typing import List, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.pydantic_v1 import BaseModel
from receiptchat.openai.prompts import TextReceiptExtractionPrompt
from receiptchat.openai.templates import ReceiptInformation, ReceiptItem
from langchain.callbacks import get_openai_callback


class Example(TypedDict):
    """A representation of an example consisting of text input and expected tool calls.

    For extraction, the tool calls are represented as instances of pydantic model.
    """

    input: str
    tool_calls: List[BaseModel]


class TextReceiptExtractionChain:

    def __init__(self, llm, examples):

        self.llm = llm
        self.raw_examples = examples
        self.prompt = TextReceiptExtractionPrompt()
        self.chain, self.examples = self.set_up_chain()

    @staticmethod
    def tool_example_to_messages(example: Example) -> List[BaseMessage]:
        """Convert an example into a list of messages that can be fed into an LLM.

        This code is an adapter that converts our example to a list of messages
        that can be fed into a chat model.

        The list of messages per example corresponds to:

        1) HumanMessage: contains the content from which content should be extracted.
        2) AIMessage: contains the extracted information from the model
        3) ToolMessage: contains confirmation to the model that the model requested a tool correctly.

        The ToolMessage is required because some of the chat models are hyper-optimized for agents
        rather than for an extraction use case.
        """
        messages: List[BaseMessage] = [HumanMessage(content=example["input"])]
        openai_tool_calls = []
        for tool_call in example["tool_calls"]:
            openai_tool_calls.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": "function",
                    "function": {
                        # The name of the function right now corresponds
                        # to the name of the pydantic model
                        # This is implicit in the API right now,
                        # and will be improved over time.
                        "name": tool_call.__class__.__name__,
                        "arguments": tool_call.json(),
                    },
                }
            )
        messages.append(
            AIMessage(content="", additional_kwargs={"tool_calls": openai_tool_calls})
        )
        tool_outputs = example.get("tool_outputs") or [
            "You have correctly called this tool."
        ] * len(openai_tool_calls)
        for output, tool_call in zip(tool_outputs, openai_tool_calls):
            messages.append(ToolMessage(content=output, tool_call_id=tool_call["id"]))
        return messages

    def set_up_examples(self):

        examples = [
            (
                example["input"],
                ReceiptInformation(
                    vendor_name=example["output"]["vendor_name"],
                    vendor_address=example["output"]["vendor_address"],
                    datetime=example["output"]["datetime"],
                    items_purchased=[
                        ReceiptItem(
                            item_name=example["output"]["items_purchased"][i][
                                "item_name"
                            ],
                            item_cost=example["output"]["items_purchased"][i][
                                "item_cost"
                            ],
                        )
                        for i in range(len(example["output"]["items_purchased"]))
                    ],
                    subtotal=example["output"]["subtotal"],
                    tax_rate=example["output"]["tax_rate"],
                    total_after_tax=example["output"]["total_after_tax"],
                ),
            )
            for example in self.raw_examples
        ]

        messages = []

        for text, tool_call in examples:
            messages.extend(
                self.tool_example_to_messages(
                    {"input": text, "tool_calls": [tool_call]}
                )
            )

        return messages

    def set_up_chain(self):

        extraction_model = self.llm
        prompt = self.prompt.prompt
        examples = self.set_up_examples()
        runnable = prompt | extraction_model.with_structured_output(
            schema=ReceiptInformation,
            method="function_calling",
            include_raw=False,
        )

        return runnable, examples

    def run_and_count_tokens(self, input_dict: dict):

        # add examples
        input_dict["examples"] = self.examples
        with get_openai_callback() as cb:
            result = self.chain.invoke(input_dict)

        return result, cb
