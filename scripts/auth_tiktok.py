#!/usr/bin/env python3
"""
scripts/auth_tiktok.py - Silicon Verdict TikTok OAuth 2.0 Handshake & Credential Persistence.
Refactored with defensive environment loading, credential integrity validation,
and strict urllib.parse.urlencode parameter encoding.
"""

import os
import sys
import json
import time
import base64
import hashlib
import secrets
import logging
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from dotenv import find_dotenv, load_dotenv

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auth_tiktok")

# --- 1. CARGA DEFENSIVA Y VALIDACIÓN DE CREDENCIALES ---
env_file = find_dotenv(usecwd=True)
if env_file:
    load_dotenv(env_file, override=True)
    logger.info("Archivo de entorno cargado desde: %s", env_file)
else:
    load_dotenv(BASE_DIR / ".env", override=True)
    logger.info("Archivo de entorno cargado desde: %s", BASE_DIR / ".env")

# Limpieza estricta de espacios, saltos de línea y comillas accidentales
client_key = os.getenv("TIKTOK_CLIENT_KEY", "").strip().strip("'\"")
client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "").strip().strip("'\"")

PORT = 8080
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", f"http://localhost:{PORT}/callback").strip()
TOKEN_OUTPUT_FILE = BASE_DIR / "data" / "tiktok_token.json"
TIKTOK_TOKEN_ENDPOINT = "https://open.tiktokapis.com/v2/oauth/token/"
BASE_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"


def validate_credentials(key: str, secret: str):
    """Comprobación de integridad de claves antes de iniciar el handshake."""
    if not key or key.lower() in ("tu_client_key_aqui", "your_client_key", "none", ""):
        print("\n" + "=" * 75)
        print(" [ERROR FATAL] TIKTOK_CLIENT_KEY no está configurada o contiene el valor por defecto.")
        print(" Revisa tu archivo .env y asigna tu Client Key obtenida de TikTok for Developers.")
        print("=" * 75 + "\n")
        sys.exit(1)

    if not secret or secret.lower() in ("tu_client_secret_aqui", "your_client_secret", "none", ""):
        print("\n" + "=" * 75)
        print(" [ERROR FATAL] TIKTOK_CLIENT_SECRET está vacía. Configúrala en tu archivo .env.")
        print("=" * 75 + "\n")
        sys.exit(1)

    # Advertencia crítica si es solo numérico (App ID en lugar de Client Key)
    if key.isdigit():
        print("\n" + "!" * 75)
        print(" [ADVERTENCIA CRÍTICA] LA CLIENT KEY INTRODUCIDA ES PURAMENTE NUMÉRICA:")
        print(f" Valor detectado: {key}")
        print(" Parece que has introducido el 'App ID' en lugar de la 'Client Key' de TikTok.")
        print(" En TikTok for Developers, la Client Key suele empezar por 'aw...' o mezclar letras y números.")
        print(" Si TikTok muestra un error de 'client_key', entra a developers.tiktok.com/apps")
        print(" y copia el valor del campo 'Client Key' (NO del App ID).")
        print("!" * 75 + "\n")


def mask_credential(val: str) -> str:
    """Oculta los caracteres intermedios para verificación visual segura."""
    if len(val) <= 8:
        return "****"
    return f"{val[:4]}{'*' * (len(val) - 8)}{val[-4:]}"


def generate_fresh_pkce_pair():
    """Generates a fresh, single-use PKCE pair using Hex SHA-256 encoding for TikTok API.
    TikTok requires:
    1. A brand new random string for every authorization attempt (min 43, max 128 chars).
    2. Hex encoding of the raw SHA-256 hash for code_challenge.
    """
    code_verifier = secrets.token_urlsafe(45)  # 60 characters
    sha256_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = sha256_hash.hex()  # Exact Hex string for TikTok

    pkce_file = BASE_DIR / "data" / ".tiktok_pkce_verifier.txt"
    pkce_file.parent.mkdir(parents=True, exist_ok=True)
    pkce_file.write_text(code_verifier, encoding="utf-8")
    OAuthCallbackHandler.current_verifier = code_verifier

    return code_verifier, code_challenge


# --- 2. SERVIDOR LOCAL Y PERSISTENCIA ---
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_success = False
    current_verifier = None

    def log_message(self, format, *args):
        sys.stderr.write(f"[oauth_server] {self.address_string()} - {format % args}\n")

    def do_GET(self):
        url = urlparse(self.path)

        if url.path not in ("/callback", "/callback/"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        params = parse_qs(url.query)

        # Manejo de error retornado por TikTok
        if "error" in params:
            err_name = params.get("error", ["Unknown error"])[0]
            err_desc = params.get("error_description", [err_name])[0]
            logger.error("[TIKTOK REDIRECT ERROR]: %s (%s)", err_name, err_desc)
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_err = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;background:#0f172a;color:#fff;padding:40px;text-align:center;">
<h1 style="color:#ef4444;">❌ Error de TikTok: {err_name}</h1>
<p style="color:#94a3b8;">{err_desc}</p>
<p>Revisa la terminal para ver el diagnóstico completo.</p>
</body></html>"""
            self.wfile.write(html_err.encode("utf-8"))
            return

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if not code:
            logger.error("No se recibió el parámetro 'code' en la redirección.")
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Parametro 'code' no encontrado en la peticion.")
            return

        logger.info("[✓] Código de autorización recibido: %s... (state: %s)", code[:10], state)
        logger.info("Ejecutando canje POST a %s...", TIKTOK_TOKEN_ENDPOINT)

        # Recuperar code_verifier garantizando correspondencia biunívoca con code_challenge
        verifier = OAuthCallbackHandler.current_verifier
        if not verifier:
            pkce_file = BASE_DIR / "data" / ".tiktok_pkce_verifier.txt"
            if pkce_file.is_file():
                verifier = pkce_file.read_text(encoding="utf-8").strip()
        logger.info("[PKCE DEBUG] Using verifier (len=%d): %s...", len(verifier) if verifier else 0, verifier[:12] if verifier else "None")

        host_header = self.headers.get("Host", f"localhost:{PORT}")
        scheme = "https" if "https" in self.headers.get("X-Forwarded-Proto", "") else "http"
        detected_redirect_uri = f"{scheme}://{host_header}{url.path}"

        # Canje por tokens persistentes
        exchange_payload = {
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": detected_redirect_uri,
        }
        if verifier:
            exchange_payload["code_verifier"] = verifier

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        }

        logger.info("[TOKEN EXCHANGE] POST %s -> redirect_uri=%s", TIKTOK_TOKEN_ENDPOINT, detected_redirect_uri)
        try:
            resp = requests.post(TIKTOK_TOKEN_ENDPOINT, data=exchange_payload, headers=headers, timeout=30)
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {"raw_text": resp.text}
        except Exception as exc:
            logger.error("Error de red contactando a TikTok: %s", exc)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error de red: {exc}".encode("utf-8"))
            return

        # Validación estricta del resultado JSON
        data_block = resp_json.get("data", resp_json) if isinstance(resp_json, dict) else {}
        access_token = data_block.get("access_token")
        refresh_token = data_block.get("refresh_token")

        # Fallback defensivo: si TikTok rechaza el PKCE en un cliente confidencial con client_secret
        if (not access_token or not refresh_token) and isinstance(resp_json, dict):
            err_desc = str(resp_json.get("error_description", "")).lower()
            if "verifier" in err_desc or "challenge" in err_desc:
                logger.warning("[PKCE FALLBACK] TikTok devolvió '%s'. Probando canje sin code_verifier...", err_desc)
                payload_fallback = dict(exchange_payload)
                payload_fallback.pop("code_verifier", None)
                try:
                    resp_fb = requests.post(TIKTOK_TOKEN_ENDPOINT, data=payload_fallback, headers=headers, timeout=30)
                    resp_fb_json = resp_fb.json()
                    data_fb = resp_fb_json.get("data", resp_fb_json)
                    if resp_fb.status_code == 200 and data_fb.get("access_token"):
                        logger.info("[✓] Canje exitoso mediante fallback confidencial (client_secret)!")
                        resp_json = resp_fb_json
                        data_block = data_fb
                        access_token = data_block.get("access_token")
                        refresh_token = data_block.get("refresh_token")
                except Exception as exc_fb:
                    logger.debug("Fallback confidencial falló: %s", exc_fb)

        if resp.status_code != 200 or not access_token or not refresh_token:
            print("\n" + "=" * 75)
            print(" [!] ERROR AL CANJEAR TOKEN EN TIKTOK:")
            print(f" HTTP Status: {resp.status_code}")
            print(" Respuesta completa del servidor TikTok:")
            print(json.dumps(resp_json, indent=2))
            print("=" * 75 + "\n")

            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_fail = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;background:#0f172a;color:#fff;padding:40px;text-align:center;">
<h1 style="color:#ef4444;">❌ Fallo en el canje de tokens</h1>
<p style="color:#94a3b8;">HTTP {resp.status_code}</p>
<pre style="background:#020617;padding:20px;border-radius:10px;text-align:left;max-width:600px;margin:20px auto;color:#38bdf8;">{json.dumps(resp_json, indent=2)}</pre>
</body></html>"""
            self.wfile.write(html_fail.encode("utf-8"))
            return

        # Estructuración y persistencia del token con timestamp UNIX actual
        now_unix = time.time()
        persisted_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "open_id": data_block.get("open_id", ""),
            "expires_in": data_block.get("expires_in", 86400),
            "refresh_expires_in": data_block.get("refresh_expires_in", 31536000),
            "scope": data_block.get("scope", "user.info.basic,video.upload,video.publish"),
            "token_type": data_block.get("token_type", "Bearer"),
            "created_at": now_unix,
            "issued_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_unix)),
            "client_key": client_key,
        }

        TOKEN_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(persisted_data, f, indent=2)

        # Copia secundaria en raíz para redundancia
        try:
            with open(BASE_DIR / "tiktok_token.json", "w", encoding="utf-8") as f:
                json.dump(persisted_data, f, indent=2)
        except Exception:
            pass

        print("\n" + "=" * 75)
        print(" [✓] CANJE DE TOKENS EXITOSO:")
        print(f" Token File:          {TOKEN_OUTPUT_FILE}")
        print(f" OpenID:              {data_block.get('open_id')}")
        print(f" Access Token Exp:    {data_block.get('expires_in', 86400)}s (~{data_block.get('expires_in', 86400)//3600}h)")
        print(f" Refresh Token Exp:   {data_block.get('refresh_expires_in', 31536000)}s (~{data_block.get('refresh_expires_in', 31536000)//86400} días)")
        print("=" * 75 + "\n")

        # Respuesta HTTP 200 al navegador
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html_ok = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Silicon Verdict // Autorización Completada</title>
  <style>
    body { background: #07090e; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .card { background: rgba(15, 23, 42, 0.9); border: 1px solid #10b981; border-radius: 20px; padding: 40px 50px; text-align: center; max-width: 520px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); }
    .badge { font-size: 40px; margin-bottom: 16px; }
    h1 { font-size: 22px; margin-bottom: 12px; }
    p { color: #94a3b8; font-size: 14px; line-height: 1.5; margin-bottom: 20px; }
    .pill { background: rgba(0, 242, 254, 0.1); border: 1px solid rgba(0, 242, 254, 0.3); color: #00f2fe; padding: 8px 16px; border-radius: 8px; font-family: monospace; font-size: 13px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">✅</div>
    <h1>Autorización de Silicon Verdict completada</h1>
    <p>La cuenta de TikTok ha sido vinculada con éxito. Las credenciales persistentes se han guardado en <strong>data/tiktok_token.json</strong>.</p>
    <div class="pill">Puedes cerrar esta pestaña y volver a la terminal</div>
  </div>
</body>
</html>"""
        self.wfile.write(html_ok.encode("utf-8"))
        OAuthCallbackHandler.auth_success = True

        # Apagado limpio del servidor
        def shutdown_server():
            time.sleep(1.0)
            logger.info("Cerrando el servidor callback local...")
            server.shutdown()

        threading.Thread(target=shutdown_server, daemon=True).start()


# --- 3. CONSTRUCCIÓN ROBUSTA DE LA URL OAUTH Y EJECUCIÓN ---
def run_auth_flow():
    global server

    # Validación de integridad de credenciales
    validate_credentials(client_key, client_secret)

    # Generación de PKCE fresco y único para este intento
    code_verifier, code_challenge = generate_fresh_pkce_pair()

    # Generar URLs para ambas variantes (con barra final y sin barra final)
    params_slash = {
        "client_key": client_key,
        "scope": "user.info.basic,video.upload,video.publish",
        "response_type": "code",
        "redirect_uri": f"http://localhost:{PORT}/callback/",
        "state": "silicon_verdict_auth",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    params_noslash = dict(params_slash, redirect_uri=f"http://localhost:{PORT}/callback")
    
    auth_url_slash = f"{BASE_AUTH_URL}?{urlencode(params_slash)}"
    auth_url_noslash = f"{BASE_AUTH_URL}?{urlencode(params_noslash)}"

    print("\n" + "=" * 75)
    print(" === SILICON VERDICT // TIKTOK OAUTH 2.0 INITIAL HANDSHAKE ===")
    print("=" * 75)
    print(f" Detected Client Key: {mask_credential(client_key)}  (Longitud: {len(client_key)} chars | Raw: {client_key})")
    print(f" Client Secret:       {mask_credential(client_secret)}  (Longitud: {len(client_secret)} chars)")
    print(f" Scopes:              {params_slash['scope']}")
    print(f" PKCE Challenge:      {code_challenge} (Method: S256)")
    print(f" Output File:         {TOKEN_OUTPUT_FILE}")
    print("-" * 75)
    print(" Opción 1 (CON barra final, recomendada por TikTok Desktop):")
    print(f" {auth_url_slash}")
    print("-" * 75)
    print(" Opción 2 (SIN barra final):")
    print(f" {auth_url_noslash}")
    print("=" * 75 + "\n")

    # Iniciar servidor HTTP escuchando en todas las interfaces del puerto 8080
    try:
        server = HTTPServer(("", PORT), OAuthCallbackHandler)
    except OSError as e:
        logger.critical("No se pudo enlazar el puerto %d: %s. ¿Hay otro proceso ejecutándose?", PORT, e)
        sys.exit(1)

    print(f"[*] Servidor local escuchando en http://localhost:{PORT}/callback/ y http://localhost:{PORT}/callback")
    print("[*] Abriendo el navegador web predeterminado (Opción 1 con /)...")

    try:
        webbrowser.open(auth_url_slash)
    except Exception as exc:
        logger.warning("No se pudo abrir el navegador automáticamente (%s). Abre la URL manualmente arriba.", exc)

    print("[*] Esperando la redirección de TikTok en http://localhost:8080/callback ... (Ctrl+C para cancelar)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Proceso de autorización cancelado por el usuario.")
        server.server_close()
        sys.exit(1)

    if OAuthCallbackHandler.auth_success:
        print("\n" + "=" * 75)
        print(" [✓] AUTORIZACIÓN DE TIKTOK COMPLETADA SATISFACTORIAMENTE")
        print(f" Credenciales guardadas en: {TOKEN_OUTPUT_FILE}")
        print(" El pipeline de publicación vertical en TikTok ya cuenta con acceso desatendido.")
        print("=" * 75 + "\n")
    else:
        print("\n[!] La autorización no finalizó correctamente.")
        sys.exit(1)


if __name__ == "__main__":
    run_auth_flow()
