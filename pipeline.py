"""
pipeline.py
Procesa un grupo de 3 signos zodiacales y los sube a YouTube.

Uso:
  python pipeline.py --group 0   # signos 0,1,2  (Aries, Tauro, Géminis)
  python pipeline.py --group 1   # signos 3,4,5  (Cáncer, Leo, Virgo)
  python pipeline.py --group 2   # signos 6,7,8  (Libra, Escorpio, Sagitario)
  python pipeline.py --group 3   # signos 9,10,11 (Capricornio, Acuario, Piscis)
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
    parser.add_argument("--group",   type=int, required=True, choices=[0,1,2,3],
                        help="Grupo de signos a procesar (0-3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Genera los videos pero no los sube a YouTube")
    parser.add_argument("--private", action="store_true",
                        help="Subir como privado")
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
    from youtube_upload import upload_video

    results = []
    errors  = []

    for idx in indices:
        nombre = SIGNOS_NOMBRES[idx]
        try:
            result = generate(signo_idx=idx)
            results.append(result)

            if not args.dry_run:
                video_id = upload_video(
                    video_path=result["video_path"],
                    title=result["title"],
                    description=result["description"],
                    tags=result["tags"],
                    privacy="private" if args.private else "public",
                )
                result["video_id"]    = video_id
                result["youtube_url"] = f"https://www.youtube.com/shorts/{video_id}"
                print(f"  📤 {nombre}: https://www.youtube.com/shorts/{video_id}")
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
    summary_path = Path(f"output_videos/group_{args.group}_summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 54)
    print(f"  ✅ Completados: {len(results)} | ❌ Errores: {len(errors)}")
    print("=" * 54 + "\n")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
