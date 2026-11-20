# Real footage (Creative Commons)

Real clips ground an explainer: the actual place, the actual machine, archive film of the event.

```bash
vg footage search "minots ledge lighthouse storm" --limit 8      # YouTube, Creative Commons filter on
vg footage get <url> -o clips/s05-archive --start 42 --end 49     # cuts just that section
```

`get` appends the URL, title, author and licence to `credits.json`.

## Licence rules

- **CC BY** (what YouTube's filter returns): usable with attribution. Credit every clip in the
  video's description or an end card: "<title>" by <author>, CC BY, <url>.
- A licence field saying anything else, or missing: don't use the clip without asking the user.
- YouTube's filter trusts the uploader. Reuploads of TV broadcasts or films marked CC are
  still not free to use. Skip anything that looks like someone else's production.
- Keep excerpts short (a few seconds per shot) and use them for what they show, not as the
  video's backbone.

## When YouTube asks you to sign in

YouTube bot-checks datacenter IPs. Search still works; per-video metadata
and downloads fail with "Sign in to confirm you're not a bot", and `search` shows the licence as
`UNCONFIRMED`. The fix is a Netscape-format cookies file at `~/video-gen/.youtube-cookies.txt`
(gitignored), exported from a browser logged into a throwaway Google account; `vg` passes it to
yt-dlp automatically. Without it, ask the user to export one, or use the sources below.

## Other sources that don't need cookies

- **Wikimedia Commons** (commons.wikimedia.org): every file page states its licence; download
  the original with `curl -L`. Much public-domain archive film.
- **Internet Archive** (archive.org): `yt-dlp <item url>` works; check the item's licence field.
- **NASA, NOAA, US government footage**: public domain; the page says so.

Trim and conform downloaded files with `vg assemble` like any other clip (`in:` and `dur:` in
`edit.yaml`), so there is no separate transcoding step.
