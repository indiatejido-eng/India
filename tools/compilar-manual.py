#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compila el manual del asistente de respuestas a partir de la boveda.

La boveda es la unica fuente de verdad: aca no se escribe conocimiento del
negocio, solo se elige que paginas entran y en que orden. Cuando una pagina de
la boveda mejora, el manual mejora al recompilar. No hay copias que se
desincronicen.

Uso:
    python tools/compilar-manual.py            # escribe manual.txt y muestra el tamano
    python tools/compilar-manual.py --stdout   # lo escupe por pantalla

Despues: abrir /responder -> Ajustes -> pegar el manual -> Guardar.
Queda en Firestore (config/asistente) y lo levantan todos los que entren.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BOVEDA = RAIZ / "Boveda" / "India"
SALIDA = RAIZ / "tools" / "manual.txt"

# Que entra al manual y con que encabezado. El orden importa: lo primero
# pesa mas en como responde el modelo.
PAGINAS = [
    ("Clientes/Cómo se conversa.md",      "COMO SE CONVERSA — el manual de atencion. Esto manda."),
    ("Clientes/Objeciones frecuentes.md", "OBJECIONES — las preguntas que se repiten y su respuesta"),
    ("Producto/Precios.md",               "PRECIOS — la lista vigente"),
    ("Producto/A medida.md",              "A MEDIDA — el servicio: medidas, sena, plazos"),
    ("Producto/Chalecos.md",              "CHALECOS — modelos, talles, colores"),
    ("Marca/Voz y tono.md",               "VOZ Y TONO — como escribe la marca"),
    ("Producto/Lana e hilado.md",         "LANA — la materia prima"),
    ("Operaciones/Envíos.md",             "ENVIOS"),
    ("Clientes/Público objetivo.md",      "A QUIEN LE VENDEMOS"),
]

# Secciones que son notas internas de trabajo, no conocimiento para responder.
SECCIONES_FUERA = ("falta", "pendiente", "por hacer", "to-do", "todo")


def limpiar(texto: str) -> str:
    """Saca frontmatter, secciones de pendientes y ruido de Obsidian."""
    # frontmatter YAML
    texto = re.sub(r"^---\n.*?\n---\n", "", texto, flags=re.DOTALL)

    # secciones "## Falta" y similares: son to-dos de Justo, no le sirven al asistente
    lineas, saltando = [], False
    for linea in texto.split("\n"):
        encabezado = re.match(r"^(#{1,6})\s+(.*)", linea)
        if encabezado:
            nivel = len(encabezado.group(1))
            titulo = encabezado.group(2).strip().lower()
            if nivel <= 2 and any(titulo.startswith(p) for p in SECCIONES_FUERA):
                saltando = True
                continue
            if nivel <= 2:
                saltando = False
        if not saltando:
            lineas.append(linea)
    texto = "\n".join(lineas)

    # los [[wikilinks]] no significan nada fuera de Obsidian: dejamos solo el texto
    texto = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", texto)
    texto = re.sub(r"\[\[([^\]]+)\]\]", r"\1", texto)

    # lineas de solo espacios y saltos triples
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def compilar() -> str:
    partes, faltantes = [], []
    for ruta, encabezado in PAGINAS:
        archivo = BOVEDA / ruta
        if not archivo.exists():
            faltantes.append(ruta)
            continue
        cuerpo = limpiar(archivo.read_text(encoding="utf-8"))
        if len(cuerpo) < 200:  # paginas casi vacias solo gastan contexto
            faltantes.append(f"{ruta} (casi vacia, {len(cuerpo)} chars)")
            continue
        partes.append(f"<<< {encabezado} >>>\n\n{cuerpo}")

    if faltantes:
        print("No entraron:", file=sys.stderr)
        for f in faltantes:
            print(f"  - {f}", file=sys.stderr)

    return "\n\n\n".join(partes)


if __name__ == "__main__":
    manual = compilar()
    if "--stdout" in sys.argv:
        print(manual)
    else:
        SALIDA.write_text(manual, encoding="utf-8")
        aprox = len(manual) // 4
        print(f"\nManual compilado -> {SALIDA}")
        print(f"{len(manual):,} caracteres (~{aprox:,} tokens)")
        print("\nAhora: abrir /responder -> Ajustes -> pegar el contenido -> Guardar manual.")
