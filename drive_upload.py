"""
drive_upload.py
Sube el video generado a Google Drive usando el Service Account existente (tts_credentials.json).
No necesita credenciales extra — usa la misma cuenta que Google TTS.

Requisitos (ya en requirements.txt):
  google-api-python-client
  google-auth
"""

import os
import json
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

# ID de la carpeta de Google Drive donde se suben los videos
# Se configura como variable de entorno DRIVE_FOLDER_ID
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")


def get_drive_service():
    """Construye el servicio de Drive usando el Service Account de TTS."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts_credentials.json")

    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    return build("drive", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    metadata: dict = None,
) -> str:
    """
    Sube el video MP4 a Google Drive.
    También sube un .json con los metadatos (título, descripción, tags)
    para que Make.com pueda usarlos al publicar en TikTok.

    Retorna el ID del archivo en Drive.
    """
    if not DRIVE_FOLDER_ID:
        print("  ⚠️  DRIVE_FOLDER_ID no configurado — saltando subida a Drive")
        return ""

    service = get_drive_service()
    video_path = Path(video_path)

    print(f"  ☁️  Subiendo a Google Drive: {video_path.name}...")

    # ── 1. Subir el video MP4 ─────────────────────────────────────────────────
    file_metadata = {
        "name": video_path.name,
        "parents": [DRIVE_FOLDER_ID],
        "description": description,
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,
    )
    video_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()

    video_id = video_file.get("id")
    print(f"  ✅ Drive: {video_file.get('webViewLink')}")

    # ── 2. Subir JSON con metadatos para Make.com ─────────────────────────────
    # Make.com lee este JSON para obtener el título y descripción de TikTok
    meta_content = {
        "title": title,
        "description": description,
        "tags": metadata.get("tags", []) if metadata else [],
        "video_file_id": video_id,
        "video_file_name": video_path.name,
    }
    meta_name = video_path.stem + "_meta.json"
    meta_bytes = json.dumps(meta_content, ensure_ascii=False, indent=2).encode("utf-8")

    # Subir el JSON como archivo de texto
    import io
    meta_media = MediaFileUpload(
        io.BytesIO(meta_bytes),
        mimetype="application/json",
        resumable=False,
    )

    # Workaround: guardar en temp y subir
    temp_meta = Path("temp") / meta_name
    temp_meta.parent.mkdir(exist_ok=True)
    temp_meta.write_bytes(meta_bytes)

    meta_metadata = {
        "name": meta_name,
        "parents": [DRIVE_FOLDER_ID],
    }
    meta_media_file = MediaFileUpload(str(temp_meta), mimetype="application/json")
    service.files().create(
        body=meta_metadata,
        media_body=meta_media_file,
        fields="id",
    ).execute()

    return video_id
