"""
youtube_upload.py — sube videos a YouTube Data API v3
"""
import os, sys, argparse
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = "client_secrets.json"
TOKEN_FILE = "token.json"

def get_credentials():
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
    return creds

def upload_video(video_path, title, description, tags, category_id="22", privacy="public"):
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description + "\n\n🔮 https://tarotgratis.online\n#tarot #lecturadetarot #tarotdiario",
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "es",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=4*1024*1024)
    print(f"📤 Subiendo: {title}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   {int(status.progress()*100)}%", end="\r")
    video_id = response["id"]
    print(f"\n✅ https://www.youtube.com/shorts/{video_id}")
    return video_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth", action="store_true")
    args = parser.parse_args()
    if args.auth:
        get_credentials()
        print(f"✅ Token guardado en {TOKEN_FILE}")
