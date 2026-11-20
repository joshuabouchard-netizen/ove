/* A shared-password gate in front of a whole Cloudflare Pages site (advanced mode: this file is site/_worker.js).
   Every request, media included, needs the cookie a correct password sets. The password lives only in the
   Pages secret SITE_PASSWORD (locally: .dev.vars). Changing it, or SALT below, signs everyone out.
   Optional plain variable SITE_TITLE names the site on the sign-in page. /__leave signs out. */
const COOKIE = 'site_pass', SALT = 'pages-gate', DAYS = 30, enc = new TextEncoder();
const NOINDEX = 'noindex, nofollow';

async function tokenFor(pw) {
  const h = await crypto.subtle.digest('SHA-256', enc.encode(`${SALT}:v1:${pw}`));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('');
}
function sameToken(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function cookieToken(req) {
  const m = (req.headers.get('Cookie') || '').match(new RegExp(`(?:^|;\\s*)${COOKIE}=([a-f0-9]{64})`));
  return m ? m[1] : null;
}
const safePath = p => (typeof p === 'string' && p.startsWith('/') && !p.startsWith('//')) ? p : '/';
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const reply = (body, status, headers = {}) =>
  new Response(body, { status, headers: { 'cache-control': 'no-store', 'x-robots-tag': NOINDEX, ...headers } });
const cookie = (value, age) => `${COOKIE}=${value}; Path=/; Max-Age=${age}; HttpOnly; Secure; SameSite=Lax`;

function loginPage(env, to, wrong) {
  const html = LOGIN.replaceAll('{{TITLE}}', esc(env.SITE_TITLE || 'Private preview')).replace('{{TO}}', esc(safePath(to)))
    .replace('{{ERR}}', wrong ? '<p class="err" role="alert">That password did not work. Try again.</p>' : '');
  return reply(html, wrong ? 401 : 200, { 'content-type': 'text/html; charset=utf-8' });
}

function rangeResponse(buf, type, range) {
  const n = buf.byteLength, m = range.match(/^bytes=(\d*)-(\d*)$/);
  let a = m && m[1] !== '' ? +m[1] : null, z = m && m[2] !== '' ? +m[2] : null;
  if (a === null && z !== null) { a = Math.max(0, n - z); z = n - 1; } else { a = a ?? 0; z = Math.min(z ?? n - 1, n - 1); }
  if (!m || (m[1] === '' && m[2] === '') || a > z || a >= n) return reply(null, 416, { 'content-range': `bytes */${n}` });
  return reply(buf.slice(a, z + 1), 206, { 'content-type': type, 'content-range': `bytes ${a}-${z}/${n}`,
    'content-length': String(z - a + 1), 'accept-ranges': 'bytes', 'cache-control': 'private, max-age=3600' });
}

export default {
  async fetch(req, env) {
    if (!env.SITE_PASSWORD) return reply('This site is not configured yet.', 503);
    const url = new URL(req.url), good = await tokenFor(env.SITE_PASSWORD);

    if (url.pathname === '/robots.txt') return reply('User-agent: *\nDisallow: /\n', 200, { 'content-type': 'text/plain' });
    if (url.pathname === '/__leave') return reply(null, 303, { location: '/', 'set-cookie': cookie('', 0) });
    if (url.pathname === '/__enter' && req.method === 'POST') {
      const form = await req.formData(), to = safePath(String(form.get('to') || '/'));
      if (sameToken(await tokenFor(String(form.get('password') || '')), good))
        return reply(null, 303, { location: to, 'set-cookie': cookie(good, DAYS * 86400) });
      await new Promise(r => setTimeout(r, 900));
      return loginPage(env, to, true);
    }
    if (!sameToken(cookieToken(req), good)) {
      if (req.method === 'GET' && (req.headers.get('accept') || '').includes('text/html'))
        return loginPage(env, url.pathname + url.search, false);
      return reply('Password required', 401, { 'content-type': 'text/plain' });
    }

    const res = await env.ASSETS.fetch(req), type = res.headers.get('content-type') || '', range = req.headers.get('range');
    if (range && res.status === 200 && /^(video|audio)\//.test(type)) return rangeResponse(await res.arrayBuffer(), type, range);
    const out = new Response(res.body, res);
    out.headers.set('x-robots-tag', NOINDEX);
    out.headers.set('cache-control', type.includes('text/html') ? 'no-store' : 'private, max-age=3600');
    if (/^(video|audio)\//.test(type)) out.headers.set('accept-ranges', 'bytes');
    return out;
  },
};

const LOGIN = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">
<title>{{TITLE}}</title><style>
:root{color-scheme:light dark;--bg:#f6f6f4;--fg:#1d1d1f;--mute:#6b6b70;--line:#d4d4d8;--field:#fff;--btn:#1d1d1f;--btnfg:#fff;--err:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#ececee;--mute:#9a9aa1;--line:#3a3a40;--field:#1f1f23;--btn:#ececee;--btnfg:#161618;--err:#f97066}}
*{box-sizing:border-box;margin:0}
html,body{height:100%}
body{display:flex;align-items:center;justify-content:center;padding:24px 16px;background:var(--bg);color:var(--fg);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{width:min(380px,100%)}
h1{font-size:22px;font-weight:600;margin-bottom:6px}
p.l{color:var(--mute);font-size:15px;margin-bottom:22px}
form{display:flex;gap:8px}
input{flex:1;min-width:0;padding:12px 14px;font:inherit;color:var(--fg);background:var(--field);border:1px solid var(--line);border-radius:10px}
input:focus{outline:2px solid var(--fg);outline-offset:1px}
button{padding:0 18px;font:inherit;font-weight:600;color:var(--btnfg);background:var(--btn);border:0;border-radius:10px;cursor:pointer}
.err{color:var(--err);font-size:14px;margin-top:12px}
</style></head><body><main><h1>{{TITLE}}</h1><p class="l">This site is private. Enter the password you were given.</p>
<form method="post" action="/__enter"><input type="hidden" name="to" value="{{TO}}">
<input type="password" name="password" placeholder="Password" autocomplete="current-password" autofocus required aria-label="Password">
<button type="submit">Enter</button></form>{{ERR}}</main></body></html>`;
