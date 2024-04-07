from dotenv import load_dotenv
import os
from receiptchat.ReceiptParseDriver import ReceiptParseDriver
from receiptchat.ReceiptParseExamplesGenerator import ReceiptParseExamplesGenerator


def load_secrets(env_path=".env"):
    # both calls are needed here
    load_dotenv()
    load_dotenv(dotenv_path=env_path)

    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }


def main():

    secrets = load_secrets()
    parser = ReceiptParseDriver(secrets, load_database_on_init=True)
    parser.update_database(model="text", write_to_db=True)


def main_generate_examples(n_examples=10):

    secrets = load_secrets()
    parser = ReceiptParseExamplesGenerator(secrets)
    parser.update_examples(n_update=n_examples)
