# -*- coding: utf-8 -*-
"""Arma las piezas de /disenar a partir de las fotos reales del catálogo.

La idea: el configurador NO dibuja un chaleco, muestra el chaleco de verdad.
La silueta, el volumen, la percha y el punto del tejido salen de la foto; lo
único que cambia en el navegador es el tono de la lana, y cambia por
luminancia — la misma técnica con la que se recoloreó el centímetro a amarillo.

Por eso cada pieza se guarda en gris normalizado + alfa: el navegador le aplica
una rampa de color y listo. Una imagen por combinación de dibujo y cuello, no
una por cada color.

Uso:  python tools/piezas.py
Sale: disenar/piezas/*.webp  +  disenar/piezas/piezas.json
"""
import io
import json
import os
import urllib.request

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'disenar', 'piezas')
API = ('https://firestore.googleapis.com/v1/projects/india-tejidos/databases/'
       '(default)/documents/chalecos?pageSize=100&key=AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs')

# Qué pieza del catálogo muestra cada dibujo y cada cuello. Los nombres son los
# del panel de Bárbara: si sube una pieza mejor, se cambia acá y se corre de nuevo.
MAPA = {
    'liso':        {'redondo': 'Marrón'},
    'veteado':     {'redondo': 'Marrón Veteado', 'v': 'Otoño'},
    'trenza':      {'redondo': 'Trenzado Cafe',  'v': '3 Trenzadas'},
    'ochos':       {'redondo': 'Marrón con ochos', 'v': 'Gris trenza'},
    'guardapampa': {'v': 'Guarda pampa'},
    'rayado':      {'redondo': 'Rayado Tierra',  'v': 'Rayado Tierra'},
}
# Cuando dos cuellos apuntan al mismo nombre hay que desempatar por foto:
# "Rayado Tierra" está cargado dos veces, con cuello distinto cada vez.
DESEMPATE = {('rayado', 'redondo'): 1, ('rayado', 'v'): 0}
# De qué pieza sale la miniatura del dibujo. Por defecto, la primera; en el
# rayado la del cuello en v tiene las franjas mucho más marcadas.
MINI_CUELLO = {'rayado': 'v'}

ANCHO, ALTO = 640, 860
MINI = 190

# De dónde se saca la miniatura de cada dibujo, en fracciones del cuerpo de la
# pieza: (centro x, centro y, lado). El centro del pecho no sirve para todos —
# en el guardapampa la greca va en columnas al costado, y el rayado necesita
# alto para que entren dos franjas.
ZONA = {
    'liso':        (0.50, 0.52, 0.42),
    'veteado':     (0.50, 0.50, 0.55),
    'trenza':      (0.50, 0.50, 0.45),
    'ochos':       (0.50, 0.50, 0.45),
    'guardapampa': (0.27, 0.52, 0.42),
    'rayado':      (0.50, 0.50, 0.52),
}


def catalogo():
    with urllib.request.urlopen(API) as r:
        datos = json.load(io.TextIOWrapper(r, encoding='utf-8'))
    piezas = []
    for doc in datos.get('documents', []):
        f = doc['fields']
        g = lambda k: list(f.get(k, {}).values())[0] if k in f else ''
        piezas.append({'nombre': g('nombre'), 'estado': g('estado'), 'foto': g('foto')})
    return piezas


def bajar(url, ancho=900):
    """La foto con el fondo ya recortado por Cloudinary, igual que en la vidriera."""
    rec = url.replace('/image/upload/',
                      '/image/upload/e_background_removal/e_trim/f_png,q_auto,w_%d,c_limit/' % ancho)
    with urllib.request.urlopen(rec) as r:
        return Image.open(io.BytesIO(r.read())).convert('RGBA')


def limpiar(im):
    """Saca los restos sueltos del recorte, sin tocar la percha: colgado se ve
    mejor y es como se muestran las piezas en la vidriera."""
    a = np.array(im)
    solido = a[..., 3] > 60
    if not solido.any():
        return im
    etiquetas, cuantas = ndimage.label(solido)
    if cuantas > 1:
        tam = ndimage.sum(solido, etiquetas, range(1, cuantas + 1))
        principal = etiquetas == (int(np.argmax(tam)) + 1)
        a[~principal, 3] = 0
    fuera = Image.fromarray(a, 'RGBA')
    r, g, b, al = fuera.split()
    al = al.filter(ImageFilter.MinFilter(3))  # el hilo claro que deja el recorte
    return Image.merge('RGBA', (r, g, b, al))


def cuerpo(im):
    """Dónde empieza y termina el chaleco, sin contar la percha.

    Los hombros son la primera fila donde la pieza pasa la mitad de su ancho
    máximo. Se encuadra por el cuerpo, no por la imagen: así el chaleco queda
    siempre del mismo tamaño aunque una foto traiga más percha que otra.
    """
    a = np.array(im)
    solido = a[..., 3] > 60
    anchos = solido.sum(axis=1)
    filas = np.where(anchos > anchos.max() * 0.5)[0]
    y0 = filas[0] if len(filas) else 0
    y1 = filas[-1] if len(filas) else solido.shape[0] - 1
    cols = np.where(solido[y0:y1 + 1].any(axis=0))[0]
    x0, x1 = (cols[0], cols[-1]) if len(cols) else (0, solido.shape[1] - 1)
    return x0, y0, x1, y1


def encuadrar(im, ocupa=0.80, base=0.965):
    """Mismo alto de cuerpo y mismo pie para todas: al cambiar de dibujo la
    pieza no salta. Arriba queda aire para la percha."""
    im = limpiar(im)
    x0, y0, x1, y1 = cuerpo(im)
    escala = (ALTO * ocupa) / max(y1 - y0 + 1, 1)
    if (x1 - x0 + 1) * escala > ANCHO * 0.93:
        escala = (ANCHO * 0.93) / (x1 - x0 + 1)
    nueva = (max(1, int(im.width * escala)), max(1, int(im.height * escala)))
    im = im.resize(nueva, Image.LANCZOS)
    cx = (x0 + x1) / 2 * escala
    cy1 = y1 * escala
    lienzo = Image.new('RGBA', (ANCHO, ALTO), (0, 0, 0, 0))
    lienzo.paste(im, (int(ANCHO / 2 - cx), int(ALTO * base - cy1)), im)
    return lienzo


def a_gris(im):
    """Luminancia estirada + alfa. El color lo pone el navegador."""
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    a = np.array(im, dtype=np.float64)
    lum = a[..., :3] @ np.array([0.299, 0.587, 0.114])
    alpha = a[..., 3]
    m = alpha > 40
    if m.any():
        lo, hi = np.percentile(lum[m], 1.5), np.percentile(lum[m], 98.5)
        lum = np.clip((lum - lo) / max(hi - lo, 1.0), 0, 1) * 255
    g = lum.astype(np.uint8)
    return Image.fromarray(np.dstack([g, g, g, alpha.astype(np.uint8)]), 'RGBA')


def parche(gris, zona):
    """Un cuadrado del tejido para la miniatura, de donde se vea el dibujo."""
    cx_rel, cy_rel, lado_rel = zona
    a = np.array(gris)
    solido = a[..., 3] > 200
    ys = np.where(solido.any(axis=1))[0]
    xs = np.where(solido.any(axis=0))[0]
    if not len(ys) or not len(xs):
        return gris.crop((0, 0, MINI, MINI))

    alto = ys[-1] - ys[0]
    ancho = xs[-1] - xs[0]
    lado = int(min(ancho * lado_rel, alto * 0.34))
    cx = int(xs[0] + ancho * cx_rel)
    cy = int(ys[0] + alto * cy_rel)
    # Que no se salga de la pieza ni agarre el contorno
    cx = max(xs[0] + lado // 2 + 6, min(xs[-1] - lado // 2 - 6, cx))
    cy = max(ys[0] + lado // 2 + 6, min(ys[-1] - lado // 2 - 6, cy))
    caja = (cx - lado // 2, cy - lado // 2, cx - lado // 2 + lado, cy - lado // 2 + lado)
    return gris.crop(caja).resize((MINI, MINI), Image.LANCZOS)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    piezas = catalogo()
    por_nombre = {}
    for p in piezas:
        por_nombre.setdefault(p['nombre'], []).append(p)

    manifiesto = {}
    for dibujo, cuellos in MAPA.items():
        manifiesto[dibujo] = {}
        for cuello, nombre in cuellos.items():
            candidatos = por_nombre.get(nombre)
            if not candidatos:
                print('  falta en el catálogo:', nombre)
                continue
            elegido = candidatos[min(DESEMPATE.get((dibujo, cuello), 0), len(candidatos) - 1)]
            gris = a_gris(encuadrar(bajar(elegido['foto'])))
            arch = '%s-%s.webp' % (dibujo, cuello)
            gris.save(os.path.join(SALIDA, arch), 'WEBP', quality=76, method=6)
            manifiesto[dibujo][cuello] = arch
            print('%-14s %-8s <- %-22s %d KB' % (
                dibujo, cuello, nombre, os.path.getsize(os.path.join(SALIDA, arch)) // 1024))

            if cuello == MINI_CUELLO.get(dibujo, sorted(cuellos)[0]):
                mini = 'mini-%s.webp' % dibujo
                parche(gris, ZONA.get(dibujo, (0.5, 0.5, 0.45))).save(os.path.join(SALIDA, mini), 'WEBP', quality=88, method=6)
                manifiesto[dibujo]['mini'] = mini

    with io.open(os.path.join(SALIDA, 'piezas.json'), 'w', encoding='utf-8') as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=1)
    print('\nlisto ->', SALIDA)


if __name__ == '__main__':
    main()
