#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sube el manual compilado a Firestore, para que /responder lo levante solo.

Sin esto hay que abrir la pagina y elegir el archivo a mano cada vez que la
boveda cambia. Con esto, el flujo es: se mejora una pagina de la boveda ->
se recompila -> se sube. Barbara y Justo no tocan nada.

Necesita las credenciales del panel en `tools/credenciales.json` (ignorado
por git):

    {"usuario": "barbara123", "password": "LA_QUE_USAN_PARA_ENTRAR"}

Uso:
    python tools/compilar-manual.py && python tools/subir-manual.py
"""
import json
import sys
import io
import urllib.request
import urllib.error
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANUAL = RAIZ / "tools" / "manual.txt"
CREDS = RAIZ / "tools" / "credenciales.json"

# La misma clave publica que usa la web (firebase-config.js). No es un secreto:
# lo que protege el acceso son las reglas de Firestore y el login.
API_KEY = "AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs"
PROYECTO = "india-tejidos"
DOMINIO = "india-admin.local"


def pedir(url, datos=None, headers=None, metodo=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(datos).encode("utf-8") if datos is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")
        try:
            detalle = json.loads(detalle)["error"]["message"]
        except Exception:
            pass
        raise SystemExit(f"Error {e.code}: {detalle}")


def entrar(usuario, password):
    """Login con el mismo usuario del panel. Devuelve el token."""
    r = pedir(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
        {"email": f"{usuario.lower()}@{DOMINIO}", "password": password, "returnSecureToken": True},
    )
    return r["idToken"]


def subir(token, manual):
    """Escribe solo el campo `manual`; el resto del documento queda intacto."""
    url = (
        f"https://firestore.googleapis.com/v1/projects/{PROYECTO}/databases/(default)"
        f"/documents/config/asistente?updateMask.fieldPaths=manual"
        f"&updateMask.fieldPaths=actualizado&updateMask.fieldPaths=por"
    )
    from datetime import datetime, timezone
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return pedir(
        url,
        {"fields": {
            "manual": {"stringValue": manual},
            "actualizado": {"timestampValue": ahora},
            "por": {"stringValue": "compilado desde la boveda"},
        }},
        headers={"Authorization": "Bearer " + token},
        metodo="PATCH",
    )


if __name__ == "__main__":
    if not MANUAL.exists():
        raise SystemExit("Falta tools/manual.txt. Corre antes: python tools/compilar-manual.py")
    if not CREDS.exists():
        raise SystemExit(
            "Falta tools/credenciales.json. Crealo con:\n"
            '    {"usuario": "barbara123", "password": "LA_QUE_USAN_PARA_ENTRAR"}\n'
            "Esta en .gitignore, no se sube a ningun lado."
        )

    creds = json.loads(CREDS.read_text(encoding="utf-8"))
    manual = MANUAL.read_text(encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Entrando como {creds['usuario']}...")
    token = entrar(creds["usuario"], creds["password"])
    print(f"Subiendo {len(manual):,} caracteres...")
    subir(token, manual)
    print("Listo. /responder lo levanta solo la proxima vez que lo abran.")
