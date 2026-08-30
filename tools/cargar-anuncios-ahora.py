# -*- coding: utf-8 -*-
"""Trae los anuncios de Meta y los deja en Firestore, ahora mismo.

Es lo mismo que hace el flujo `Meta -> anuncios` de n8n todos los dias a las 6:30.
Este script esta para dos cosas: la primera carga (para no esperar al otro dia) y
para forzar una actualizacion cuando se acaba de cambiar algo en el administrador
de Meta y se quiere ver reflejado ya.

Uso:
    python tools/cargar-anuncios-ahora.py

Lee los secretos de afuera del repo y no los imprime:
    C:/Users/justo/bin/meta-ads/config.json   el token de Meta
    tools/credenciales.json                   el usuario del panel
"""
import io, json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
META = json.load(io.open(r'C:/Users/justo/bin/meta-ads/config.json', encoding='utf-8'))
CRED = json.load(io.open(os.path.join(RAIZ, 'tools', 'credenciales.json'), encoding='utf-8'))
API_KEY = "AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs"   # la misma clave publica de firebase-config.js
PROY = "india-tejidos"

# Las mismas dos que usa el nodo Code del flujo. La primera cuenta a alguien que
# abrio una conversacion; la segunda es el respaldo por si Meta no devuelve aquella.
CHARLAS = ['onsite_conversion.messaging_conversation_started_7d',
           'onsite_conversion.total_messaging_connection']


def graph(ruta, **p):
    p['access_token'] = META['accessToken']
    url = 'https://graph.facebook.com/%s%s?%s' % (META['apiVersion'], ruta, urllib.parse.urlencode(p))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def post(url, cuerpo, cabeceras=None, metodo='POST'):
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode('utf-8'), method=metodo)
    req.add_header('Content-Type', 'application/json')
    for k, v in (cabeceras or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or '{}')


def main():
    cuenta = META['adAccountId']
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

    estados = {a['id']: a for a in graph('/%s/ads' % cuenta,
               fields='id,name,effective_status', limit=200).get('data', [])}
    filas = graph('/%s/insights' % cuenta, level='ad', date_preset='last_30d',
                  fields='ad_id,ad_name,spend,impressions,reach,actions',
                  limit=200).get('data', [])
    print('Meta: %d anuncios en la cuenta, %d con movimiento en 30 dias' % (len(estados), len(filas)))

    docs, vistos = [], set()
    for f in filas:
        ad = f.get('ad_id')
        if not ad:
            continue
        vistos.add(ad)
        info = estados.get(ad, {})
        charlas = 0
        for tipo in CHARLAS:
            acc = next((a for a in f.get('actions', []) if a.get('action_type') == tipo), None)
            if acc:
                charlas = int(float(acc.get('value') or 0))
                break
        gasto = round(float(f.get('spend') or 0), 2)
        docs.append({
            'docId': ad,
            'nombre': info.get('name') or f.get('ad_name') or ad,
            'estado': info.get('effective_status') or 'DESCONOCIDO',
            'gasto': gasto, 'charlas': charlas,
            'impresiones': int(f.get('impressions') or 0),
            'alcance': int(f.get('reach') or 0),
            'costoCharla': round(gasto / charlas) if charlas else 0,
            'actualizado': ahora,
        })
    # Los prendidos que todavia no gastaron no vienen en el insight, y son justo
    # los que hay que mirar: se agregan en cero.
    for a in estados.values():
        if a.get('effective_status') == 'ACTIVE' and a['id'] not in vistos:
            docs.append({'docId': a['id'], 'nombre': a.get('name') or a['id'], 'estado': 'ACTIVE',
                         'gasto': 0, 'charlas': 0, 'impresiones': 0, 'alcance': 0,
                         'costoCharla': 0, 'actualizado': ahora})

    if not docs:
        print('No hay nada para escribir.')
        return

    tok = post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=' + API_KEY,
               {'email': CRED['usuario'] + '@india-admin.local',
                'password': CRED['password'], 'returnSecureToken': True})['idToken']

    campos = ['nombre', 'estado', 'gasto', 'charlas', 'impresiones', 'alcance', 'costoCharla', 'actualizado']
    mask = '&'.join('updateMask.fieldPaths=' + c for c in campos)
    base = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/anuncios/' % PROY

    ok = 0
    for d in sorted(docs, key=lambda x: -x['gasto']):
        cuerpo = {'fields': {
            'nombre': {'stringValue': d['nombre']},
            'estado': {'stringValue': d['estado']},
            'gasto': {'doubleValue': d['gasto']},
            'charlas': {'integerValue': str(d['charlas'])},
            'impresiones': {'integerValue': str(d['impresiones'])},
            'alcance': {'integerValue': str(d['alcance'])},
            'costoCharla': {'doubleValue': d['costoCharla']},
            'actualizado': {'timestampValue': d['actualizado']},
        }}
        try:
            post(base + d['docId'] + '?' + mask, cuerpo, {'Authorization': 'Bearer ' + tok}, 'PATCH')
            ok += 1
            marca = 'ANDANDO' if d['estado'] == 'ACTIVE' else 'parado '
            print('  %s  $%-10s %3s charlas  %s' % (marca, format(int(d['gasto']), ',d').replace(',', '.'),
                                                    d['charlas'] or '-', d['nombre'][:42]))
        except urllib.error.HTTPError as e:
            print('  ERROR al guardar %s: %s %s' % (d['nombre'][:30], e.code,
                                                    e.read().decode('utf-8', 'replace')[:200]))
    print('\nGuardados %d de %d anuncios en Firestore.' % (ok, len(docs)))


if __name__ == '__main__':
    sys.exit(main())
