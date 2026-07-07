"""
generate_video.py
Genera videos de tarot por signo zodiacal (YouTube Shorts 9:16, 720p).

Stack:
  - Groq (Llama 3.3 70B)    → guión personalizado por signo
  - Google Cloud TTS         → voz en español Neural2
  - Pexels API               → fondo específico por carta
  - MoviePy + PIL            → composición 720x1280 (720p Shorts)

Estética: paleta de tarotgratis.online
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

# ── Resolución 720p (Shorts sigue siendo 9:16) ────────────────────────────────
VIDEO_W    = 720
VIDEO_H    = 1280
FPS        = 24
OUTPUT_DIR = Path("output_videos")
TEMP_DIR   = Path("temp")

# ── Paleta tarotgratis.online ─────────────────────────────────────────────────
C_BG_DEEP    = (30, 20, 59)
C_BG_MID     = (45, 30, 87)
C_GOLD       = (201, 168, 76)
C_GOLD_LIGHT = (240, 208, 128)
C_PURPLE     = (130, 43, 189)
C_PURPLE_L   = (182, 109, 248)
C_TEAL       = (15, 171, 162)
C_TEXT       = (253, 248, 240)
C_MUTED      = (160, 147, 176)

# ── Signos zodiacales ─────────────────────────────────────────────────────────
SIGNOS = [
    {"nombre": "Aries",       "emoji": "♈", "fechas": "21 mar – 19 abr"},
    {"nombre": "Tauro",       "emoji": "♉", "fechas": "20 abr – 20 may"},
    {"nombre": "Géminis",     "emoji": "♊", "fechas": "21 may – 20 jun"},
    {"nombre": "Cáncer",      "emoji": "♋", "fechas": "21 jun – 22 jul"},
    {"nombre": "Leo",         "emoji": "♌", "fechas": "23 jul – 22 ago"},
    {"nombre": "Virgo",       "emoji": "♍", "fechas": "23 ago – 22 sep"},
    {"nombre": "Libra",       "emoji": "♎", "fechas": "23 sep – 22 oct"},
    {"nombre": "Escorpio",    "emoji": "♏", "fechas": "23 oct – 21 nov"},
    {"nombre": "Sagitario",   "emoji": "♐", "fechas": "22 nov – 21 dic"},
    {"nombre": "Capricornio", "emoji": "♑", "fechas": "22 dic – 19 ene"},
    {"nombre": "Acuario",     "emoji": "♒", "fechas": "20 ene – 18 feb"},
    {"nombre": "Piscis",      "emoji": "♓", "fechas": "19 feb – 20 mar"},
]

# ── Arcanos mayores ───────────────────────────────────────────────────────────
ARCANOS = [
    "El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador",
    "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño",
    "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte",
    "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna",
    "El Sol", "El Juicio", "El Mundo",
]

CARD_GLYPHS = {
    "El Loco": "🎭", "El Mago": "⚡", "La Sacerdotisa": "🌙",
    "La Emperatriz": "🌿", "El Emperador": "👑", "El Hierofante": "🕊️",
    "Los Enamorados": "💫", "El Carro": "⚔️", "La Fuerza": "🦁",
    "El Ermitaño": "🕯️", "La Rueda de la Fortuna": "☸️", "La Justicia": "⚖️",
    "El Colgado": "💧", "La Muerte": "🌑", "La Templanza": "✨",
    "El Diablo": "🔥", "La Torre": "⚡", "La Estrella": "⭐",
    "La Luna": "🌙", "El Sol": "☀️", "El Juicio": "🎺", "El Mundo": "🌍",
}

# Pexels queries específicos por carta
CARD_PEXELS = {
    "El Loco":               ["adventure path nature", "freedom road", "leap cliff"],
    "El Mago":               ["mystical candle purple", "magic ritual dark", "crystal ball"],
    "La Sacerdotisa":        ["moon night purple", "mystery veil", "moonlight dark"],
    "La Emperatriz":         ["nature green abundance", "flowers garden", "earth goddess"],
    "El Emperador":          ["mountain peak", "stone throne", "power dark sky"],
    "El Hierofante":         ["ancient temple", "spiritual ceremony", "sacred candle"],
    "Los Enamorados":        ["couple sunset", "heart light bokeh", "love romance"],
    "El Carro":              ["road ahead night", "speed motion blur", "triumph victory"],
    "La Fuerza":             ["lion majestic", "strength nature", "powerful animal"],
    "El Ermitaño":           ["lantern night dark", "solitude path fog", "mystical forest"],
    "La Rueda de la Fortuna":["spinning stars galaxy", "cosmic wheel", "universe rotation"],
    "La Justicia":           ["scales balance", "law justice", "symmetry architecture"],
    "El Colgado":            ["water reflection", "hanging tree", "peaceful surrender"],
    "La Muerte":             ["autumn leaves falling", "transformation dark", "rebirth nature"],
    "La Templanza":          ["water pour light", "balance zen", "flowing river"],
    "El Diablo":             ["fire dark flames", "smoke dramatic", "red dark abstract"],
    "La Torre":              ["lightning storm dramatic", "tower dark", "storm clouds"],
    "La Estrella":           ["night sky stars", "galaxy milky way", "star field purple"],
    "La Luna":               ["full moon night", "moon reflection water", "lunar mystical"],
    "El Sol":                ["sunrise golden", "sunlight rays", "bright sun nature"],
    "El Juicio":             ["sunrise dramatic", "awakening light", "epic sky clouds"],
    "El Mundo":              ["earth globe space", "world complete", "universe harmony"],
}

DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background"]


# ── Carta del día para cada signo ─────────────────────────────────────────────
def get_card_for_sign(signo_idx: int) -> str:
    """Cada signo tiene su propia carta del día basada en fecha + índice."""
    hoy = datetime.now()
    idx = (hoy.year + hoy.month + hoy.day + signo_idx * 7) % len(ARCANOS)
    return ARCANOS[idx]


# ── Fuentes ───────────────────────────────────────────────────────────────────
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
        try_load(reg_candidates, size_small),
    )


# ── Guión con Groq ────────────────────────────────────────────────────────────
def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%-d de %B de %Y") if os.name != 'nt' else datetime.now().strftime("%d de %B de %Y")

    prompt = f"""Eres la voz del Oráculo del Tarot. Generá contenido para un YouTube Short de tarot para {signo['nombre']} con la carta "{card}".

Respondé ÚNICAMENTE con JSON válido (sin markdown, sin backticks):
{{
  "title": "{signo['nombre'].upper()} HOY {signo['emoji']} | {card} | Tarot {hoy}",
  "script": "guión de 160-180 palabras en español rioplatense, místico y personal",
  "description": "descripción YouTube 150-200 chars con emojis para {signo['nombre']}",
  "tags": ["tarot", "{signo['nombre'].lower()}", "tarot {signo['nombre'].lower()}", "horoscopo hoy", "lectura de tarot", "{card.lower()}", "tarot diario", "oráculo"]
}}

Reglas para el guión:
- Empezar con: "{signo['emoji']} {signo['nombre']}, hoy el universo te habla a través de {card}."
- Explicar qué significa esta carta específicamente para {signo['nombre']} (2 oraciones)
- Un mensaje de guía concreto para hoy
- Terminar con: "Para tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online"
- Sonar natural al ser leído en voz alta
- Usar vos, sentís, visitá (rioplatense)"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=600,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "title": f"{signo['nombre'].upper()} HOY {signo['emoji']} | {card} | Tarot {hoy}",
            "script": raw[:400],
            "description": f"Tarot de hoy para {signo['nombre']}: {card} 🔮",
            "tags": ["tarot", signo['nombre'].lower(), "tarot diario"],
        }
    return data


# ── Google Cloud TTS ──────────────────────────────────────────────────────────
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
        input=synthesis_input, voice=voice, audio_config=audio_config,
    )
    Path(output_path).write_bytes(response.audio_content)
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    return duration


# ── Pexels ────────────────────────────────────────────────────────────────────
def download_pexels_video(card: str, output_path: str) -> bool:
    api_key = os.environ["PEXELS_API_KEY"]
    queries = CARD_PEXELS.get(card, DEFAULT_QUERIES)
    query   = random.choice(queries)
    print(f"   Pexels: '{query}'...")

    for attempt_query in [query, "dark mystical purple", "night sky stars"]:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": attempt_query, "per_page": 10, "size": "medium"},
            timeout=30,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if videos:
            break

    if not videos:
        return False

    video  = random.choice(videos[:6])
    files  = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))
    chosen = next((f for f in reversed(files) if f.get("width", 9999) <= 1920), files[-1])

    with requests.get(chosen["link"], stream=True, timeout=90) as r:
        r.raise_for_status()
        with open(output_path, "wb") as out:
            for chunk in r.iter_content(chunk_size=65536):
                out.write(chunk)
    return True


# ── Overlays PIL ──────────────────────────────────────────────────────────────
def _make_title_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, 320
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg  = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(210 * max(0, 1 - y / h * 1.3))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(54, 32, 22)
    GOLD_A  = (*C_GOLD, 255)
    MUTED_A = (*C_MUTED, 200)

    margin = 50
    draw.line([(margin, 20), (w - margin, 20)], fill=GOLD_A, width=1)

    # Signo
    signo_text = f"{signo['emoji']}  {signo['nombre'].upper()}  {signo['emoji']}"
    bbox = draw.textbbox((0, 0), signo_text, font=font_big)
    draw.text(((w - (bbox[2]-bbox[0])) // 2, 34), signo_text, font=font_big, fill=GOLD_A)

    # "HOY"
    hoy_text = "✦  TAROT DE HOY  ✦"
    bbox = draw.textbbox((0, 0), hoy_text, font=font_sm)
    draw.text(((w - (bbox[2]-bbox[0])) // 2, 100), hoy_text, font=font_sm, fill=MUTED_A)

    # Carta
    glyph = CARD_GLYPHS.get(card, "🔮")
    card_text = f"{glyph}  {card}"
    bbox = draw.textbbox((0, 0), card_text, font=font_med)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x + 2, 138), card_text, font=font_med, fill=(0, 0, 0, 160))
    draw.text((x, 136), card_text, font=font_med, fill=GOLD_A)

    draw.line([(margin, 210), (w - margin, 210)], fill=GOLD_A, width=1)

    return np.array(img)


def _make_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 180
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg  = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(220 * (y / h))
        for x in range(w):
            bg.putpixel((x, y), (int(C_BG_DEEP[0]*.6), int(C_BG_DEEP[1]*.6), int(C_BG_MID[2]*.8), alpha))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(38, 28, 20)
    GOLD_A  = (*C_GOLD, 255)
    MUTED_A = (*C_MUTED, 200)

    # Línea dorada
    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0]-C_GOLD[0]) * (1 - abs(t*2-1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1]-C_GOLD[1]) * (1 - abs(t*2-1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2]-C_GOLD[2]) * (1 - abs(t*2-1)))
        draw.point((x, 12), fill=(r, g, b, 160))

    line1 = "🔮  Lectura gratis y personalizada"
    bbox  = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 28), line1, font=font_sm, fill=MUTED_A)

    line2 = "tarotgratis.online"
    bbox  = draw.textbbox((0, 0), line2, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+2, 72), line2, font=font_big, fill=(0,0,0,160))
    draw.text((x, 70), line2, font=font_big, fill=GOLD_A)

    return np.array(img)


def _make_mid_cta_overlay() -> np.ndarray:
    """CTA que aparece en el medio del video para llevar a la web."""
    w, h = VIDEO_W, 100
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg   = Image.new("RGBA", (w, h), (*C_BG_MID, 180))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(28, 22, 18)
    GOLD_A = (*C_GOLD, 255)

    text = "¿Qué significa para vos? → tarotgratis.online"
    bbox = draw.textbbox((0, 0), text, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 36), text, font=font_sm, fill=GOLD_A)

    return np.array(img)


# ── Composición del video ─────────────────────────────────────────────────────
def compose_video(bg_video_path, audio_path, signo, card, output_path):
    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.0

    bg = VideoFileClip(bg_video_path, audio=False)
    if bg.duration < total_duration:
        loops = int(total_duration / bg.duration) + 2
        bg = concatenate_videoclips([bg.copy() for _ in range(loops)])
    bg = bg.subclip(0, total_duration)

    # Escalar a 720x1280
    bg_ratio     = bg.w / bg.h
    target_ratio = VIDEO_W / VIDEO_H
    if bg_ratio > target_ratio:
        bg = bg.resize(height=VIDEO_H)
        bg = bg.crop(x_center=bg.w/2, width=VIDEO_W)
    else:
        bg = bg.resize(width=VIDEO_W)
        bg = bg.crop(y_center=bg.h/2, height=VIDEO_H)

    dark = (
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(C_BG_DEEP))
        .set_opacity(0.52)
        .set_duration(total_duration)
    )

    # Título arriba
    title_clip = (
        ImageClip(_make_title_overlay(signo, card))
        .set_start(0.4)
        .set_duration(total_duration - 0.4)
        .set_position(("center", 80))
        .crossfadein(0.7)
    )

    # CTA medio — aparece a mitad del video por 4 segundos
    mid_start = total_duration * 0.45
    mid_clip  = (
        ImageClip(_make_mid_cta_overlay())
        .set_start(mid_start)
        .set_duration(4.0)
        .set_position(("center", VIDEO_H // 2 - 50))
        .crossfadein(0.8)
        .crossfadeout(0.8)
    )

    # CTA final
    cta_start = max(1.0, total_duration - 7)
    cta_clip  = (
        ImageClip(_make_cta_overlay())
        .set_start(cta_start)
        .set_duration(total_duration - cta_start)
        .set_position(("center", VIDEO_H - 200))
        .crossfadein(1.0)
    )

    TEMP_DIR.mkdir(exist_ok=True)
    final = CompositeVideoClip(
        [bg, dark, title_clip, mid_clip, cta_clip],
        size=(VIDEO_W, VIDEO_H),
    ).set_audio(audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(TEMP_DIR / f"tmp_{Path(output_path).stem}.m4a"),
        remove_temp=True,
        threads=2,
        preset="ultrafast",
        verbose=False,
        logger=None,
    )
    for clip in [audio, bg, final]:
        try: clip.close()
        except: pass

    return output_path


# ── Función principal ─────────────────────────────────────────────────────────
def generate(signo_idx: int) -> dict:
    """Genera el video para un signo específico (0-11)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    signo = SIGNOS[signo_idx]
    card  = get_card_for_sign(signo_idx)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug  = f"{signo['nombre'].lower()}_{stamp}"

    print(f"\n{signo['emoji']}  {signo['nombre']} — {card}")
    print("─" * 48)

    print("📝  Generando guión...")
    reading = generate_reading(signo, card)
    print(f"    {reading['title']}")

    audio_path = str(TEMP_DIR / f"{slug}.mp3")
    print("🎙️   Generando voz...")
    duration = generate_voice(reading["script"], audio_path)
    print(f"    {duration:.1f}s")

    bg_path = str(TEMP_DIR / f"{slug}_bg.mp4")
    print("🎬  Descargando fondo Pexels...")
    if not download_pexels_video(card, bg_path):
        raise RuntimeError(f"No se pudo descargar fondo para {signo['nombre']}")

    output_path = str(OUTPUT_DIR / f"{slug}.mp4")
    print("🎞️   Componiendo video...")
    compose_video(bg_path, audio_path, signo, card, output_path)

    print(f"✅  {signo['nombre']} listo: {output_path}")

    return {
        "video_path": output_path,
        "title":      reading["title"],
        "description":reading["description"],
        "tags":       reading["tags"],
        "signo":      signo["nombre"],
        "card":       card,
        "duration_s": duration,
    }
