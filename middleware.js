import { next } from '@vercel/functions';

// Candado SOLO para la herramienta interna /carga.
// El resto del sitio publico (/, /admin, etc.) queda sin tocar.
export const config = {
  matcher: ['/carga', '/carga/:path*'],
};

const REALM = 'India Tejidos - Carga';

function pedirClave(msg) {
  return new Response(msg, {
    status: 401,
    headers: {
      'WWW-Authenticate': `Basic realm="${REALM}", charset="UTF-8"`,
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}

export default function middleware(request) {
  // Usuario y clave viven como variables de entorno en Vercel, no en el repo.
  const USER = process.env.CARGA_USER || 'barbara';
  const PASS = process.env.CARGA_PASSWORD;

  // Fail-safe: si todavia no se configuro la clave en Vercel, queda CERRADO.
  if (!PASS) {
    return pedirClave('Falta configurar la clave (CARGA_PASSWORD) en Vercel.');
  }

  const header = request.headers.get('authorization') || '';
  if (header.startsWith('Basic ')) {
    let decoded = '';
    try {
      decoded = atob(header.slice(6));
    } catch (e) {
      decoded = '';
    }
    const sep = decoded.indexOf(':');
    const user = sep >= 0 ? decoded.slice(0, sep) : '';
    const pass = sep >= 0 ? decoded.slice(sep + 1) : '';
    if (user === USER && pass === PASS) {
      return next(); // clave correcta -> sirve la pagina
    }
  }

  return pedirClave('Acceso restringido. Ingresa usuario y clave.');
}
