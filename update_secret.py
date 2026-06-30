import os
import json
import sys
import requests
from base64 import b64encode
from nacl import encoding, public

def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key_bytes = encoding.Base64Encoder.decode(public_key.encode("utf-8"))
    public_key_obj = public.PublicKey(public_key_bytes)
    sealed_box = public.SealedBox(public_key_obj)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

def main():
    gh_pat = os.getenv("GH_PAT")
    repository = os.getenv("GITHUB_REPOSITORY")
    original_token_str = os.getenv("ORIGINAL_YOUTUBE_TOKEN_JSON")
    token_file = "token.json"

    if not gh_pat:
        print("❌ Error: GH_PAT no está configurado como variable de entorno.")
        sys.exit(1)
    if not repository:
        print("❌ Error: GITHUB_REPOSITORY no está configurado.")
        sys.exit(1)
    if not os.path.exists(token_file):
        print(f"⚠️ Advertencia: Archivo {token_file} no encontrado. Nada que actualizar.")
        sys.exit(0)

    with open(token_file, "r", encoding="utf-8") as f:
        current_token_str = f.read().strip()

    # Comparar si hay cambios reales para evitar llamadas innecesarias a la API
    try:
        current_json = json.loads(current_token_str)
        if original_token_str:
            original_json = json.loads(original_token_str)
            # Comparamos si el access_token o la expiración cambiaron
            if current_json.get("token") == original_json.get("token"):
                print("ℹ️ El token de YouTube no ha cambiado. No es necesario actualizar el secreto.")
                sys.exit(0)
        else:
            print("⚠️ No se proporcionó el token original para comparar, se procederá a actualizar.")
    except Exception as e:
        print(f"⚠️ Error al comparar tokens ({e}). Se actualizará de todos modos.")

    # 1. Obtener clave pública del repositorio
    headers = {
        "Authorization": f"token {gh_pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    pub_key_url = f"https://api.github.com/repos/{repository}/actions/secrets/public-key"
    
    print("🔑 Obteniendo clave pública de GitHub...")
    resp = requests.get(pub_key_url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Error al obtener clave pública: {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    pub_key_data = resp.json()
    key_id = pub_key_data["key_id"]
    public_key = pub_key_data["key"]

    # 2. Encriptar el valor del secreto
    encrypted_value = encrypt(public_key, current_token_str)

    # 3. Actualizar el secreto en GitHub
    secret_name = "YOUTUBE_TOKEN_JSON"
    secret_url = f"https://api.github.com/repos/{repository}/actions/secrets/{secret_name}"
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    
    print(f"📤 Actualizando secreto '{secret_name}'...")
    resp = requests.put(secret_url, headers=headers, json=data)
    if resp.status_code in (201, 204):
        print(f"✅ Secreto '{secret_name}' actualizado exitosamente en GitHub.")
    else:
        print(f"❌ Error al actualizar secreto: {resp.status_code} - {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
