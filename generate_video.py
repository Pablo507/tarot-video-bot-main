"""
generate_video.py
Genera videos de tarot por signo zodiacal (YouTube Shorts / TikTok 9:16, 720p).
Optimizado con la URL visible desde el fotograma 0 para máxima conversión en perfil.

Stack:
  - Groq (openai/gpt-oss-120b) → guión personalizado y extendido por signo (con respaldo robusto)
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

# ── Resolución 720p (Shorts / TikTok 9:16) ────────────────────────────────────
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
    "La Ermitaño":           ["lantern night dark", "solitude path fog", "mystical forest"],
    "La Rueda de la Fortuna":["spinning stars galaxy", "cosmic wheel", "universe rotation"],
    "La Justicia":           ["scales balance", "law justice", "symmetry architecture"],
    "La Colgado":            ["water reflection", "hanging tree", "peaceful surrender"],
    "La Muerte":             ["autumn leaves falling", "transformation dark", "rebirth nature"],
    "La Templanza":          ["water pour light", "balance zen", "flowing river"],
    "El Diablo":             ["fire dark flames", "smoke dramatic", "red dark abstract"],
    "La Torre":              ["lightning storm dramatic", "tower dark", "storm clouds"],
    "La Estrella":           ["night sky stars", "galaxy milky way", "star field purple"],
    "La Luna":               ["full moon night", "moon reflection water", "lunar mystical"],
    "El Sol":                ["sunrise golden", "sunlight rays", "bright sun nature"],
    "La Juicio":             ["sunrise dramatic", "awakening light", "epic sky clouds"],
    "La Mundo":              ["earth globe space", "world complete", "universe harmony"],
}

DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background"]


def get_card_for_sign(signo_idx: int) -> str:
    hoy = datetime.now()
    idx = (hoy.year + hoy.month + hoy.day + signo_idx * 7) % len(ARCANOS)
    return ARCANOS[idx]


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


# ── Guión extendido con Groq (openai/gpt-oss-120b) y respaldo garantizado ──────
def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""Eres la voz del Oráculo del Tarot. Generá un guión extenso y detallado para un YouTube Short de tarot para {signo['nombre']} con la carta "{card}".

Devolvé UNICAMENTE un objeto JSON válido con estas claves exactas (sin bloques de código markdown, sin comillas invertidas extra):
{{
  "title": "{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
  "script": "Escribí un texto fluido de al menos 90 a 110 palabras en español. Hablá sobre el amor, la energía del día y un consejo profundo. Terminá estrictamente con la frase: Para tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online",
  "description": "Tarot de hoy para {signo['nombre']} 🔮",
  "tags": ["tarot", "{signo['nombre'].lower()}", "tarot diario"]
}}"""

    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=900,
    )
    raw = resp.choices[0].message.content.strip()
    print("Respuesta cruda de Groq:", raw[:200])
    
    clean_raw = raw.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(clean_raw)
    except json.JSONDecodeError:
        fallback_text = (
            f"Hola, {signo['nombre']}. Hoy la energía del arcano {card} se manifiesta con fuerza en tu vida. "
            "Es un momento de profunda introspección, donde tus emociones te piden escuchar tu intuición y dejar atrás las dudas del pasado. "
            "En el plano afectivo y personal, se abren puertas hacia nuevos comienzos si te permitís soltar el control y fluir con el universo. "
            "Recordá que cada obstáculo es una lección de crecimiento espiritual diseñada para tu evolución. "
            "Para tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online"
        )
        data = {
            "title": f"{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
            "script": fallback_text,
            "description": f"Tarot diario para {signo['nombre']} con {card} 🔮",
            "tags": ["tarot", signo['nombre'].lower(), "tarot diario"],
        }
    return data


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
        speaking_rate=0.90,  # Velocidad pausada y ceremonial
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
    print(f"Duración exacta del audio TTS: {duration} segundos")
    return duration


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


def _make_title_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, 390
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg  = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(210 * max(0, 1 - (y / h) * 1.0))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_sign, font_card, font_url = _load_fonts(50, 32, 42)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 240)
    MUTED_A = (*C_MUTED, 230)

    margin = 40
    draw.line([(margin, 16), (w - margin, 16)], fill=GOLD_A, width=2)

    signo_text = f"-- {signo['nombre'].upper()} --"
    bbox = draw.textbbox((0, 0), signo_text, font=font_sign)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+2, 28), signo_text, font=font_sign, fill=(0, 0, 0, 200))
    draw.text((x, 26), signo_text, font=font_sign, fill=GOLD_A)

    card_text = card.upper()
    bbox = draw.textbbox((0, 0), card_text, font=font_card)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+2, 92), card_text, font=font_card, fill=(0, 0, 0, 200))
    draw.text((x, 90), card_text, font=font_card, fill=WHITE_A)

    for xi in range(margin + 80, w - margin - 80):
        draw.point((xi, 138), fill=(*C_GOLD, 140))

    url_label = "Lectura gratis en:"
    font_sm = _load_fonts(24, 24, 22)[2]
    bbox = draw.textbbox((0, 0), url_label, font=font_sm)
    draw.text(((w - (bbox[2]-bbox[0])) // 2, 150), url_label, font=font_sm, fill=MUTED_A)

    url_text = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), url_text, font=font_url)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+3, 183), url_text, font=font_url, fill=(0, 0, 0, 240))
    draw.text((x, 180), url_text, font=font_url, fill=GOLD_A)

    for xi in range(margin, w - margin):
        t = (xi - margin) / (w - 2*margin)
        intensity = 1 - abs(t*2-1)
        ga = int(210 * intensity)
        draw.point((xi, 246), fill=(*C_GOLD, ga))
    draw.point((w//2, 246), fill=(*C_GOLD_LIGHT, 255))

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

    font_big, font_med, font_sm = _load_fonts(46, 30, 22)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 235)

    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0]-C_GOLD[0]) * (1 - abs(t*2-1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1]-C_GOLD[1]) * (1 - abs(t*2-1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2]-C_GOLD[2]) * (1 - abs(t*2-1)))
        draw.point((x, 12), fill=(r, g, b, 160))

    line1 = "Lectura gratis y personalizada"
    bbox  = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 28), line1, font=font_sm, fill=WHITE_A)

    line2 = "tarotgratis.online"
    bbox  = draw.textbbox((0, 0), line2, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+3, 80), line2, font=font_big, fill=(0, 0, 0, 230))
    draw.text((x, 77), line2, font=font_big, fill=GOLD_A)

    return np.array(img)


def _make_mid_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 170
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = min(210, 170 + int(40 * (y / h)))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(54, 32, 24)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 245)

    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0]-C_GOLD[0]) * (1 - abs(t*2-1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1]-C_GOLD[1]) * (1 - abs(t*2-1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2]-C_GOLD[2]) * (1 - abs(t*2-1)))
        draw.point((x, 2), fill=(r, g, b, 220))

    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0]-C_GOLD[0]) * (1 - abs(t*2-1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1]-C_GOLD[1]) * (1 - abs(t*2-1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2]-C_GOLD[2]) * (1 - abs(t*2-1)))
        draw.point((x, h-3), fill=(r, g, b, 220))

    l1 = "Lectura gratuita y personalizada:"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 18), l1, font=font_sm, fill=WHITE_A)

    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+3, 63), l2, font=font_big, fill=(0, 0, 0, 240))
    draw.text((x, 60), l2, font=font_big, fill=GOLD_A)

    return np.array(img)


def compose_video(bg_video_path, audio_path, signo, card, output_path):
    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.0

    bg = VideoFileClip(bg_video_path, audio=False)
    if bg.duration < total_duration:
        loops = int(total_duration / bg.duration) + 2
        bg = concatenate_videoclips([bg.copy() for _ in range(loops)])
    bg = bg.subclip(0, total_duration)

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
        .set_opacity(0.30)
        .set_duration(total_duration)
    )

    purple_tint = (
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(C_PURPLE))
        .set_opacity(0.18)
        .set_duration(total_duration)
    )

    title_clip = (
        ImageClip(_make_title_overlay(signo, card))
        .set_start(0.0)
        .set_duration(total_duration)
        .set_position(("center", 60))
    )

    mid_start = total_duration * 0.40
    mid_clip  = (
        ImageClip(_make_mid_cta_overlay())
        .set_start(mid_start)
        .set_duration(6.0)
        .set_position(("center", int(VIDEO_H * 0.58)))
        .crossfadein(0.8)
        .crossfadeout(0.8)
    )

    cta_start = max(1.0, total_duration - 7)
    cta_clip  = (
        ImageClip(_make_cta_overlay())
        .set_start(cta_start)
        .set_duration(total_duration - cta_start)
        .set_position(("center", int(VIDEO_H * 0.70)))
        .crossfadein(1.0)
    )

    TEMP_DIR.mkdir(exist_ok=True)
    final = CompositeVideoClip(
        [bg, dark, purple_tint, title_clip, mid_clip, cta_clip],
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


def generate(signo_idx: int) -> dict:
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
    print("🎞️   Componiendo video con URL visible desde el frame 0...")
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