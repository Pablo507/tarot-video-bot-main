# 🔮 Oráculo del Tarot — Video Bot

Bot que genera y publica automáticamente videos de tarot en YouTube 3 veces por semana usando **GitHub Actions** (gratis, sin servidor, sin computadora prendida).

Estética idéntica a [tarotgratis.online](https://tarotgratis.online).

---

## Stack

| Componente | Tecnología | Costo |
|---|---|---|
| Guión | Groq (Llama 3.3 70B) | Gratis |
| Voz | Google Cloud TTS Neural2 | Gratis (1M chars/mes) |
| Fondo | Pexels API | Gratis |
| Composición | MoviePy + PIL | Gratis |
| Publicación | YouTube Data API v3 | Gratis |
| Automatización | GitHub Actions | Gratis (2000 min/mes) |

---

## Flujo

```
GitHub Actions (lun/mié/vie, 11 AM Uruguay)
  → Groq genera el guión de la carta del día
  → Google Cloud TTS genera la voz en español
  → Pexels provee el fondo oscuro místico
  → MoviePy compone el video 1080×1920 (Shorts)
  → YouTube Data API lo publica automáticamente
```

---

## Setup paso a paso

### 1. Instalar entorno local

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
copy .env.example .env         # Windows
# cp .env.example .env         # Mac/Linux
```

Completar `.env` con las keys de Groq y Pexels.

### 2. Google Cloud — un proyecto, tres servicios

Ir a [console.cloud.google.com](https://console.cloud.google.com):

1. **Nuevo proyecto** → `tarot-video-bot`
2. **Facturación** → activar con tarjeta (no te cobra, es requisito de Google)
3. **APIs y servicios → Biblioteca** → habilitar:
   - `YouTube Data API v3`
   - `Cloud Text-to-Speech API`

### 3. Credencial OAuth para YouTube

1. **Credenciales → Crear credenciales → ID de cliente OAuth**
2. Tipo: **App de escritorio** → nombre: `tarot-bot`
3. Descargar JSON → renombrar a `client_secrets.json`

### 4. Service Account para Google Cloud TTS

1. **Credenciales → Crear credenciales → Cuenta de servicio**
2. Nombre: `tarot-tts` → rol: **Editor**
3. Click en la cuenta → **Claves → Agregar clave → JSON**
4. Renombrar a `tts_credentials.json`

### 5. Autorizar YouTube (una sola vez)

```bash
python youtube_upload.py --auth
```

Se abre el browser → autorizás → se guarda `token.json`.

### 6. Test local

```bash
# Solo genera el video (sin subir)
python pipeline.py --dry-run

# Genera y sube como privado para verificar
python pipeline.py --private

# Forzar carta específica
python pipeline.py --dry-run --card "La Luna"
```

### 7. Subir a GitHub

Crear repo → subir todos los archivos.  
El `.gitignore` ya excluye `.env`, `client_secrets.json`, `token.json` y `tts_credentials.json`.

### 8. Configurar 5 GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Nombre | Valor |
|---|---|
| `GROQ_API_KEY` | tu key de Groq |
| `PEXELS_API_KEY` | tu key de Pexels |
| `YOUTUBE_CLIENT_SECRETS` | contenido completo de `client_secrets.json` |
| `YOUTUBE_TOKEN_JSON` | contenido completo de `token.json` |
| `GOOGLE_TTS_CREDENTIALS` | contenido completo de `tts_credentials.json` |

Para copiar el contenido de un JSON: abrís con Bloc de notas → Ctrl+A → Ctrl+C.

### 9. Test en la nube

**Actions → Publicar video de Tarot en YouTube → Run workflow → tildar Dry run → Run**

Descargá el MP4 desde Artifacts. Si se ve bien, corré sin dry-run.

---

## Voces disponibles

Configurar en `.env` → `GOOGLE_TTS_VOICE`:

| Voz | Descripción |
|---|---|
| `es-US-Neural2-A` | Femenina, neutro latinoamericano (default) |
| `es-US-Journey-F` | Femenina, más expresiva y natural |
| `es-US-Neural2-B` | Masculina, neutro latinoamericano |
| `es-ES-Neural2-A` | Femenina, castellano de España |

---

## Uso de cuota mensual (3 videos/semana = 12/mes)

| Servicio | Límite gratis | Uso real |
|---|---|---|
| GitHub Actions | 2,000 min | ~60 min |
| Groq | 14,400 req/día | 12 req/mes |
| Google TTS | 1,000,000 chars | ~24,000 chars |
| Pexels | 200 req/hora | 12 req/mes |
| YouTube API | 10,000 unidades/día | ~19,200 unidades/mes |

---

## Solución de problemas

**"google.auth.exceptions.DefaultCredentialsError"**
→ Verificar que `tts_credentials.json` existe y que `GOOGLE_APPLICATION_CREDENTIALS` apunta a él.

**"Token expired" en GitHub Actions**
→ Correr `python youtube_upload.py --auth` localmente y actualizar el Secret `YOUTUBE_TOKEN_JSON`.

**Video de fondo negro**
→ Verificar `PEXELS_API_KEY` en los Secrets.

**ffmpeg not found (Windows local)**
→ moviepy incluye ffmpeg automáticamente. Si falla, instalar [ffmpeg](https://ffmpeg.org/download.html) manualmente.
