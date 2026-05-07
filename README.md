# India - Web + Admin

Página pública (`index.html`) y panel admin (`admin.html`) para que tu mamá gestione los chalecos. Conectado a **Firebase** (auth + base de datos) y **Cloudinary** (fotos). Deploy en Vercel.

---

## CHECKLIST RÁPIDO

1. [x] Firebase: proyecto creado
2. [x] Authentication activado y usuario `barbara123` creado
3. [ ] Firestore Database activado y reglas pegadas
4. [ ] Cloudinary: crear cuenta + upload preset (reemplaza a Firebase Storage)
5. [ ] Pegar las claves en `firebase-config.js`
6. [ ] Subir todo a Vercel
7. [ ] Probar: subir un chaleco desde admin y ver que aparece en la home

> **Importante**: Firebase ahora obliga a tener tarjeta de crédito (plan Blaze) para usar Storage. Por eso usamos **Cloudinary** para las fotos: 25 GB gratis, sin tarjeta, sin riesgo de que te cobren nada.

---

## 1) Firestore Database (si todavía no lo activaste)

1. Menú izquierdo en Firebase Console: **Compilación → Firestore Database**.
2. Clic en **"Crear base de datos"**.
3. Modo: **"Modo de producción"**.
4. Ubicación: **southamerica-east1** (São Paulo, lo más cerca de Argentina).
5. Una vez creada, andá a la pestaña **"Reglas"** y pegá esto:

```js
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /chalecos/{doc} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

6. Clic en **"Publicar"**.

---

## 2) Cloudinary (reemplaza a Firebase Storage)

### 2.1 Crear cuenta

1. Andá a https://cloudinary.com/users/register/free
2. Registrate con Google o email. **No te pide tarjeta.**
3. Cuando entrás al dashboard, en la parte de arriba vas a ver tu **Cloud Name** (algo como `dxy123abc`). **Anotalo**, lo necesitás después.

### 2.2 Crear el "Upload Preset" (esto autoriza al admin a subir fotos sin clave secreta)

1. En el dashboard, arriba a la derecha clic en el **engranaje ⚙ (Settings)**.
2. En el menú izquierdo elegí **"Upload"**.
3. Bajá hasta la sección **"Upload presets"** y clic en **"Add upload preset"**.
4. Configuralo así:
   - **Preset name**: ponele algo simple, ej. `india_unsigned` (anotalo).
   - **Signing Mode**: cambialo a **Unsigned** (importante).
   - **Folder** (opcional): podés poner `chalecos` para que todo quede ordenado.
5. Clic en **"Save"** arriba a la derecha.

### 2.3 (Opcional pero recomendado) Limitar qué se puede subir

Mientras estás editando el preset, abajo de todo activá:
- **Max file size**: ej. `5000000` (5 MB) → así nadie puede llenarte el storage.
- **Allowed formats**: `jpg, jpeg, png, webp`.

Esto previene abusos si alguien descubre el preset (no es secreto, va en el JS).

---

## 3) Pegar TODAS las claves en `firebase-config.js`

Abrí `firebase-config.js` y completá:

```js
export const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};

export const cloudinaryConfig = {
  cloudName: "TU_CLOUD_NAME",        // del paso 2.1
  uploadPreset: "india_unsigned"      // el nombre que pusiste en 2.2
};
```

### ¿Dónde están las claves de Firebase?

1. En Firebase Console, arriba a la izquierda clic en el ⚙️ → **"Configuración del proyecto"**.
2. Bajá hasta **"Tus apps"** → clic en el ícono web `</>`.
3. Apodo: `india-web`. **NO marcar** "Configurar Firebase Hosting".
4. **"Registrar app"** → te muestra el bloque con las claves. Copiá los valores.

---

## 4) Subir a Vercel

### Opción simple (sin GitHub)

1. Entrá a https://vercel.com → registrarse con Google.
2. **"Add New... → Project"**.
3. Si no querés conectar GitHub, instalá la CLI:

```bash
npm install -g vercel
cd india-web
vercel
# Seguí las preguntas. La primera vez te pide login.
# Para producción:
vercel --prod
```

Te da una URL tipo `https://india-tejidos.vercel.app`. Esa es la pública.
El admin está en `https://india-tejidos.vercel.app/admin.html`.

---

## 5) Probar todo

1. Andá a `tu-url.vercel.app/admin.html`.
2. Login: `barbara123` + tu contraseña.
3. Clic en **"Agregar chaleco"** → subir foto, nombre, descripción → Guardar.
4. Abrí en otra pestaña `tu-url.vercel.app` → tendría que aparecer el chaleco.

---

## CÓMO USA TU MAMÁ EL ADMIN

- **Disponibles**: lo que está a la venta. Aparece en la página principal.
- **Vendidos / Hechos**: portfolio de trabajos pasados. Aparece más abajo en la página.
- Puede mover entre las dos listas con un clic, editar nombre/foto/descripción, o borrar.

## CÓMO LO USA EL CLIENTE

- Entra a la URL pública.
- Ve los chalecos disponibles arriba.
- Más abajo ve "Trabajos anteriores" como portfolio.
- Botón verde de WhatsApp en cada uno con mensaje pre-cargado del nombre del chaleco.

---

## COSTO TOTAL

- **Firebase** (Spark plan): gratis. Solo usamos Auth + Firestore (no Storage). Sin tarjeta.
- **Cloudinary** (Free plan): 25 GB de fotos + 25 GB de tráfico/mes. Sin tarjeta.
- **Vercel** (Hobby): gratis ilimitado para proyectos personales.

Para el volumen de tu mamá: **cero pesos por mes, sin tarjeta de crédito en ningún lado**.

---

## SI ALGO NO ANDA

- **"Permission denied"** al guardar → revisá las reglas de Firestore.
- **La foto no sube / "Upload preset must be specified"** → revisá que `cloudinaryConfig` esté bien pegado y que el preset esté en modo **Unsigned**.
- **El admin se queda en blanco** → abrí F12 (consola del navegador) y mirá errores. Lo más común es que `firebase-config.js` esté mal pegado.
- **No aparecen los chalecos en la página pública** → mirá en Firestore Console que existan los documentos en la colección `chalecos`.

## NOTA SOBRE EL BORRADO DE FOTOS

Cuando borrás un chaleco, el dato se borra de Firestore (deja de aparecer) pero la foto queda guardada en Cloudinary. No es problema: tenés 25 GB. Si alguna vez querés limpiar fotos viejas, entrás al dashboard de Cloudinary → **Media Library** y las borrás a mano.

Cualquier cosa, me decís.
