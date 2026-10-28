// This file is the only place React makes HTTP requests.
// Vite forwards /api to port 8000, so cookies work on the same site.
const ROOT = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

// A shared helper saves repeated fetch and error-handling code.
async function request(path, method = 'GET', body = null) {
  // Cookies contain our session; JavaScript never reads access tokens.
  const options = { method, credentials: 'include' };
  // FormData manages its own multipart boundary; don't add Content-Type.
  if (body instanceof FormData) options.body = body;
  // JSON is only used for simple signup/login credentials.
  else if (body) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  // A network failure is different from an API validation failure.
  let response;
  try { response = await fetch(ROOT + path, options); }
  catch { throw new Error('Cannot reach the FastAPI backend on port 8000.'); }
  // Parse JSON even on errors, so the user sees a readable message.
  const data = await response.json().catch(() => ({}));
  // FastAPI errors may be a string or an array of validation details.
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === 'string' ? detail :
      Array.isArray(detail) ? detail.map(item => item.msg || 'Invalid input').join(', ') :
      `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

// Each API method maps directly to a documented FastAPI route.
export const api = {
  health: () => request('/api/health'),
  signup: (form) => request('/api/auth/signup', 'POST', form),
  login: (form) => request('/api/auth/login', 'POST', form),
  me: () => request('/api/auth/me'),
  logout: () => request('/api/auth/logout', 'POST'),
  styles: () => request('/api/styles'),
  creations: () => request('/api/creations'),
  // Everything goes in one multipart request. No separate upload/queue flow.
  create: (file, settings) => {
    const form = new FormData();
    form.append('image', file);
    form.append('options', JSON.stringify(settings));
    return request('/api/creations', 'POST', form);
  },
};

// URLs from ImageKit are already public HTTPS URLs.
export const imageUrl = (url) => url || '';

// ImageKit can create preview crops without another paid AI generation.
export function transformUrl(url, width, height) {
  if (!url) return '';
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}tr=w-${width},h-${height},fo-auto`;
}
