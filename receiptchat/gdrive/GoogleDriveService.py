import os
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


class GoogleDriveService:

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        credential_path = os.path.join(base_path, "gdrive_credential.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path

    def build(self):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), self.SCOPES
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        return service
