"""
generate_video.py

Genera un video de tarot (YouTube Shorts 9:16).

Stack:
- Groq (Llama 3.3 70B) → guión y metadatos
- Google Cloud TTS      → voz en español de alta calidad
- Pexels API            → video de fondo luminoso y cálido
- MoviePy + PIL         → composición del video final

Estética: luminosa y cálida — fondos claros, texto oscuro sobre luz.
Paleta: crema #fdf8f0 | dorado #c9a84c | lavanda suave #9b7fd4 | tierra #8b5e3c
"""

import PIL.Image as _pil_img
if not hasattr(_pil_img, 'ANTIALIAS'):
    _pil_img.ANTIALIAS = _pil_img.LANCZOS

import os
import json
import random
from datetime import datetime
from pathlib import Path

import requests
import numpy as np
from groq import Groq
from google.cloud import texttospeech
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    ImageClip, ColorClip, concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────────
VIDEO_W = 1080
VIDEO_H = 1920
FPS     = 24
OUTPUT_DIR = Path("output_videos")
TEMP_DIR   = Path("temp")

# ── Paleta luminosa y cálida ───────────────────────────────────────────────────
# Fondos claros — sensación de luz, claridad, espiritualidad sin oscuridad
C_CREAM      = (253, 248, 240)  # #fdf8f0  — fondo crema cálido
C_CREAM_DARK = (240, 228, 210)  # #f0e4d2  — crema ligeramente más oscuro
C_GOLD       = (180, 130, 40)   # #b48228  — dorado más oscuro para contraste
C_GOLD_LIGHT = (220, 175, 80)   # #dcaf50  — dorado suave
C_LAVENDER   = (155, 127, 212)  # #9b7fd4  — lavanda suave
C_LAVENDER_L = (200, 180, 240)  # #c8b4f0  — lavanda muy claro
C_EARTH      = (139, 94, 60)    # #8b5e3c  — tierra cálida
C_TEXT_DARK  = (60, 40, 20)     # #3c2814  — texto oscuro sobre fondo claro
C_TEXT_MED   = (100, 70, 40)    # #644628  — texto medio
C_MUTED      = (150, 120, 90)   # #967858  — texto apagado

# Overlay muy suave (reemplaza el 0.55 oscuro anterior)
OVERLAY_OPACITY = 0.18   # Solo 18% — deja pasar la luz del fondo
OVERLAY_COLOR   = C_CREAM  # Tinte crema en vez de negro

ARCANOS = [
    "El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador",
    "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño",
    "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte",
    "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna",
    "El Sol", "El Juicio", "El Mundo",
]

CARD_GLYPHS = {
    "El Loco": "*", "El Mago": "+", "La Sacerdotisa": ")",
    "La Emperatriz": "~", "El Emperador": "#", "El Hierofante": "=",
    "Los Enamorados": "<3", "El Carro": ">", "La Fuerza": "8",
    "El Ermitaño": "|", "La Rueda de la Fortuna": "O", "La Justicia": "=",
    "El Colgado": "V", "La Muerte": "X", "La Templanza": "+",
    "El Diablo": "!", "La Torre": "^", "La Estrella": "*",
    "La Luna": "C", "El Sol": "o", "El Juicio": "!", "El Mundo": "@",
}

# Simbolos zodiacales en texto — sin emoji, universalmente compatibles
ZODIAC_SYMBOLS_TEXT = {
    "aries":       "( Aries )",
    "tauro":       "( Tauro )",
    "geminis":     "( Geminis )",
    "cancer":      "( Cancer )",
    "leo":         "( Leo )",
    "virgo":       "( Virgo )",
    "libra":       "( Libra )",
    "escorpio":    "( Escorpio )",
    "sagitario":   "( Sagitario )",
    "capricornio": "( Capricornio )",
    "acuario":     "( Acuario )",
    "piscis":      "( Piscis )",
}

ZODIAC_SIGNS = {
    "aries":       {"emoji": "", "nombre": "Aries"},
    "tauro":       {"emoji": "", "nombre": "Tauro"},
    "geminis":     {"emoji": "", "nombre": "Geminis"},
    "cancer":      {"emoji": "", "nombre": "Cancer"},
    "leo":         {"emoji": "", "nombre": "Leo"},
    "virgo":       {"emoji": "", "nombre": "Virgo"},
    "libra":       {"emoji": "", "nombre": "Libra"},
    "escorpio":    {"emoji": "", "nombre": "Escorpio"},
    "sagitario":   {"emoji": "", "nombre": "Sagitario"},
    "capricornio": {"emoji": "", "nombre": "Capricornio"},
    "acuario":     {"emoji": "", "nombre": "Acuario"},
    "piscis":      {"emoji": "", "nombre": "Piscis"},
}

# ── Queries Pexels — fondos luminosos y cálidos ────────────────────────────────
# Reemplaza las queries oscuras anteriores por escenas de luz y naturaleza
PEXELS_QUERIES_LIGHT = [
    "white clouds blue sky sunny day",
    "golden wheat field sunrise daytime",
    "white cherry blossom flowers sunlight",
    "green meadow sunny daytime nature",
    "beach waves sunny blue sky day",
    "mountain landscape sunny day bright",
    "lavender field purple flowers sunny",
    "sunrise over ocean golden light",
    "forest trees sunlight rays daytime",
    "white dandelion field bright sunlight",
]

# ── Fuentes ────────────────────────────────────────────────────────────────────
def _load_fonts(size_large, size_medium, size_small):
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
    ]
    reg_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
    ]
    def try_load(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()
    return (
        try_load(bold_candidates, size_large),
        try_load(bold_candidates, size_medium),
        try_load(reg_candidates,  size_small),
    )

# ── Carta del día ──────────────────────────────────────────────────────────────
def get_card_of_day(zodiac_key: str = None) -> str:
    hoy = datetime.now()
    if zodiac_key:
        # Carta diferente por signo: offset basado en el índice del signo
        sign_list = list(ZODIAC_SIGNS.keys())
        sign_idx  = sign_list.index(zodiac_key) if zodiac_key in sign_list else 0
        idx = (hoy.year + hoy.month + hoy.day + sign_idx * 3) % len(ARCANOS)
    else:
        idx = (hoy.year + hoy.month + hoy.day) % len(ARCANOS)
    return ARCANOS[idx]

# ── Guión con Groq ─────────────────────────────────────────────────────────────
def generate_reading(card: str, zodiac_key: str = None) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    hoy_str = datetime.now().strftime("%-d de %B de %Y")

    if zodiac_key and zodiac_key in ZODIAC_SIGNS:
        sign_info = ZODIAC_SIGNS[zodiac_key]
        sign_name = sign_info["nombre"]
        sign_emoji = sign_info["emoji"]

        prompt = f"""Eres la voz del Oráculo del Tarot Gratis. Generá contenido para un video de YouTube Shorts
de tarot para el signo {sign_name}, con la carta "{card}", para el {hoy_str}.

Responde ÚNICAMENTE con JSON válido (sin markdown, sin backticks, sin texto extra):
{{
  "title": "{sign_name.upper()} HOY | {card} | Tarot {hoy_str}",
  "script": "guión para leer en voz alta (180-220 palabras, en español rioplatense, místico y personal, sin símbolos como asteriscos, emojis o corchetes)",
  "description": "descripción del video para YouTube (150-200 chars, sin emojis)",
  "tags": ["tarot {sign_name.lower()}", "tarot hoy {sign_name.lower()}", "{sign_name.lower()} hoy", "tarot gratis", "{card.lower()}", "lectura de tarot", "oraculo", "tarot diario"]
}}

Reglas para el guión:
- Empezar con: "{sign_name}, hoy el universo te envía un mensaje a través de {card}."
- Explicar qué significa esta carta específicamente para {sign_name} hoy
- Dar un mensaje de guía concreto para amor, trabajo o energía del día
- Terminar con: "Para recibir tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online"
- Sonar natural al ser leído en voz alta
- Usar español rioplatense (vos, sentís, visitá)
- NO usar emojis ni símbolos especiales en ningún campo"""

    else:
        prompt = f"""Eres la voz del Oráculo del Tarot Gratis. Generá contenido para un video de YouTube Shorts
sobre la carta "{card}" para el {hoy_str}.

Responde ÚNICAMENTE con JSON válido (sin markdown, sin backticks, sin texto extra):
{{
  "title": "título llamativo para YouTube Shorts (máx 80 chars, incluye el nombre de la carta, sin emojis)",
  "script": "guión para leer en voz alta (180-220 palabras, en español rioplatense, místico y personal, sin símbolos como asteriscos, emojis o corchetes)",
  "description": "descripción del video para YouTube (150-200 chars, sin emojis)",
  "tags": ["tarot", "lectura de tarot", "arcanos mayores", "{card.lower()}", "tarot diario", "espiritualidad", "oraculo", "tarot gratis"]
}}

Reglas para el guión:
- Empezar con: "Hoy el universo te envía un mensaje a través de {card}."
- Explicar el significado espiritual de la carta (2-3 oraciones)
- Dar un mensaje de guía concreto para hoy
- Terminar con: "Para recibir tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online"
- Sonar natural al ser leído en voz alta
- Usar español rioplatense (vos, sentís, visitá)
- NO usar emojis ni símbolos especiales en ningún campo"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=700,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        glyph = CARD_GLYPHS.get(card, "✨")
        sign_label = f"{ZODIAC_SIGNS[zodiac_key]['nombre']} — " if zodiac_key else ""
        data = {
            "title": f"{glyph} {sign_label}{card} — Tu mensaje del universo hoy",
            "script": raw[:500],
            "description": f"Lectura de tarot: {card}. Descubrí tu mensaje del día 🔮",
            "tags": ["tarot", card.lower(), "tarot diario", "espiritualidad"],
        }
    return data

# ── Google Cloud TTS ───────────────────────────────────────────────────────────
def generate_voice(script: str, output_path: str) -> float:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script)
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-US",
        name=os.getenv("GOOGLE_TTS_VOICE", "es-US-Neural2-A"),
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.90,
        pitch=-1.0,
        volume_gain_db=1.0,
    )
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    Path(output_path).write_bytes(response.audio_content)
    print(f"  Audio guardado: {output_path}")
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    return duration

# ── Pexels — fondos luminosos ──────────────────────────────────────────────────
def download_pexels_video(output_path: str) -> bool:
    api_key = os.environ["PEXELS_API_KEY"]
    query   = random.choice(PEXELS_QUERIES_LIGHT)
    print(f"  Buscando video Pexels luminoso: '{query}'...")

    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 15, "size": "medium"},
        timeout=30,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    if not videos:
        # Fallback seguro: luz dorada
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": "sunny blue sky clouds daytime bright", "per_page": 10},
            timeout=30,
        )
        videos = resp.json().get("videos", [])

    if not videos:
        return False

    video  = random.choice(videos[:8])
    files  = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))
    chosen = next((f for f in reversed(files) if f.get("width", 9999) <= 1920), files[-1])

    print(f"  Descargando {chosen.get('width')}x{chosen.get('height')}...")
    with requests.get(chosen["link"], stream=True, timeout=90) as r:
        r.raise_for_status()
        with open(output_path, "wb") as out:
            for chunk in r.iter_content(chunk_size=65536):
                out.write(chunk)
    return True

# ── Overlays PIL — estética clara y luminosa ───────────────────────────────────

def _make_title_overlay(card_name: str, zodiac_key: str = None) -> np.ndarray:
    """
    Panel superior con fondo SOLIDO crema claro.
    No depende del video de fondo — siempre queda luminoso.
    El borde inferior hace fade hacia transparente para transicion suave.
    """
    w, h = VIDEO_W, 420

    # Base solida crema — completamente opaca
    img = Image.new("RGBA", (w, h), (*C_CREAM, 255))

    # Fade en los ultimos 90px hacia transparente
    fade_start = h - 90
    pixels = img.load()
    for y in range(fade_start, h):
        alpha = int(255 * (1 - (y - fade_start) / 90))
        for x_px in range(w):
            r_px, g_px, b_px, _ = pixels[x_px, y]
            pixels[x_px, y] = (r_px, g_px, b_px, alpha)

    draw = ImageDraw.Draw(img)
    font_big, font_med, font_sm = _load_fonts(80, 50, 34)

    GOLD_A    = (*C_GOLD, 255)
    TEXT_DARK = (*C_TEXT_DARK, 240)
    MUTED_A   = (*C_MUTED, 210)
    LAV_A     = (*C_LAVENDER, 230)
    line_margin = 80

    # Linea decorativa dorada superior
    draw.line([(line_margin, 28), (w - line_margin, 28)], fill=GOLD_A, width=2)

    if zodiac_key and zodiac_key in ZODIAC_SIGNS:
        sign = ZODIAC_SIGNS[zodiac_key]

        # Decorador texto del signo
        deco = ZODIAC_SYMBOLS_TEXT.get(zodiac_key, "")
        bbox = draw.textbbox((0, 0), deco, font=font_sm)
        draw.text(((w - (bbox[2]-bbox[0])) // 2, 44), deco, font=font_sm, fill=GOLD_A)

        # Nombre del signo — oscuro sobre crema claro
        sign_name = sign["nombre"].upper()
        bbox = draw.textbbox((0, 0), sign_name, font=font_big)
        tw = bbox[2] - bbox[0]
        x  = (w - tw) // 2
        draw.text((x + 2, 107), sign_name, font=font_big, fill=(180, 150, 120, 60))
        draw.text((x, 104), sign_name, font=font_big, fill=TEXT_DARK)

        # Separador
        sub = "- Tu carta de hoy -"
        bbox = draw.textbbox((0, 0), sub, font=font_sm)
        draw.text(((w - (bbox[2]-bbox[0])) // 2, 212), sub, font=font_sm, fill=MUTED_A)

        # Nombre de la carta — lavanda sobre crema
        bbox = draw.textbbox((0, 0), card_name, font=font_med)
        tw = bbox[2] - bbox[0]
        x  = (w - tw) // 2
        draw.text((x + 2, 260), card_name, font=font_med, fill=(180, 150, 120, 50))
        draw.text((x, 257), card_name, font=font_med, fill=LAV_A)

    else:
        sub = "- Tu carta del dia -"
        bbox = draw.textbbox((0, 0), sub, font=font_sm)
        draw.text(((w - (bbox[2]-bbox[0])) // 2, 48), sub, font=font_sm, fill=MUTED_A)

        bbox = draw.textbbox((0, 0), card_name, font=font_big)
        tw = bbox[2] - bbox[0]
        x  = (w - tw) // 2
        draw.text((x + 2, 142), card_name, font=font_big, fill=(180, 150, 120, 60))
        draw.text((x, 139), card_name, font=font_big, fill=TEXT_DARK)

    # Linea decorativa dorada inferior
    draw.line([(line_margin, 343), (w - line_margin, 343)], fill=GOLD_A, width=2)

    return np.array(img)


def _make_cta_overlay() -> np.ndarray:
    """
    Panel CTA inferior — fondo solido crema claro con borde dorado.
    Fade en el borde superior hacia transparente.
    """
    w, h = VIDEO_W, 220
    img  = Image.new("RGBA", (w, h), (*C_CREAM, 255))

    # Fade en los primeros 70px desde arriba: transparente -> solido
    pixels = img.load()
    for y in range(70):
        alpha = int(255 * (y / 70))
        for x_px in range(w):
            r_px, g_px, b_px, _ = pixels[x_px, y]
            pixels[x_px, y] = (r_px, g_px, b_px, alpha)

    draw = ImageDraw.Draw(img)
    font_big, font_med, font_sm = _load_fonts(56, 40, 30)

    GOLD_A    = (*C_GOLD, 255)
    TEXT_DARK = (*C_TEXT_DARK, 240)
    MUTED_A   = (*C_MUTED, 210)

    # Línea dorada superior
    draw.line([(80, 18), (w - 80, 18)], fill=GOLD_A, width=2)

    # "Lectura gratis y personalizada"
    line1 = "Lectura gratis y personalizada"
    bbox  = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w - (bbox[2]-bbox[0])) // 2, 38), line1, font=font_sm, fill=MUTED_A)

    # "tarotgratis.online" — grande y oscuro
    line2 = "tarotgratis.online"
    bbox  = draw.textbbox((0, 0), line2, font=font_big)
    x     = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x + 2, 108), line2, font=font_big, fill=(200, 200, 200, 80))  # sombra muy suave
    draw.text((x, 105), line2, font=font_big, fill=TEXT_DARK)

    return np.array(img)

# ── Composición del video ──────────────────────────────────────────────────────
def compose_video(
    bg_video_path: str,
    audio_path:    str,
    card_name:     str,
    output_path:   str,
    zodiac_key:    str = None,
) -> str:
    print("  Cargando audio...")
    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.5

    print("  Procesando video de fondo...")
    bg = VideoFileClip(bg_video_path, audio=False)

    if bg.duration < total_duration:
        loops = int(total_duration / bg.duration) + 2
        bg    = concatenate_videoclips([bg.copy() for _ in range(loops)])
    bg = bg.subclip(0, total_duration)

    # Escalar y recortar a 9:16
    bg_ratio     = bg.w / bg.h
    target_ratio = VIDEO_W / VIDEO_H
    if bg_ratio > target_ratio:
        bg = bg.resize(height=VIDEO_H)
        bg = bg.crop(x_center=bg.w / 2, width=VIDEO_W)
    else:
        bg = bg.resize(width=VIDEO_W)
        bg = bg.crop(y_center=bg.h / 2, height=VIDEO_H)

    # ── Overlay MUY SUAVE (solo 18% de opacidad, tinte crema) ──────────────────
    # Antes: ColorClip oscuro al 55% — hacía el video muy sombrío
    # Ahora: tinte crema al 18% — realza los colores cálidos sin oscurecer
    overlay = (
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(OVERLAY_COLOR))
        .set_opacity(OVERLAY_OPACITY)
        .set_duration(total_duration)
    )

    # Título — fade in a los 0.5s
    title_arr  = _make_title_overlay(card_name, zodiac_key)
    title_clip = (
        ImageClip(title_arr)
        .set_start(0.5)
        .set_duration(total_duration - 0.5)
        .set_position(("center", 80))
        .crossfadein(0.8)
    )

    # CTA — aparece en los últimos 8 segundos
    cta_arr   = _make_cta_overlay()
    cta_start = max(1.0, total_duration - 8)
    cta_clip  = (
        ImageClip(cta_arr)
        .set_start(cta_start)
        .set_duration(total_duration - cta_start)
        .set_position(("center", VIDEO_H - 290))
        .crossfadein(1.5)
    )

    print("  Componiendo y exportando (tarda ~3-4 min)...")
    TEMP_DIR.mkdir(exist_ok=True)

    final = CompositeVideoClip(
        [bg, overlay, title_clip, cta_clip],
        size=(VIDEO_W, VIDEO_H),
    ).set_audio(audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(TEMP_DIR / "tmp_audio.m4a"),
        remove_temp=True,
        threads=2,
        preset="ultrafast",
        verbose=False,
        logger=None,
    )

    for clip in [audio, bg, final]:
        try: clip.close()
        except Exception: pass

    return output_path

# ── Función principal ──────────────────────────────────────────────────────────
def generate(card: str = None, zodiac_key: str = None) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    card  = card or get_card_of_day(zodiac_key)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug  = card.lower().replace(" ", "_")

    sign_label = ""
    if zodiac_key and zodiac_key in ZODIAC_SIGNS:
        sign_label = f" [{ZODIAC_SIGNS[zodiac_key]['nombre']}]"

    print(f"\n🃏 Carta del día{sign_label}: {card}")
    print("─" * 52)

    # 1. Guión
    print("📝 Generando guión con Groq...")
    reading = generate_reading(card, zodiac_key)
    print(f"  Título: {reading['title']}")

    meta_path = TEMP_DIR / f"{stamp}_{slug}_meta.json"
    meta_path.write_text(json.dumps(reading, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Voz
    audio_path = str(TEMP_DIR / f"{stamp}_{slug}.mp3")
    print("🎙️ Generando voz con Google Cloud TTS...")
    duration = generate_voice(reading["script"], audio_path)
    print(f"  Duración: {duration:.1f}s")

    # 3. Video de fondo
    bg_path = str(TEMP_DIR / f"{stamp}_bg.mp4")
    print("🎬 Descargando video de fondo luminoso (Pexels)...")
    if not download_pexels_video(bg_path):
        raise RuntimeError("No se pudo descargar el video de fondo de Pexels.")

    # 4. Composición
    sign_suffix  = f"_{zodiac_key}" if zodiac_key else ""
    output_path  = str(OUTPUT_DIR / f"{stamp}_{slug}{sign_suffix}.mp4")
    print("🎞️ Componiendo video final...")
    compose_video(bg_path, audio_path, card, output_path, zodiac_key)

    print(f"\n✅ Video listo: {output_path}")
    return {
        "video_path":  output_path,
        "title":       reading["title"],
        "description": reading["description"],
        "tags":        reading["tags"],
        "card":        card,
        "zodiac_key":  zodiac_key,
        "duration_s":  duration,
    }
