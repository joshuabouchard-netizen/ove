// One tokens object per brand direction. mockups.html and board.html both read this file, so a change here
// carries through every asset. Replace the placeholders; `mark` and `photo` are optional image paths
// (relative to this folder). Without them, a simple SVG mark and a colour-field "photo" stand in.
// `ground` should be the sampled background colour of the mark image, so the image edge disappears.
window.BRAND = {
  name: "{BRAND}",
  sub: "by {PRACTITIONER}",
  tagline: "{TAGLINE}",
  contact: ["{ADDRESS LINE}", "{EMAIL OR PHONE}", "{WEBSITE}"],
};
window.DIRECTIONS = {
  1: { title: "Engraved", ground: "#F6EFE0", ink: "#2E2A24", accent: "#A8823C", dark: "#2E2A24", onDark: "#F6EFE0",
       display: "Cormorant Garamond", displayWeight: 500, body: "EB Garamond", bodyWeight: 400,
       swatches: [["Parchment", "#F6EFE0"], ["Ink", "#2E2A24"], ["Antique gold", "#A8823C"], ["Sage", "#9AA58A"]],
       style: "Fine-line engraving, like an old botanical plate.", feel: "Heritage, careful, quiet.",
       watch: "Can read old-fashioned; the fine lines fill in at small sizes.", mark: null, photo: null, shape: "leaf" },
  2: { title: "Monoline", ground: "#FAFAF7", ink: "#1F2A2A", accent: "#5E8C7A", dark: "#1F2A2A", onDark: "#FAFAF7",
       display: "Jost", displayWeight: 300, body: "Jost", bodyWeight: 400,
       swatches: [["Chalk", "#FAFAF7"], ["Slate", "#1F2A2A"], ["Eucalyptus", "#5E8C7A"], ["Stone", "#CFCBC2"]],
       style: "One continuous thin line, uniform weight.", feel: "Calm, clinical in a good way.",
       watch: "Generic if the line drawing isn't distinctive.", mark: null, photo: null, shape: "ring" },
  3: { title: "Editorial", ground: "#E9F06A", ink: "#151515", accent: "#E4572E", dark: "#151515", onDark: "#E9F06A",
       display: "Bricolage Grotesque", displayWeight: 800, body: "DM Mono", bodyWeight: 400,
       swatches: [["Chartreuse", "#E9F06A"], ["Black", "#151515"], ["Signal", "#E4572E"], ["Paper", "#F4F1EA"]],
       style: "Fashion-editorial: flash, hard shadows, bold type.", feel: "Confident, current, a little loud.",
       watch: "Polarising; check it suits the people who will walk in.", mark: null, photo: null, shape: "dots" },
};
window.FONT_URL = (d) => "https://fonts.googleapis.com/css2?family=" +
  [...new Set([d.display, d.body])].map((f) => f.replace(/ /g, "+") + ":ital,wght@0,300..800;1,300..800").join("&family=") + "&display=block";
window.SVG_MARK = (d, size) => {
  const s = size, c = d.accent, k = d.ink;
  if (d.shape === "ring") return `<svg width="${s}" height="${s}" viewBox="0 0 100 100"><circle cx="50" cy="50" r="34" fill="none" stroke="${k}" stroke-width="2.2"/><path d="M50 16 C70 34 70 66 50 84 C30 66 30 34 50 16Z" fill="none" stroke="${c}" stroke-width="2.2"/></svg>`;
  if (d.shape === "dots") { let g = ""; for (let y = 0; y < 7; y++) for (let x = 0; x < 7; x++) { const r = 4.2 * Math.exp(-((x - 3) ** 2 + (y - 3) ** 2) / 9); g += `<circle cx="${14 + x * 12}" cy="${14 + y * 12}" r="${r.toFixed(2)}" fill="${x === 3 && y === 3 ? c : k}"/>`; } return `<svg width="${s}" height="${s}" viewBox="0 0 100 100">${g}</svg>`; }
  return `<svg width="${s}" height="${s}" viewBox="0 0 100 100"><path d="M50 12 C78 30 80 66 50 90 C20 66 22 30 50 12Z" fill="none" stroke="${k}" stroke-width="1.6"/><path d="M50 18 L50 88" stroke="${c}" stroke-width="1.6"/>${[30,42,54,66].map(y=>`<path d="M50 ${y} L${64-y/8} ${y-8} M50 ${y} L${36+y/8} ${y-8}" stroke="${k}" stroke-width="1"/>`).join("")}</svg>`;
};
