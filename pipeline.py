"""
pipeline.py
Procesa un grupo de 3 signos zodiacales, los sube a YouTube y a Google Drive.
Make.com detecta los archivos en Drive y los publica en TikTok automáticamente.

Uso:
  python pipeline.py --group 0   # Aries, Tauro, Géminis
  python pipeline.py --group 1   # Cáncer, Leo, Virgo
  python pipeline.py --group 2   # Libra, Escorpio, Sagitario
  python pipeline.py --group 3   # Capricornio, Acuario, Piscis
  python pipeline.py --group 0 --dry-run   # solo genera, no sube
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

GROUPS = [
    [0, 1, 2],   # Aries, Tauro, Géminis
    [3, 4, 5],   # Cáncer, Leo, Virgo
    [6, 7, 8],   # Libra, Escorpio, Sagitario
    [9, 10, 11], # Capricornio, Acuario, Piscis
]

SIGNOS_NOMBRES = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]


def main():
    parser = argparse.ArgumentParser(description="Tarot Video Bot — Grupo de signos")
    parser.add_argument("--group",   type=int, required=True, choices=[0,1,2,3])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    indices = GROUPS[args.group]
    nombres = [SIGNOS_NOMBRES[i] for i in indices]

    print("\n" + "=" * 54)
    print(f"  🔮  TAROT BOT — Grupo {args.group}: {', '.join(nombres)}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("  Modo: DRY RUN")
    print("=" * 54)

    from generate_video import generate
    from youtube_upload import upload_video as yt_upload
    from drive_upload import upload_video as drive_upload
    import os

    use_drive = bool(os.getenv("DRIVE_FOLDER_ID", ""))

    results = []
    errors  = []

    for idx in indices:
        nombre = SIGNOS_NOMBRES[idx]
        try:
            result = generate(signo_idx=idx)
            results.append(result)

            if not args.dry_run:
                # ── Subir a YouTube ───────────────────────────────────────────
                video_id = yt_upload(
                    video_path=result["video_path"],
                    title=result["title"],
                    description=result["description"],
                    tags=result["tags"],
                    privacy="private" if args.private else "public",
                )
                result["video_id"]    = video_id
                result["youtube_url"] = f"https://www.youtube.com/shorts/{video_id}"
                print(f"  📺 YouTube: https://www.youtube.com/shorts/{video_id}")

                # ── Subir a Google Drive (para TikTok via Make.com) ───────────
                if use_drive:
                    drive_id = drive_upload(
                        video_path=result["video_path"],
                        title=result["title"],
                        description=result["description"],
                        metadata=result,
                    )
                    result["drive_id"] = drive_id
                    if drive_id:
                        print(f"  ☁️  Drive: {drive_id}")
                else:
                    print(f"  ⏭️  Drive: DRIVE_FOLDER_ID no configurado, saltando")

            else:
                print(f"  ✅ {nombre}: {result['video_path']} (dry-run)")

        except Exception as e:
            print(f"  ❌ Error en {nombre}: {e}")
            errors.append({"signo": nombre, "error": str(e)})

    # Guardar resumen
    summary = {
        "timestamp": datetime.now().isoformat(),
        "group":     args.group,
        "signos":    nombres,
        "results":   results,
        "errors":    errors,
    }
    Path("output_videos").mkdir(exist_ok=True)
    Path(f"output_videos/group_{args.group}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 54)
    print(f"  ✅ Completados: {len(results)} | ❌ Errores: {len(errors)}")
    print("=" * 54 + "\n")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

