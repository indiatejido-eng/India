# Directivas para Claude (y cualquier agente IA) en India Tejidos

> Este archivo manda. Si una instrucción del chat contradice algo de acá sin justificar el cambio, preguntá antes de romper la regla.

## Contexto

- **Quién dirige:** Justo (18, Concordia, Entre Ríos). Hablale en español rioplatense con voseo, sin formalismos, directo al grano. Si ves un enfoque mejor, decílo — no le des la razón solo para agradar.
- **Para quién es el sitio:** Bárbara (mamá de Justo). Teje chalecos de lana hilada a mano, artesanales, hechos a medida según las medidas de cada cliente. Bárbara no toca código — el panel `admin.html` es para que ella sola gestione el catálogo.
- **Qué es el sitio:** vidriera digital + panel de catálogo. Compradores llegan por WhatsApp.

## Stack y arquitectura

- **Hosting:** Vercel, autodeploy en cada push a `main`. ~30s para republicar.
- **Repo:** https://github.com/indiatejido-eng/India
- **URL pública:** https://india-tejidos.vercel.app
- **Auth:** Firebase Authentication. Usuario único `barbara123@india-admin.local`. La UI acepta `barbara123` y concatena el dominio internamente.
- **DB:** Firestore, proyecto `india-tejidos`, región `southamerica-east1`, colección `chalecos`.
- **Storage imágenes:** Cloudinary (NO Firebase Storage). Cloud `dgl2mizsf`, upload preset unsigned `india_unsigned`. Subida directa desde el navegador.
- **Sin backend propio.** HTML + JS estático puro servido por Vercel.

## Estructura del repo

- `index.html` — página pública. Lee chalecos de Firestore en tiempo real. Dos secciones: "Disponibles" (estado=disponible) y "Trabajos anteriores" (estado=anterior).
- `admin.html` — panel de Bárbara. Login → dos pestañas. CRUD completo + subida de fotos a Cloudinary.
- `firebase-config.js` — exporta `firebaseConfig` y `cloudinaryConfig`.
- `README.md` — setup ya aplicado.

## Modelo de datos

Colección `chalecos`, cada doc:

| campo | tipo | nota |
|---|---|---|
| `nombre` | string | |
| `desc` | string | |
| `foto` | string | URL pública de Cloudinary |
| `fotoPath` | string | public_id de Cloudinary |
| `estado` | string | `"disponible"` o `"anterior"` |
| `orden` | number | timestamp para ordenar |
| `creadoEn` | timestamp | serverTimestamp |
| `actualizadoEn` | timestamp | serverTimestamp |

**Reglas Firestore:** lectura pública, escritura solo con `request.auth != null` sobre `chalecos/{doc}`.

## Workflow que quiero

1. Justo pide cambios en lenguaje natural.
2. Vos editás → `git add` → `git commit` con mensaje claro en español imperativo → `git push origin main`.
3. Vercel republica solo. Justo refresca y ve el cambio.

**Reglas del workflow:**

- Mensajes de commit en español, descriptivos, en imperativo: `fix: ...`, `feat: ...`, `refactor: ...`.
- Cambios de UX/diseño: 1-2 oraciones de qué vas a hacer, después ejecutás.
- Bugfix o cambio chico: ejecutás directo y reportás en 1-2 líneas qué hiciste.
- **Cuando arregles un bug, buscá si el mismo patrón existe en otros archivos del proyecto y arreglalo en TODOS los lugares en un solo commit.** No hacer que Justo pida el mismo fix dos veces. (Caso fundacional: el fix de `where + orderBy` en `admin.html` también aplicaba a `index.html` y debió ir junto.)

## Diseño → usar Google Stitch (MCP)

- **Para TODO trabajo de diseño/UI** (rediseñar una página, un componente, el layout, la estética, una landing nueva) **consultá SIEMPRE primero el MCP de Google Stitch.** Es la herramienta de diseño del proyecto — generá el diseño ahí antes de maquetar a mano.
- **Adaptá su output al stack:** Stitch suele devolver React/Tailwind, y acá va **HTML + JS estático puro, sin frameworks** (ver Reglas duras). Portealo a vanilla respetando la estética (Fraunces, crema/marrón) y sin romper Firebase/Cloudinary. **NUNCA pegar el código de Stitch tal cual si trae frameworks o build.**
- El MCP `stitch` se carga al arrancar Claude Code. Si no aparece en tus tools, decile a Justo que reinicie — no asumas que no existe.

## Reglas duras (NO negociables sin pedido explícito)

- **NUNCA tocar `firebase-config.js`.** Las claves reales ya están bien configuradas.
- **NUNCA hardcodear claves nuevas.** Si necesitás un valor de configuración, pedíselo a Justo.
- **NUNCA agregar frameworks pesados** (React, Vue, Next, Svelte, etc.). El sitio es HTML+JS estático puro y debe seguir así.
- **Mantener la estética actual:** paleta beige/marrón, tipografía serif (Fraunces), tagline "Lana, agujas y tiempo".

## Lo que NO quiero

- "Deberías hacer X" sin hacerlo. Si tenés permiso para ejecutar, ejecutá.
- Pedir confirmación para cosas obvias.
- Explicaciones largas. Resumen de 2-3 líneas y ejecución.
- Cambios en `firebase-config.js`.
