"""
pipeline.py — Orquestador del bot de videos de tarot.

Uso:
  python pipeline.py                          → carta del día, sube a YouTube
  python pipeline.py --dry-run                → genera el video (no sube)
  python pipeline.py --card "La Luna"         → fuerza una carta específica
  python pipeline.py --private                → sube como privado
  python pipeline.py --zodiac aries           → genera video para Aries
  python pipeline.py --all-signs              → genera y sube los 12 signos
  python pipeline.py --all-signs --dry-run    → genera los 12 sin subir
"""

import argparse
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ZODIAC_KEYS = [
    "aries", "tauro", "geminis", "cancer", "leo", "virgo",
    "libra", "escorpio", "sagitario", "capricornio", "acuario", "piscis",
]

def run_single(card: str, zodiac_key: str, dry_run: bool, private: bool) -> dict:
    """Genera y opcionalmente sube un video. Devuelve el resumen."""
    from generate_video import generate

    result = generate(card=card, zodiac_key=zodiac_key)

    summary = {
        "timestamp":   datetime.now().isoformat(),
        "card":        result["card"],
        "zodiac_key":  zodiac_key,
        "title":       result["title"],
        "description": result["description"],
        "tags":        result["tags"],
        "duration_s":  result["duration_s"],
        "video_path":  result["video_path"],
        "uploaded":    False,
        "video_id":    None,
    }

    if dry_run:
        print(f"\n⏭️  Dry-run: saltando subida → {result['video_path']}")
    else:
        try:
            from youtube_upload import upload_video
            video_id = upload_video(
                video_path=result["video_path"],
                title=result["title"],
                description=result["description"],
                tags=result["tags"],
                privacy="private" if private else "public",
            )
            summary["uploaded"]     = True
            summary["video_id"]     = video_id
            summary["youtube_url"]  = f"https://www.youtube.com/shorts/{video_id}"
            print(f"  ✅ Publicado: {summary['youtube_url']}")
        except Exception as e:
            print(f"  ❌ Error subiendo: {e}")
            summary["upload_error"] = str(e)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Oráculo del Tarot — Video Bot")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Genera los videos pero NO los sube a YouTube")
    parser.add_argument("--card",      type=str, default=None,
                        help='Carta específica, ej: --card "La Luna"')
    parser.add_argument("--private",   action="store_true",
                        help="Subir como Privado en vez de Público")
    parser.add_argument("--zodiac",    type=str, default=None,
                        choices=ZODIAC_KEYS,
                        help="Signo zodiacal, ej: --zodiac aries")
    parser.add_argument("--all-signs", action="store_true",
                        help="Genera y sube un video para cada uno de los 12 signos")
    args = parser.parse_args()

    print("\n" + "=" * 56)
    print("  🔮 ORÁCULO DEL TAROT — VIDEO BOT")
    print("  tarotgratis.online")
    print("=" * 56)
    if args.dry_run:
        print("  Modo: DRY RUN (no se sube nada)")
    if args.all_signs:
        print("  Modo: 12 SIGNOS (un video por signo)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 56)

    Path("output_videos").mkdir(exist_ok=True)
    summaries = []

    # ── Modo 12 signos ─────────────────────────────────────────────────────────
    if args.all_signs:
        for i, zodiac_key in enumerate(ZODIAC_KEYS):
            print(f"\n[{i+1}/12] Generando video para {zodiac_key.upper()}...")
            try:
                s = run_single(
                    card=args.card,
                    zodiac_key=zodiac_key,
                    dry_run=args.dry_run,
                    private=args.private,
                )
                summaries.append(s)
            except Exception as e:
                print(f"  ❌ Error con {zodiac_key}: {e}")
                summaries.append({
                    "zodiac_key": zodiac_key,
                    "error": str(e),
                    "uploaded": False,
                })

            # Pausa de 8 segundos entre videos para no saturar las APIs
            if i < len(ZODIAC_KEYS) - 1:
                print("  ⏳ Pausa 8s antes del siguiente signo...")
                time.sleep(8)

        # Resumen final
        ok      = sum(1 for s in summaries if s.get("uploaded") or args.dry_run)
        failed  = len(summaries) - ok
        print("\n" + "=" * 56)
        print(f"  ✅ Completados: {ok}/12")
        if failed:
            print(f"  ⚠️  Fallidos:    {failed}/12")
        print("=" * 56 + "\n")

    # ── Modo signo único o carta del día ───────────────────────────────────────
    else:
        try:
            s = run_single(
                card=args.card,
                zodiac_key=args.zodiac,
                dry_run=args.dry_run,
                private=args.private,
            )
            summaries.append(s)
        except Exception as e:
            print(f"\n❌ Error generando el video: {e}")
            raise

        print("\n" + "=" * 56)
        if s.get("uploaded"):
            print(f"  ✅ Publicado: {s['youtube_url']}")
        elif args.dry_run:
            print(f"  ✅ Video generado: {s['video_path']}")
        else:
            print("  ⚠️  Video generado pero no se pudo subir")
        print("=" * 56 + "\n")

    # ── Guardar resumen ────────────────────────────────────────────────────────
    summary_path = Path("output_videos/last_run.json")
    summary_path.write_text(
        json.dumps(summaries if args.all_signs else summaries[0],
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Exit code 1 solo si ningún video se subió (y no es dry-run)
    if not args.dry_run and not args.all_signs:
        if not summaries[0].get("uploaded"):
            sys.exit(1)


if __name__ == "__main__":
    main()
