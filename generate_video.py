"""
generate_video.py
v7.0 - Premium: Carta protagonista, lectura profunda, cero spam visual.
"""

import PIL.Image as _pil_img
if not hasattr(_pil_img, 'ANTIALIAS'):
    _pil_img.ANTIALIAS = _pil_img.LANCZOS

import os
import json
import random
import hashlib
import time
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

VIDEO_W    = 720
VIDEO_H    = 1280
FPS        = 24
OUTPUT_DIR = Path("output_videos")
TEMP_DIR   = Path("temp")

C_BG_DEEP    = (30, 20, 59)
C_BG_MID     = (45, 30, 87)
C_GOLD       = (201, 168, 76)
C_GOLD_LIGHT = (240, 208, 128)
C_TEXT       = (253, 248, 240)
C_MUTED      = (160, 147, 176)

PALETAS_TINT = [
    {"nombre": "purple", "color": (130, 43, 189), "opacity": 0.25},
    {"nombre": "blue",   "color": (15, 40, 100),  "opacity": 0.30},
    {"nombre": "wine",   "color": (90, 20, 60),   "opacity": 0.25},
]

TAROT_MEANINGS = {
    "El Loco": "nuevos comienzos, dar un salto de fe, libertad, espontaneidad",
    "El Mago": "poder personal, manifestación, habilidades, acción",
    "La Sacerdotisa": "intuición, secretos, sabiduría interior, paciencia",
    "La Emperatriz": "abundancia, creatividad, fertilidad, cuidado",
    "El Emperador": "estructura, autoridad, control, estabilidad",
    "El Hierofante": "tradición, guía espiritual, reglas, aprendizaje",
    "Los Enamorados": "relaciones, elecciones, alineación de valores, amor",
    "El Carro": "voluntad, determinación, victoria, control del destino",
    "La Fuerza": "coraje interior, compasión, paciencia, control de impulsos",
    "El Ermitaño": "introspección, soledad, buscar la verdad, guía interior",
    "La Rueda de la Fortuna": "cambios, ciclos, destino, giros inesperados",
    "La Justicia": "verdad, causa y efecto, equilibrio, decisiones justas",
    "El Colgado": "pausa, rendición, dejar ir, nueva perspectiva",
    "La Muerte": "transformación profunda, finales, renacimiento",
    "La Templanza": "equilibrio, moderación, sanación, paciencia",
    "El Diablo": "tentación, ataduras, sombra, deseo material",
    "La Torre": "ruptura, caos, revelación, reconstrucción",
    "La Estrella": "esperanza, inspiración, sanación, fe en el futuro",
    "La Luna": "ilusión, miedo, subconsciente, confusión",
    "El Sol": "éxito, alegría, vitalidad, claridad",
    "El Juicio": "despertar, juicio, renacimiento, perdón",
    "El Mundo": "culminación, éxito, logros, plenitud",
}

# Solo un CTA sutil al final
CTA_FINAL = "Si querés saber qué te depara el destino, entrá ahora a tarotgratis.online y sacá tu carta gratis."

SIGN_CARD_OFFSETS = [0, 7, 14, 3, 10, 17, 4, 11, 18, 5, 12, 19]

SIGNOS = [
    {"nombre": "Aries", "emoji": "♈", "elemento": "Fuego", "tono": "impulsivo, directo", "temas": ["acción inmediata", "liderazgo", "coraje", "paciencia"]},
    {"nombre": "Tauro", "emoji": "♉", "elemento": "Tierra", "tono": "sensual, estable", "temas": ["seguridad material", "placeres simples", "constancia", "soltar"]},
    {"nombre": "Géminis", "emoji": "♊", "elemento": "Aire", "tono": "curioso, disperso", "temas": ["comunicación", "aprendizaje", "decisiones", "elegir"]},
    {"nombre": "Cáncer", "emoji": "♋", "elemento": "Agua", "tono": "emocional, protector", "temas": ["familia", "hogar", "sanar", "límites"]},
    {"nombre": "Leo", "emoji": "♌", "elemento": "Fuego", "tono": "dramático, orgulloso", "temas": ["brillar", "creatividad", "reconocimiento", "humildad"]},
    {"nombre": "Virgo", "emoji": "♍", "elemento": "Tierra", "tono": "analítico, servicial", "temas": ["orden", "salud", "servicio", "soltar perfeccionismo"]},
    {"nombre": "Libra", "emoji": "♎", "elemento": "Aire", "tono": "diplomático, indeciso", "temas": ["relaciones", "belleza", "equilibrio", "decidir"]},
    {"nombre": "Escorpio", "emoji": "♏", "elemento": "Agua", "tono": "intenso, reservado", "temas": ["transformación", "poder personal", "celos", "confiar"]},
    {"nombre": "Sagitario", "emoji": "♐", "elemento": "Fuego", "tono": "aventurero, exagerado", "temas": ["expansión", "viajes", "fe", "compromiso"]},
    {"nombre": "Capricornio", "emoji": "♑", "elemento": "Tierra", "tono": "disciplinado, frío", "temas": ["metas", "responsabilidad", "trabajo", "disfrutar"]},
    {"nombre": "Acuario", "emoji": "♒", "elemento": "Aire", "tono": "rebelde, distante", "temas": ["libertad", "innovación", "amistades", "emociones"]},
    {"nombre": "Piscis", "emoji": "♓", "elemento": "Agua", "tono": "soñador, evasivo", "temas": ["intuición", "arte", "espiritualidad", "límites"]},
]

ARCANOS = ["El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador", "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño", "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte", "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna", "El Sol", "El Juicio", "El Mundo"]
CARD_PEXELS = {"El Loco": ["adventure path", "freedom road"], "El Mago": ["candle purple", "magic ritual"], "La Sacerdotisa": ["moon night", "mystery veil"], "La Emperatriz": ["nature abundance", "flowers"], "El Emperador": ["mountain peak", "stone throne"], "El Hierofante": ["ancient temple", "sacred candle"], "Los Enamorados": ["couple sunset", "love romance"], "El Carro": ["road night", "speed motion"], "La Fuerza": ["lion majestic", "powerful animal"], "La Ermitaño": ["lantern dark", "solitude path"], "La Rueda de la Fortuna": ["spinning stars", "cosmic wheel"], "La Justicia": ["scales balance", "symmetry architecture"], "La Colgado": ["water reflection", "hanging tree"], "La Muerte": ["autumn leaves", "transformation dark"], "La Templanza": ["water pour", "balance zen"], "El Diablo": ["dark flames", "smoke dramatic"], "La Torre": ["lightning storm", "tower dark"], "La Estrella": ["night sky stars", "galaxy milky"], "La Luna": ["full moon", "moon reflection"], "El Sol": ["sunrise golden", "sunlight rays"], "La Juicio": ["sunrise dramatic", "awakening light"], "La Mundo": ["earth globe", "universe harmony"]}
DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background"]
VOCES_POR_ELEMENTO = {"Fuego": "es-US-Neural2-A", "Tierra": "es-US-Neural2-A", "Aire": "es-US-Journey-F", "Agua": "es-US-Neural2-A"}
VOCES_SIN_PITCH = {"es-US-Journey-F", "es-US-Journey-D", "es-US-Journey-O"}
_BOLD_FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"]

def get_card_for_sign(signo_idx: int) -> str:
    hoy = datetime.now()
    day_offset = (hoy.year * 31 + hoy.month * 17 + hoy.day) % len(ARCANOS)
    idx = (day_offset + SIGN_CARD_OFFSETS[signo_idx]) % len(ARCANOS)
    return ARCANOS[idx]

def _load_fonts(size_large, size_medium, size_small):
    reg_candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "C:/Windows/Fonts/georgia.ttf"]
    def try_load(paths, size):
        for p in paths:
            try: return ImageFont.truetype(p, size)
            except: continue
        return ImageFont.load_default()
    return (try_load(_BOLD_FONT_PATHS, size_large), try_load(_BOLD_FONT_PATHS, size_medium), try_load(reg_candidates, size_small))

def _fit_font_to_width(text: str, max_width: int, initial_size: int, min_size: int = 36):
    size = initial_size
    while size > min_size:
        font = None
        for p in _BOLD_FONT_PATHS:
            try: font = ImageFont.truetype(p, size); break
            except: continue
        if font is None: return ImageFont.load_default()
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width: return font
        size -= 2
    return ImageFont.truetype(_BOLD_FONT_PATHS[0], min_size) if os.path.exists(_BOLD_FONT_PATHS[0]) else ImageFont.load_default()

def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")
    significado_carta = TAROT_MEANINGS.get(card, "transformación y crecimiento")
    temas = ", ".join(signo["temas"])
    
    prompt = f"""Eres un tarotista experto. Escribí una lectura profunda para {signo['nombre']} con la carta "{card}".
Significado: {significado_carta}.
AUDIENCIA: 45-64 años, LATAM. Tono directo y sabio.
Mencioná: {temas}.
REGLAS: Mínimo 80 palabras, máximo 95. NO uses clichés. Enfocate en explicar el mensaje de la carta.

JSON:
{{"title": "{signo['nombre'].upper()} HOY | {card}", "lectura": "texto aquí", "description": "Tarot de hoy para {signo['nombre']}."}}"""

    data = None
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}], temperature=0.8, max_tokens=400,
            )
            raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            if len(parsed.get("lectura", "").split()) >= 60:
                data = parsed
                break
        except: time.sleep(2)

    if not data:
        data = {"title": f"{signo['nombre'].upper()} HOY | {card}", "lectura": f"{signo['nombre']}, la energía de {card} te invita a reflexionar sobre {significado_carta}. Es un momento clave para tomar decisiones con el corazón.", "description": "Tarot"}

    data["script"] = f"{data['lectura']} {CTA_FINAL}"
    data["tags"] = ["tarot", signo['nombre'].lower(), "tarot gratis", "horoscopo"]
    return data

def generate_voice(script: str, output_path: str, elemento: str = "Fuego") -> float:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script)
    voice_name = os.getenv("GOOGLE_TTS_VOICE", VOCES_POR_ELEMENTO.get(elemento, "es-US-Neural2-A"))
    voice = texttospeech.VoiceSelectionParams(language_code="es-US", name=voice_name, ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.95, volume_gain_db=1.0)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    Path(output_path).write_bytes(response.audio_content)
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    return duration

def download_pexels_video(card: str, output_path: str) -> bool:
    api_key = os.environ["PEXELS_API_KEY"]
    queries = CARD_PEXELS.get(card, DEFAULT_QUERIES)
    random.shuffle(queries)
    for q in queries[:2] + ["dark mystical purple"]:
        try:
            resp = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": api_key}, params={"query": q, "per_page": 10, "size": "medium"}, timeout=30)
            videos = resp.json().get("videos", [])
            if videos:
                video = random.choice(videos)
                chosen = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))[-1]
                with requests.get(chosen["link"], stream=True, timeout=90) as r:
                    with open(output_path, "wb") as out:
                        for chunk in r.iter_content(chunk_size=65536): out.write(chunk)
                return True
        except: continue
    return False

def _make_tarot_card_visual(card: str) -> np.ndarray:
    w, h = 500, 750  # Tarjeta más grande
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        idx = ARCANOS.index(card)
        img_path = Path("cards") / f"m{idx:02d}.jpg"
        if img_path.exists():
            card_img = Image.open(img_path).convert("RGBA").resize((460, 710), Image.LANCZOS)
            img.paste(card_img, (20, 20))
            # Marco elegante
            draw.rectangle([(0, 0), (w-1, h-1)], outline=C_GOLD, width=8)
            draw.rectangle([(12, 12), (w-13, h-13)], outline=C_GOLD_LIGHT, width=2)
            return np.array(img)
    except: pass

    # Fallback si falta la imagen
    draw.rectangle([(0, 0), (w-1, h-1)], fill=C_BG_DEEP, outline=C_GOLD, width=8)
    font_card = _fit_font_to_width(card.upper(), w - 40, 60, 30)
    bbox = draw.textbbox((0, 0), card.upper(), font=font_card)
    draw.text(((w-(bbox[2]-bbox[0]))//2, h//2), card.upper(), font=font_card, fill=C_TEXT)
    return np.array(img)

def _make_top_title(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, 200
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Gradiente sutil arriba
    for y in range(h):
        alpha = int(200 * (1 - (y/h)))
        draw.line([(0, y), (w, y)], fill=(*C_BG_DEEP, alpha))
    
    font_sign, font_card, _ = _load_fonts(55, 40, 20)
    
    signo_text = signo['nombre'].upper()
    bbox = draw.textbbox((0, 0), signo_text, font=font_sign)
    draw.text(((w - (bbox[2]-bbox[0]))//2+2, 40+2), signo_text, font=font_sign, fill=(0, 0, 0, 200))
    draw.text(((w - (bbox[2]-bbox[0]))//2, 40), signo_text, font=font_sign, fill=C_GOLD)
    
    card_text = card.upper()
    bbox = draw.textbbox((0, 0), card_text, font=font_card)
    draw.text(((w - (bbox[2]-bbox[0]))//2+2, 110+2), card_text, font=font_card, fill=(0, 0, 0, 200))
    draw.text(((w - (bbox[2]-bbox[0]))//2, 110), card_text, font=font_card, fill=C_TEXT)
    
    return np.array(img)

def _make_bottom_cta() -> np.ndarray:
    w, h = VIDEO_W, 200
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Gradiente sutil abajo
    for y in range(h):
        alpha = int(200 * (y/h))
        draw.line([(0, y), (w, y)], fill=(*C_BG_DEEP, alpha))
    
    font_big, _, font_sm = _load_fonts(50, 20, 24)
    
    l1 = "Tu carta del día GRATIS en:"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 40), l1, font=font_sm, fill=C_MUTED)
    
    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    draw.text(((w - (bbox[2] - bbox[0]))//2 + 3, 80+3), l2, font=font_big, fill=(0, 0, 0, 230))
    draw.text(((w - (bbox[2] - bbox[0]))//2, 80), l2, font=font_big, fill=C_GOLD)
    
    return np.array(img)

def compose_video(bg_video_path, audio_path, signo, card, output_path, cta_type="none", paleta_tint=None):
    if paleta_tint is None: paleta_tint = random.choice(PALETAS_TINT)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.0

    bg = VideoFileClip(bg_video_path, audio=False)
    if bg.duration < total_duration: bg = concatenate_videoclips([bg.copy() for _ in range(int(total_duration/bg.duration)+2)])
    bg = bg.subclip(0, total_duration)

    if (bg.w / bg.h) > (VIDEO_W/VIDEO_H): bg = bg.resize(height=VIDEO_H).crop(x_center=bg.w/2, width=VIDEO_W)
    else: bg = bg.resize(width=VIDEO_W).crop(y_center=bg.h/2, height=VIDEO_H)

    # Capa oscura para que resalte la carta
    dark = ColorClip(size=(VIDEO_W, VIDEO_H), color=list(C_BG_DEEP)).set_opacity(0.50).set_duration(total_duration)
    tint = ColorClip(size=(VIDEO_W, VIDEO_H), color=list(paleta_tint["color"])).set_opacity(paleta_tint["opacity"]).set_duration(total_duration)

    # Elementos visuales
    card_img = ImageClip(_make_tarot_card_visual(card)).set_position(("center", "center")).set_duration(total_duration).crossfadein(1.0)
    top_title = ImageClip(_make_top_title(signo, card)).set_position(("center", 0)).set_duration(total_duration)
    bottom_cta = ImageClip(_make_bottom_cta()).set_position(("center", VIDEO_H - 200)).set_duration(total_duration)

    final_clips = [bg, dark, tint, card_img, top_title, bottom_cta]

    TEMP_DIR.mkdir(exist_ok=True)
    final = CompositeVideoClip(final_clips, size=(VIDEO_W, VIDEO_H)).set_audio(audio)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(output_path, fps=FPS, codec="libx264", audio_codec="aac", temp_audiofile=str(TEMP_DIR / f"tmp_{Path(output_path).stem}.m4a"), remove_temp=True, threads=2, preset="ultrafast", verbose=False, logger=None)
    
    for clip in [audio, bg, final]:
        try: clip.close()
        except: pass
    return output_path

def generate(signo_idx: int, cta_type: str = "none", prev_scripts: list = None) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)
    signo = SIGNOS[signo_idx]
    card  = get_card_for_sign(signo_idx)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug  = f"{signo['nombre'].lower()}_{stamp}"
    paleta = random.choice(PALETAS_TINT)

    print(f"\n{signo['emoji']}  {signo['nombre']} — {card} [paleta: {paleta['nombre']}]")
    print("─" * 48)

    print("📝  Generando guión...")
    reading = generate_reading(signo, card)

    print(f"    {reading['title']}")
    audio_path = str(TEMP_DIR / f"{slug}.mp3")
    print("🎙️   Generando voz...")
    duration = generate_voice(reading["script"], audio_path, signo["elemento"])
    print(f"    {duration:.1f}s")

    bg_path = str(TEMP_DIR / f"{slug}_bg.mp4")
    print("🎬  Descargando fondo Pexels...")
    if not download_pexels_video(card, bg_path): raise RuntimeError(f"No se pudo descargar fondo para {signo['nombre']}")

    output_path = str(OUTPUT_DIR / f"{slug}.mp4")
    print(f"🎞️   Componiendo video con CTA: {cta_type}")
    compose_video(bg_path, audio_path, signo, card, output_path, cta_type, paleta)
    print(f"✅  {signo['nombre']} listo: {output_path}")

    return {
        "video_path": output_path, "title": reading["title"], "description": reading["description"],
        "tags": reading["tags"], "script": reading["script"], "signo": signo["nombre"],
        "card": card, "duration_s": duration, "cta_type": cta_type, "paleta": paleta["nombre"],
    }