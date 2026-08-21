# -*- coding: utf-8 -*-
"""
Endpoint del asistente de respuestas — se monta sobre el crm-api que ya corre
en el servidor (contenedor `crm-api`, puerto 8090).

Que hace: recibe el pedido de /responder, le pega la API key de Anthropic
(que vive SOLO aca, nunca en el navegador) y lo reenvia. Nada mas. La logica
de herramientas corre en el navegador contra el propio crm-api, asi que este
archivo es un pasamanos y no tiene que saber nada del negocio.

Instalar:
  1. Copiar este archivo junto al app.py del crm-api.
  2. En app.py:  from asistente import registrar_asistente
                 registrar_asistente(app, verificar_token)
     (`verificar_token` es la funcion que el crm-api ya usa para validar el
     token de Firebase en el resto de las rutas.)
  3. En el docker-compose.yml del contenedor crm-api, sumar la variable:
                 ANTHROPIC_API_KEY: "sk-ant-..."
  4. docker compose up -d crm-api

Verificar:  curl -H "Authorization: Bearer <token>" \
                 https://crm.india-tejidos.duckdns.org/api/asistente/health
Cuando eso devuelva 200, /responder deja de pedir la clave sola.
"""
import os
import json
import urllib.request
import urllib.error

from flask import request, jsonify

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
TIMEOUT = 120

# Techo por pedido, para que un bucle raro no se coma la cuenta.
MAX_TOKENS_TECHO = 4000


def registrar_asistente(app, verificar_token):
    """Cuelga /asistente y /asistente/health del crm-api."""

    @app.route("/api/asistente/health", methods=["GET"])
    def asistente_health():
        if not verificar_token(request):
            return jsonify({"error": "no autorizado"}), 401
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return jsonify({"ok": False, "error": "falta ANTHROPIC_API_KEY"}), 503
        return jsonify({"ok": True})

    @app.route("/api/asistente", methods=["POST"])
    def asistente():
        if not verificar_token(request):
            return jsonify({"error": "no autorizado"}), 401

        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return jsonify({"error": "falta ANTHROPIC_API_KEY en el server"}), 503

        cuerpo = request.get_json(silent=True) or {}
        if "messages" not in cuerpo:
            return jsonify({"error": "falta messages"}), 400
        cuerpo["max_tokens"] = min(int(cuerpo.get("max_tokens", 2000)), MAX_TOKENS_TECHO)

        pedido = urllib.request.Request(
            ANTHROPIC_URL,
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
                return app.response_class(
                    response=r.read(), status=r.status, mimetype="application/json"
                )
        except urllib.error.HTTPError as e:
            # el error de Anthropic pasa tal cual: la pagina sabe mostrarlo
            return app.response_class(
                response=e.read(), status=e.code, mimetype="application/json"
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 502
