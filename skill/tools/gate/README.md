# Password gate for a Cloudflare Pages site

Publishes a static site (a prototype, a review page, a video) on Cloudflare Pages behind one shared password.
Every request, video and audio included, goes through `_worker.js`:

- without the password, pages show a sign-in form and everything else gets 401;
- a correct password sets an HttpOnly cookie for 30 days; a wrong one shows an error;
- `/__leave` signs out; `/robots.txt` disallows everything and every response carries `x-robots-tag: noindex, nofollow`;
- HTML is never cached (signing out or changing the password takes effect at once); media is cached privately;
- video and audio answer byte-range requests with 206, so seeking works and Safari plays them.

The password is stored only as the Pages secret `SITE_PASSWORD`. It is never in these files.
Pages allows at most 25 MiB per file; `build.sh` warns about anything over 24 MB.

## Files

| File | What it does |
|---|---|
| `_worker.js` | the gate (Pages advanced mode) |
| `build.sh [SRC]` | copies the site (default `../dist`) into `site/` and adds the gate |
| `deploy.sh PROJECT [SRC]` | builds, then `wrangler pages deploy` to the project's `main` branch |
| `test_gate.py` | checks the gate against a local server |

## First time (the site owner does these steps)

Run from this folder. Node.js is needed for `npx`.

1. `npm install` (installs wrangler locally)
2. `npx wrangler login` (opens the browser to sign in to Cloudflare)
3. `npx wrangler pages project create <name> --production-branch main`
4. `npx wrangler pages secret put SITE_PASSWORD --project-name <name>` and type the password when asked
5. `./deploy.sh <name>` and the site is at `https://<name>.pages.dev`

Optional: set a plain variable `SITE_TITLE` on the project to name the site on the sign-in page.

## After changing the site

Rebuild it into `../dist` (or pass its folder), then `./deploy.sh <name> [SRC]`.

## Changing the password

Repeat step 4, then `./deploy.sh <name>`. Everyone is signed out.

## Testing locally

No Cloudflare account is needed.

1. Create `.dev.vars` in this folder with one line, `SITE_PASSWORD=<a test password>` (it is git-ignored).
2. `./build.sh [SRC]`
3. `npx wrangler pages dev site --port 8788 --ip 127.0.0.1`
4. In another terminal: `uv run --with playwright python test_gate.py` (add `--media /path.mp4` to pick the file
   used for the range check).

After changing `_worker.js`, run `./build.sh` again and restart `wrangler pages dev`; it does not pick up the change.
