#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Muestra que hay que aprender: las correcciones que dejaron Barbara y Justo
usando /responder, y como viene usandose la herramienta.

Las correcciones viven en Firestore y ya entran al prompt en caliente. Este
script es para el paso siguiente: CONSOLIDARLAS en la boveda, que es donde el
conocimiento tiene que vivir de verdad. Una lista de parches que crece sin
parar termina contradiciendo al manual; una pagina de la boveda bien escrita,
no.

Uso:
    python tools/aprender.py
"""
import io
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CREDS = RAIZ / "tools" / "credenciales.json"
API_KEY = "AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs"
PROY = "india-tejidos"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROY}/databases/(default)/documents"


def entrar():
    c = json.loads(CREDS.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
        data=json.dumps({"email": f"{c['usuario']}@india-admin.local",
                         "password": c["password"], "returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["idToken"]


def traer(ruta, token):
    req = urllib.request.Request(BASE + ruta, headers={"Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(req))


def valor(campo):
    """Firestore envuelve cada valor en su tipo; aca se desenvuelve."""
    if not isinstance(campo, dict):
        return campo
    for k in ("stringValue", "booleanValue", "timestampValue", "integerValue"):
        if k in campo:
            return campo[k]
    if "arrayValue" in campo:
        return [valor(v) for v in campo["arrayValue"].get("values", [])]
    if "mapValue" in campo:
        return {k: valor(v) for k, v in campo["mapValue"].get("fields", {}).items()}
    return None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not CREDS.exists():
        raise SystemExit("Falta tools/credenciales.json")
    token = entrar()

    # ── correcciones ──
    cfg = traer("/config/asistente", token).get("fields", {})
    correcciones = valor(cfg.get("correcciones", {})) or []
    print(f"\n{'='*66}\nCORRECCIONES QUE DEJARON ({len(correcciones)})\n{'='*66}")
    if not correcciones:
        print("Ninguna todavia. Aparecen cuando le dicen 'no, eso se dice asi'.")
    else:
        por_tema = {}
        for c in correcciones:
            por_tema.setdefault(c.get("tema", "general"), []).append(c)
        for tema, lista in sorted(por_tema.items(), key=lambda x: -len(x[1])):
            print(f"\n  {tema.upper()}  ({len(lista)})")
            for c in lista:
                print(f"    · {c.get('regla','')}")
                print(f"      {c.get('fecha','')[:10]}")
        print(f"\n  >>> Consolidar estas en la pagina de la boveda que corresponda,")
        print(f"      recompilar, y vaciar la lista desde la consola de Firebase.")

    # ── uso ──
    docs = traer("/asistente_uso?pageSize=300", token).get("documents", [])
    usos = [{k: valor(v) for k, v in d.get("fields", {}).items()} for d in docs]
    print(f"\n{'='*66}\nCOMO SE VIENE USANDO ({len(usos)} respuestas sugeridas)\n{'='*66}")
    if not usos:
        print("Sin datos todavia.")
        raise SystemExit(0)

    copiadas = [u for u in usos if u.get("copiado")]
    print(f"  Copiadas tal cual : {len(copiadas)} de {len(usos)} ({100*len(copiadas)//len(usos)}%)")
    print(f"  Modelo            : {Counter(u.get('modelo','?') for u in usos).most_common()}")
    largos = [len(u.get("sugerido", "")) for u in usos]
    print(f"  Largo promedio    : {sum(largos)//len(largos)} caracteres")

    sin_copiar = [u for u in usos if not u.get("copiado")]
    if sin_copiar:
        print(f"\n  {len(sin_copiar)} sugerencias NO se copiaron. Son las que hay que mirar:")
        print("  (si no se copio, o no servia, o la reescribieron a mano)")
        for u in sin_copiar[:5]:
            print(f"\n    pidieron  : {(u.get('pedido') or '')[:90]}")
            print(f"    se sugirio: {(u.get('sugerido') or '')[:90]}")

    print(f"\n{'='*66}")
    print("EL CRUCE QUE FALTA: comparar esto contra lo que Barbara REALMENTE mando,")
    print("que Evolution guarda en el server. Ahi se ve donde el manual esta flojo.")
    print("Necesita acceso SSH al servidor n8n.")
