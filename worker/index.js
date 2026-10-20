// Xpress Bygg site worker.
// Static pages are served straight from the assets; only /api/* reaches this code.
//
// Settings it reads from Cloudflare (Worker > Settings > Variables and Secrets):
//   QUOTE_TO          (secret, required)  inbox that receives quote requests
//   QUOTE_FROM        (optional)          sender address, must be on xpressbygg.com
//   TURNSTILE_SITEKEY (optional)          public Turnstile key; turns the human check on
//   TURNSTILE_SECRET  (secret, optional)  private Turnstile key
// Bindings (wrangler.jsonc): ASSETS, QUOTE_MAIL (send_email), QUOTE_LIMIT (rate limit)

import { EmailMessage } from "cloudflare:email";

const MAX_PHOTOS = 8;
const MAX_PHOTO_BYTES = 3 * 1024 * 1024;   // per photo, after browser resizing
const MAX_TOTAL_BYTES = 14 * 1024 * 1024;  // all photos together
const MIN_FILL_MS = 4000;                  // humans need longer than this

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/quote-config") {
      return json({ turnstileSiteKey: env.TURNSTILE_SECRET ? (env.TURNSTILE_SITEKEY || null) : null });
    }

    if (url.pathname === "/api/quote") {
      if (request.method !== "POST") return json({ ok: false, error: "method" }, 405);
      try {
        return await handleQuote(request, env);
      } catch (err) {
        console.error("quote failed", err && err.stack || err);
        return json({ ok: false, error: "server" }, 500);
      }
    }

    return env.ASSETS.fetch(request);
  },
};

async function handleQuote(request, env) {
  if (!env.QUOTE_TO || !env.QUOTE_MAIL) {
    console.error("quote form not configured: QUOTE_TO secret or QUOTE_MAIL binding missing");
    return json({ ok: false, error: "config" }, 503);
  }

  const len = Number(request.headers.get("content-length") || 0);
  if (len > MAX_TOTAL_BYTES + 512 * 1024) return json({ ok: false, error: "too_large" }, 413);

  // One visitor may send a handful of requests per minute, no more.
  if (env.QUOTE_LIMIT) {
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const { success } = await env.QUOTE_LIMIT.limit({ key: ip });
    if (!success) return json({ ok: false, error: "rate" }, 429);
  }

  let fd;
  try {
    fd = await request.formData();
  } catch {
    return json({ ok: false, error: "bad_form" }, 400);
  }

  // Bot traps: a hidden field people never see, and a minimum fill-in time.
  // Bots get a normal-looking "ok" so they don't learn anything.
  if (str(fd.get("website"))) return json({ ok: true });
  const started = Number(fd.get("t") || 0);
  if (!started || Date.now() - started < MIN_FILL_MS) return json({ ok: true });

  if (env.TURNSTILE_SECRET) {
    const token = str(fd.get("cf-turnstile-response"));
    const ok = token && await verifyTurnstile(token, env.TURNSTILE_SECRET, request.headers.get("cf-connecting-ip"));
    if (!ok) return json({ ok: false, error: "human_check" }, 400);
  }

  const lang = ["sv", "fi", "en"].includes(str(fd.get("lang"))) ? str(fd.get("lang")) : "sv";
  const q = {
    name: clean(fd.get("name"), 120),
    phone: clean(fd.get("phone"), 40),
    email: clean(fd.get("email"), 160),
    address: clean(fd.get("address"), 240),
    work: fd.getAll("work").map(w => clean(w, 40)).filter(Boolean).slice(0, 6),
    timing: clean(fd.get("timing"), 60),
    message: cleanMultiline(fd.get("message"), 5000),
    lang,
  };

  const missing = ["name", "phone", "email", "address", "message"].filter(k => !q[k]);
  if (missing.length) return json({ ok: false, error: "missing", fields: missing }, 400);
  if (!/^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]{2,}$/.test(q.email)) {
    return json({ ok: false, error: "missing", fields: ["email"] }, 400);
  }

  // Photos: JPEG only (the browser converts every photo to JPEG before sending).
  // Anything that isn't a real JPEG is refused, so no other file type can get through.
  const photos = [];
  let total = 0;
  for (const f of fd.getAll("photos")) {
    if (typeof f === "string") continue;
    if (photos.length >= MAX_PHOTOS) break;
    if (f.size === 0) continue;
    if (f.size > MAX_PHOTO_BYTES) return json({ ok: false, error: "photo_too_large" }, 413);
    total += f.size;
    if (total > MAX_TOTAL_BYTES) return json({ ok: false, error: "too_large" }, 413);
    const bytes = new Uint8Array(await f.arrayBuffer());
    if (!isJpeg(bytes)) return json({ ok: false, error: "photo_type" }, 415);
    photos.push(bytes);
  }

  const from = env.QUOTE_FROM || "offert@xpressbygg.com";
  const raw = buildEmail({ q, photos, from, to: env.QUOTE_TO });
  await env.QUOTE_MAIL.send(new EmailMessage(from, env.QUOTE_TO, raw));

  return json({ ok: true });
}

async function verifyTurnstile(token, secret, ip) {
  const body = new FormData();
  body.append("secret", secret);
  body.append("response", token);
  if (ip) body.append("remoteip", ip);
  const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body });
  const data = await r.json().catch(() => ({}));
  return data.success === true;
}

// JPEG files start with FF D8 FF and end with FF D9.
function isJpeg(b) {
  if (b.length < 1024) return false;
  if (b[0] !== 0xff || b[1] !== 0xd8 || b[2] !== 0xff) return false;
  for (let i = b.length - 1; i > b.length - 64 && i > 0; i--) {
    if (b[i - 1] === 0xff && b[i] === 0xd9) return true;
  }
  return false;
}

/* ── email ─────────────────────────────────────────────── */

const LABELS = {
  name: "Namn", phone: "Telefon", email: "E-post", address: "Adress", work: "Arbete",
  timing: "Tidsram", lang: "Språk på sidan", message: "Beskrivning", photos: "Bilder",
};
const LANG_NAMES = { sv: "Svenska", fi: "Finska", en: "Engelska" };

function buildEmail({ q, photos, from, to }) {
  const id = crypto.randomUUID();
  const mixed = "rel_" + id.replace(/-/g, "");
  const alt = "alt_" + id.replace(/-/g, "");

  const where = shortPlace(q.address);
  const what = q.work.length ? q.work.join(" + ") : "Offertförfrågan";
  const subject = `Offertförfrågan: ${what}${where ? ", " + where : ""}, ${q.name}`;

  const headers = [
    `From: ${encodeWords("Xpress Bygg webbplats")} <${from}>`,
    `To: <${to}>`,
    `Reply-To: ${encodeWords(q.name)} <${q.email}>`,
    `Subject: ${encodeWords(subject)}`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: <${id}@xpressbygg.com>`,
    "MIME-Version: 1.0",
    `Content-Type: multipart/related; boundary="${mixed}"`,
  ];

  const parts = [];
  parts.push(
    `--${mixed}`,
    `Content-Type: multipart/alternative; boundary="${alt}"`,
    "",
    `--${alt}`,
    "Content-Type: text/plain; charset=UTF-8",
    "Content-Transfer-Encoding: base64",
    "",
    b64lines(utf8(textBody(q, photos.length))),
    `--${alt}`,
    "Content-Type: text/html; charset=UTF-8",
    "Content-Transfer-Encoding: base64",
    "",
    b64lines(utf8(htmlBody(q, photos.length))),
    `--${alt}--`,
  );
  photos.forEach((bytes, i) => {
    parts.push(
      `--${mixed}`,
      `Content-Type: image/jpeg`,
      "Content-Transfer-Encoding: base64",
      `Content-ID: <foto${i + 1}@xpressbygg>`,
      "Content-Disposition: inline",
      "",
      b64lines(bytes),
    );
  });
  parts.push(`--${mixed}--`, "");

  return headers.join("\r\n") + "\r\n\r\n" + parts.join("\r\n");
}

function textBody(q, n) {
  return [
    "Ny offertförfrågan från xpressbygg.com",
    "",
    `${LABELS.name}: ${q.name}`,
    `${LABELS.phone}: ${q.phone}`,
    `${LABELS.email}: ${q.email}`,
    `${LABELS.address}: ${q.address}`,
    `${LABELS.work}: ${q.work.join(", ") || "-"}`,
    `${LABELS.timing}: ${q.timing || "-"}`,
    `${LABELS.lang}: ${LANG_NAMES[q.lang]}`,
    "",
    `${LABELS.message}:`,
    q.message,
    "",
    `${LABELS.photos}: ${n}`,
    "",
    "Svara på det här mejlet för att svara kunden direkt.",
  ].join("\r\n");
}

function htmlBody(q, n) {
  const row = (label, value) =>
    `<tr><td style="width:1%;padding:8px 22px 8px 0;color:#5A606B;font-size:13px;white-space:nowrap;vertical-align:top">${esc(label)}</td>` +
    `<td style="padding:8px 0;font-size:15px;color:#14161A">${value}</td></tr>`;
  const maps = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(q.address);
  const tel = q.phone.replace(/[^\d+]/g, "");
  const imgs = Array.from({ length: n }, (_, i) =>
    `<div style="margin:0 0 14px"><img src="cid:foto${i + 1}@xpressbygg" alt="Bild ${i + 1}" ` +
    `style="display:block;max-width:100%;width:640px;height:auto;border:1px solid #E3E5E8"></div>`).join("");

  return `<!doctype html><html><body style="margin:0;padding:24px;background:#EEEFF1;font-family:Arial,Helvetica,sans-serif">
<div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #E3E5E8">
  <div style="background:#15181D;padding:18px 24px;color:#ffffff;font-size:18px;font-weight:bold;font-style:italic;letter-spacing:.5px">
    <span style="color:#0A84FF">X</span>PRESS BYGG <span style="font-weight:normal;color:#9aa1ad;font-size:14px;font-style:normal">&nbsp;Ny offertförfrågan</span>
  </div>
  <div style="padding:24px">
    <table role="presentation" cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%">
      ${row(LABELS.name, `<strong>${esc(q.name)}</strong>`)}
      ${row(LABELS.phone, `<a href="tel:${esc(tel)}" style="color:#0060DF">${esc(q.phone)}</a>`)}
      ${row(LABELS.email, `<a href="mailto:${esc(q.email)}" style="color:#0060DF">${esc(q.email)}</a>`)}
      ${row(LABELS.address, `<a href="${esc(maps)}" style="color:#0060DF">${esc(q.address)}</a>`)}
      ${row(LABELS.work, esc(q.work.join(", ") || "-"))}
      ${row(LABELS.timing, esc(q.timing || "-"))}
      ${row(LABELS.lang, esc(LANG_NAMES[q.lang]))}
    </table>
    <div style="margin:22px 0 8px;color:#5A606B;font-size:13px">${esc(LABELS.message)}</div>
    <div style="font-size:15px;line-height:1.55;color:#14161A;white-space:pre-wrap;background:#F7F8FA;border-left:3px solid #0A84FF;padding:14px 16px">${esc(q.message)}</div>
    ${n ? `<div style="margin:26px 0 12px;color:#5A606B;font-size:13px">${esc(LABELS.photos)} (${n})</div>${imgs}` : ""}
    <div style="margin-top:22px;padding-top:16px;border-top:1px solid #E3E5E8;color:#5A606B;font-size:12px">
      Svara på det här mejlet för att svara kunden direkt.
    </div>
  </div>
</div></body></html>`;
}

// "Storgatan 5, 10600 Ekenäs" -> "Ekenäs"
function shortPlace(addr) {
  const parts = addr.split(",").map(s => s.trim()).filter(Boolean);
  const last = parts.length > 1 ? parts[parts.length - 1] : "";
  return last.replace(/^\d{3,6}\s*/, "").slice(0, 40);
}

/* ── helpers ───────────────────────────────────────────── */

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}
function str(v) { return typeof v === "string" ? v.trim() : ""; }
function clean(v, max) { return str(v).replace(/[\r\n\t\u0000-\u001f\u007f]+/g, " ").replace(/\s{2,}/g, " ").slice(0, max); }
function cleanMultiline(v, max) { return str(v).replace(/\r\n?/g, "\n").replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, "").slice(0, max); }
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function utf8(s) { return new TextEncoder().encode(s); }

function b64(bytes) {
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}
function b64lines(bytes) { return b64(bytes).replace(/.{1,76}/g, "$&\r\n").trimEnd(); }

// RFC 2047 header encoding, split so each encoded word stays short.
function encodeWords(s) {
  if (/^[\x20-\x7e]*$/.test(s) && !/[=?_"]/.test(s)) return `"${s}"`.replace(/^"(.*)"$/, s.includes(",") ? '"$1"' : "$1");
  const chars = Array.from(s);
  const words = [];
  let chunk = "";
  for (const ch of chars) {
    if (utf8(chunk + ch).length > 42) { words.push(chunk); chunk = ""; }
    chunk += ch;
  }
  if (chunk) words.push(chunk);
  return words.map(w => `=?UTF-8?B?${b64(utf8(w))}?=`).join("\r\n ");
}
