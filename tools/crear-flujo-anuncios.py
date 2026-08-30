# -*- coding: utf-8 -*-
"""Crea en n8n el flujo que trae los anuncios de Meta y los deja en Firestore.

Se corre UNA VEZ. Despues el flujo vive en n8n y se dispara solo todos los dias
a las 6:30. Para volver a crearlo hay que borrar el viejo primero, o quedan dos.

Uso:
    python tools/crear-flujo-anuncios.py            crea el flujo
    python tools/crear-flujo-anuncios.py --ver x.json   solo lo escribe, para mirarlo

Lee los secretos de dos archivos que NO estan en el repo:
    C:/Users/justo/bin/meta-ads/config.json   el token de Meta
    tools/credenciales.json                   el usuario del panel
y la credencial de n8n de C:/Users/justo/bin/n8n/config.json. Ninguno se imprime.


Copia el molde del flujo "Meta -> provincias", que ya hace ese mismo camino:
Meta -> Code -> entrar a Firebase con el usuario del panel -> PATCH a Firestore.
"""
import io, json, os, sys

sys.path.insert(0, r'C:/Users/justo/bin/n8n')
import n8n

R = r"c:/Users/justo/OneDrive/Escritorio/India"
META = json.load(io.open(r'C:/Users/justo/bin/meta-ads/config.json', encoding='utf-8'))
CRED = json.load(io.open(R + '/tools/credenciales.json', encoding='utf-8'))
API_KEY = "AIzaSyDuky-ihQRO2Lv-mGrXfxVvHSpUIp52Hcs"   # la misma clave publica de firebase-config.js
CUENTA = META['adAccountId']
VER = META['apiVersion']

CODIGO = r"""// De lo que devuelve Meta a un documento por anuncio en Firestore.
//
// Dos fuentes que hay que cruzar:
//   - /ads      -> el nombre y el estado (ACTIVE, PAUSED, ADSET_PAUSED...)
//   - /insights -> lo que gasto y cuanta gente escribio, en los ultimos 30 dias
// El insight NO trae el estado y la lista de anuncios NO trae el gasto, por eso van
// las dos y se juntan por ad_id.
//
// La charla nueva es `messaging_conversation_started_7d`: es la que cuenta a alguien
// que abrio una conversacion, no cada mensaje suelto. `total_messaging_connection`
// queda de respaldo por si en alguna ventana Meta no devuelve la primera.
const CHARLAS = ['onsite_conversion.messaging_conversation_started_7d',
                 'onsite_conversion.total_messaging_connection'];
const ahora = new Date().toISOString().replace(/\.\d+Z$/, 'Z');

const estados = {};
for (const it of $('Traer los anuncios').all()) {
  for (const a of (it.json.data || [])) estados[a.id] = a;
}

const filas = [];
for (const it of $input.all()) {
  for (const f of (it.json.data || [])) filas.push(f);
}

const salida = [];
const vistos = {};
for (const f of filas) {
  const id = f.ad_id; if (!id) continue;
  vistos[id] = true;
  const info = estados[id] || {};
  let charlas = 0;
  for (const tipo of CHARLAS) {
    const acc = (f.actions || []).find(a => a.action_type === tipo);
    if (acc) { charlas = Number(acc.value) || 0; break; }
  }
  const gasto = Math.round((Number(f.spend) || 0) * 100) / 100;
  salida.push({ json: {
    docId: id,
    nombre: info.name || f.ad_name || id,
    estado: info.effective_status || 'DESCONOCIDO',
    gasto: gasto,
    charlas: charlas,
    impresiones: Number(f.impressions) || 0,
    alcance: Number(f.reach) || 0,
    // Sin charlas no hay costo por charla: va 0 y la pantalla lo muestra como "—".
    costoCharla: charlas > 0 ? Math.round(gasto / charlas) : 0,
    actualizado: ahora,
  } });
}

// Los anuncios prendidos que todavia no gastaron nada no aparecen en el insight, y son
// justo los que hay que mirar: se agregan en cero para que se vean en el panel.
for (const a of Object.values(estados)) {
  if (a.effective_status === 'ACTIVE' && !vistos[a.id]) {
    salida.push({ json: {
      docId: a.id, nombre: a.name || a.id, estado: 'ACTIVE',
      gasto: 0, charlas: 0, impresiones: 0, alcance: 0, costoCharla: 0, actualizado: ahora,
    } });
  }
}

return salida;
"""

CAMPOS = ['nombre', 'estado', 'gasto', 'charlas', 'impresiones', 'alcance', 'costoCharla', 'actualizado']
MASK = '&'.join('updateMask.fieldPaths=' + c for c in CAMPOS)

CUERPO = ("={{ JSON.stringify({ fields: {"
          " nombre: { stringValue: $('Armar anuncios').item.json.nombre },"
          " estado: { stringValue: $('Armar anuncios').item.json.estado },"
          " gasto: { doubleValue: $('Armar anuncios').item.json.gasto },"
          " charlas: { integerValue: String($('Armar anuncios').item.json.charlas) },"
          " impresiones: { integerValue: String($('Armar anuncios').item.json.impresiones) },"
          " alcance: { integerValue: String($('Armar anuncios').item.json.alcance) },"
          " costoCharla: { doubleValue: $('Armar anuncios').item.json.costoCharla },"
          " actualizado: { timestampValue: $('Armar anuncios').item.json.actualizado }"
          " } }) }}")

nodos = [
    {"id": "n1", "name": "Todos los días a las 6:30", "type": "n8n-nodes-base.scheduleTrigger",
     "typeVersion": 1.2, "position": [-220, 300],
     "parameters": {"rule": {"interval": [{"field": "hours", "triggerAtHour": 6, "triggerAtMinute": 30}]}}},

    {"id": "n2", "name": "Configuración", "type": "n8n-nodes-base.set", "typeVersion": 3.4,
     "position": [0, 300],
     "notes": "El token de Meta es de usuario del sistema: no vence. El usuario es el mismo del panel.",
     "parameters": {"assignments": {"assignments": [
         {"id": "a1", "name": "metaToken", "value": META['accessToken'], "type": "string"},
         {"id": "a2", "name": "usuario", "value": CRED['usuario'] + "@india-admin.local", "type": "string"},
         {"id": "a3", "name": "password", "value": CRED['password'], "type": "string"},
     ]}, "options": {}}},

    {"id": "n3", "name": "Traer los anuncios", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [220, 300],
     "notes": "Nombre y estado de cada anuncio. El insight no trae el estado.",
     "parameters": {
         "url": "https://graph.facebook.com/%s/%s/ads" % (VER, CUENTA),
         "sendQuery": True,
         "queryParameters": {"parameters": [
             {"name": "fields", "value": "id,name,effective_status"},
             {"name": "limit", "value": "200"},
             {"name": "access_token", "value": "={{ $json.metaToken }}"},
         ]},
         "options": {}}},

    {"id": "n4", "name": "Traer el rendimiento", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [440, 300],
     "notes": "Gasto y charlas de los últimos 30 días, un renglón por anuncio.",
     "parameters": {
         "url": "https://graph.facebook.com/%s/%s/insights" % (VER, CUENTA),
         "sendQuery": True,
         "queryParameters": {"parameters": [
             {"name": "level", "value": "ad"},
             {"name": "fields", "value": "ad_id,ad_name,spend,impressions,reach,actions"},
             {"name": "date_preset", "value": "last_30d"},
             {"name": "limit", "value": "200"},
             {"name": "access_token", "value": "={{ $('Configuración').first().json.metaToken }}"},
         ]},
         "options": {}}},

    {"id": "n5", "name": "Armar anuncios", "type": "n8n-nodes-base.code", "typeVersion": 2,
     "position": [660, 300], "parameters": {"jsCode": CODIGO}},

    {"id": "n6", "name": "Entrar a Firebase", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [880, 300],
     "notes": "Un solo login para toda la tanda; el idToken dura una hora.",
     "parameters": {
         "method": "POST",
         "url": "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + API_KEY,
         "sendBody": True, "specifyBody": "json",
         "jsonBody": ("={{ JSON.stringify({ email: $('Configuración').first().json.usuario,"
                      " password: $('Configuración').first().json.password, returnSecureToken: true }) }}"),
         "executeOnce": True, "options": {}}},

    {"id": "n7", "name": "Guardar en Firestore", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [1100, 300],
     "notes": "PATCH por anuncio: pisa el documento anterior, no duplica.",
     "parameters": {
         "method": "PATCH",
         "url": ("={{ 'https://firestore.googleapis.com/v1/projects/india-tejidos/databases/(default)"
                 "/documents/anuncios/' + $('Armar anuncios').item.json.docId + '?%s' }}" % MASK),
         "sendHeaders": True,
         "headerParameters": {"parameters": [
             {"name": "Authorization", "value": "={{ 'Bearer ' + $('Entrar a Firebase').first().json.idToken }}"}]},
         "sendBody": True, "specifyBody": "json", "jsonBody": CUERPO,
         "options": {}}},
]

conex = {}
orden = [n["name"] for n in nodos]
for a, b in zip(orden, orden[1:]):
    conex[a] = {"main": [[{"node": b, "type": "main", "index": 0}]]}

wf = {"name": "Meta -> anuncios", "nodes": nodos, "connections": conex,
      "settings": {"executionOrder": "v1"}}

if "--ver" in sys.argv:
    io.open(sys.argv[sys.argv.index("--ver") + 1], "w", encoding="utf-8").write(
        json.dumps(wf, ensure_ascii=False, indent=1))
    print("guardado para revisar")
    sys.exit(0)

r = n8n.pedir('/workflows', 'POST', wf)
print(json.dumps({k: v for k, v in r.items() if k in ('id', 'name', 'active', 'ERROR', 'detalle')},
                 ensure_ascii=False))
