"""
youtube_upload.py
Sube videos a YouTube usando la Data API v3.

Primera vez (local):
  python youtube_upload.py --auth
  → abre el browser, autorizás, se guarda token.json
"""

import os
import sys
import argparse
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES         = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = "client_secrets.json"
TOKEN_FILE     = "token.json"


def get_credentials() -> Credentials:
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("🔄 Refrescando token de YouTube...")
        creds.refresh(Request())
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        if not Path(CLIENT_SECRETS).exists():
            raise FileNotFoundError(
                "No se encontró client_secrets.json.\n"
                "Descargalo desde Google Cloud Console → APIs & Services → Credentials."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
        print(f"✅ Token guardado en {TOKEN_FILE}")

    return creds


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    category_id: str = "22",
    privacy: str = "public",
) -> str:
    print("🔐 Autenticando con YouTube...")
    creds   = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": (
                description + "\n\n"
                "🔮 Consultá tu tarot gratis en: https://tarotgratis.online\n\n"
                "#tarot #lecturadetarot #arcanosmayores #tarotdiario #espiritualidad #oraculogratuito"
            ),
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "es",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,
    )

    size_mb = Path(video_path).stat().st_size / 1024 / 1024
    print(f"📤 Subiendo: {title}")
    print(f"   Archivo: {video_path} ({size_mb:.1f} MB)")

    request  = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Progreso: {int(status.progress() * 100)}%", end="\r")

    video_id  = response["id"]
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"\n✅ Publicado: {video_url}")
    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth",    action="store_true", help="Solo autorizá y guardá el token")
    parser.add_argument("--file",    type=str)
    parser.add_argument("--title",   type=str, default="Lectura de tarot del día 🔮")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    if args.auth:
        get_credentials()
        print(f"\n✅ Autenticación completada.")
        print(f"   Copiá el contenido de '{TOKEN_FILE}' → GitHub Secret: YOUTUBE_TOKEN_JSON")
        print(f"   Copiá el contenido de '{CLIENT_SECRETS}' → GitHub Secret: YOUTUBE_CLIENT_SECRETS")
        sys.exit(0)

    if not args.file:
        parser.error("Necesitás --file si no usás --auth")

    upload_video(
        video_path=args.file,
        title=args.title,
        description="Tu carta del día",
        tags=["tarot", "lectura de tarot", "tarot diario"],
        privacy="private" if args.private else "public",
    )
