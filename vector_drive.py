import io
import os
from functools import lru_cache

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials

from config import SETTINGS


SCOPES = ["https://www.googleapis.com/auth/drive"]


@lru_cache
def _get_drive_service():

    creds = Credentials.from_service_account_info(
        SETTINGS.google_service_account_json,
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def upload_vector(local_path: str, filename: str):

    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [SETTINGS.google_drive_vectors_folder_id]
    }

    media = MediaFileUpload(local_path, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return file.get("id")


def download_vector(filename: str, local_path: str):

    service = _get_drive_service()

    query = f"name='{filename}' and '{SETTINGS.google_drive_vectors_folder_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()

    files = results.get("files", [])

    if not files:
        raise FileNotFoundError(f"Drive 找不到 vector: {filename}")

    file_id = files[0]["id"]

    request = service.files().get_media(fileId=file_id)

    fh = io.FileIO(local_path, "wb")

    downloader = MediaIoBaseDownload(fh, request)

    done = False

    while not done:
        status, done = downloader.next_chunk()

    return local_path


def list_vectors():

    service = _get_drive_service()

    results = service.files().list(
        q=f"'{SETTINGS.google_drive_vectors_folder_id}' in parents",
        fields="files(id, name)"
    ).execute()

    return results.get("files", [])
