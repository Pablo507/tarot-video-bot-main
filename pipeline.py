"""
pipeline.py
Procesa un grupo de 3 signos zodiacales y los sube a YouTube.
Los videos se suben manualmente a TikTok después.

Uso:
  python pipeline.py --group 0   # Aries, Tauro, Géminis
  python pipeline.py --group 1   # Cáncer, Leo, Virgo
  python pipeline.py --group 2   # Libra, Escorpio, Sagitario
  python pipeline.py --group 3   # Capricornio, Acuario, Piscis
  python pipeline.py --group 0 --dry-run
  python pipeline.py --group 0 --cta paid
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

GROUPS = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [9, 10, 11],
]

SIGNOS_NOMBRES = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]


def main():
    parser = argparse.ArgumentParser(description="Tarot Video Bot — Grupo de signos")
    parser.add_argument("--group",   type=int, required=True, choices=[0, 1, 2, 3])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--cta",
        type=str,
        choices=["none", "free", "paid"],
        default="paid",
        help="Tipo de CTA: none, free, paid",
    )
    args = parser.parse_args()

    indices = GROUPS[args.group]
    nombres = [SIGNOS_NOMBRES[i] for i in indices]

    print("\n" + "=" * 54)
    print(f"  🔮  TAROT BOT — Grupo {args.group}: {', '.join(nombres)}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  CTA: {args.cta}")
    if args.dry_run:
        print("  Modo: DRY RUN")
    print("=" * 54)

    from generate_video import generate
    from youtube_upload import upload_video as yt_upload

    results = []
    errors = []
    guiones_previos = []

    for idx in indices:
        nombre = SIGNOS_NOMBRES[idx]
        try:
            result = generate(
                signo_idx=idx,
                cta_type=args.cta,
                prev_scripts=guiones_previos,
            )
            guiones_previos.append(result.get("script", ""))
            results.append(result)

            if not args.dry_run:
                video_id = yt_upload(
                    video_path=result["video_path"],
                    title=result["title"],
                    description=result["description"],
                    tags=result["tags"],
                    privacy="private" if args.private else "public",
                )
                result["video_id"] = video_id
                result["youtube_url"] = f"https://www.youtube.com/shorts/{video_id}"
                print(f"  📺 YouTube: https://www.youtube.com/shorts/{video_id}")
            else:
                print(f"  ✅ {nombre}: {result['video_path']} (dry-run)")

        except Exception as e:
            print(f"  ❌ Error en {nombre}: {e}")
            errors.append({"signo": nombre, "error": str(e)})

    summary = {
        "timestamp": datetime.now().isoformat(),
        "group":     args.group,
        "signos":    nombres,
        "cta_type":  args.cta,
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