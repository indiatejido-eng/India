#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sube la bitacora de pruebas a Firestore, para que se vea en /carga -> Mapa del pais.

La investigacion larga vive en la boveda (`Boveda/India/Marketing/`). Aca van solo
los RESULTADOS, en fichas cortas: que variable se movio, que quedo quieto, que paso.
La regla del metodo es esa: una variable por vez, o no se sabe cual la movio.

Se edita `tools/hallazgos.json` y se corre esto. Cada ficha se escribe por su `id`,
asi que volver a subir la misma no duplica: la pisa.

Necesita las credenciales del panel en `tools/credenciales.json` (ignorado por git):

    {"usuario": "barbara123", "password": "LA_QUE_USAN_PARA_ENTRAR"}

Uso:
    python tools/subir-hallazgos.py
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FICHAS = RAIZ / "tools" / "hallazgos.json"
CREDS = RAIZ / "tools" / "credenciales.json"

# La misma clave publica que usa la web (firebase-config.js). No es un secreto:
# lo que protege el acceso son las reglas de Firestore y el login.
API_KEY = "AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs"
PROYECTO = "india-tejidos"
DOMINIO = "india-admin.local"

CAMPOS = ("fecha", "titulo", "variable", "fijo", "veredicto", "resultado")


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


def subir(token, ficha):
    """Escribe una ficha por su id. Vuelve a subirla la pisa, no la duplica."""
    campos = [c for c in CAMPOS if ficha.get(c)]
    mask = "&".join(f"updateMask.fieldPaths={c}" for c in campos)
    url = (
        f"https://firestore.googleapis.com/v1/projects/{PROYECTO}/databases/(default)"
        f"/documents/hallazgos/{ficha['id']}?{mask}"
    )
    return pedir(
        url,
        {"fields": {c: {"stringValue": str(ficha[c])} for c in campos}},
        headers={"Authorization": "Bearer " + token},
        metodo="PATCH",
    )


if __name__ == "__main__":
    if not FICHAS.exists():
        raise SystemExit("Falta tools/hallazgos.json.")
    if not CREDS.exists():
        raise SystemExit(
            "Falta tools/credenciales.json. Crealo con:\n"
            '    {"usuario": "barbara123", "password": "LA_QUE_USAN_PARA_ENTRAR"}\n'
            "Esta en .gitignore, no se sube a ningun lado."
        )

    creds = json.loads(CREDS.read_text(encoding="utf-8"))
    fichas = json.loads(FICHAS.read_text(encoding="utf-8"))

    faltan = [f for f in fichas if not f.get("id") or not f.get("titulo")]
    if faltan:
        raise SystemExit(f"{len(faltan)} ficha(s) sin `id` o sin `titulo`. No se subio nada.")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Entrando como {creds['usuario']}...")
    token = entrar(creds["usuario"], creds["password"])
    for f in fichas:
        subir(token, f)
        print(f"  ok  {f['id']}")
    print(f"Listo: {len(fichas)} ficha(s). Se ven en /carga -> Mapa del pais.")
