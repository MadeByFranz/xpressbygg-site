// Quote request form: photo previews, in-browser resizing, sending.
(function () {
  const form = document.getElementById("quote-form");
  if (!form) return;
  const T = JSON.parse(document.getElementById("quote-text").textContent);

  const MAX_PHOTOS = 8;
  const MAX_SIDE = 1600;     // longest side in pixels after resizing
  const QUALITY = 0.82;

  const drop = document.getElementById("drop");
  const picker = document.getElementById("photo-input");
  const grid = document.getElementById("thumbs");
  const photoNote = document.getElementById("photo-note");
  const status = document.getElementById("form-status");
  const submit = form.querySelector("button[type=submit]");
  const photos = []; // { blob, url }
  let busy = 0;

  form.querySelector("input[name=t]").value = String(Date.now());

  // Optional "are you human" check, switched on from Cloudflare settings.
  fetch("/api/quote-config").then(r => r.ok ? r.json() : {}).then(cfg => {
    if (!cfg || !cfg.turnstileSiteKey) return;
    const box = document.getElementById("human-check");
    box.hidden = false;
    window.__xbTurnstile = () => window.turnstile.render(box, { sitekey: cfg.turnstileSiteKey, language: T.lang });
    const s = document.createElement("script");
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=__xbTurnstile&render=explicit";
    s.async = true;
    document.head.appendChild(s);
  }).catch(() => {});

  /* ── photos ─────────────────────────────── */

  drop.addEventListener("click", () => picker.click());
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); picker.click(); } });
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => addFiles(e.dataTransfer.files));
  picker.addEventListener("change", () => { addFiles(picker.files); picker.value = ""; });

  async function addFiles(list) {
    const files = Array.from(list || []);
    let skipped = 0, failed = 0;
    for (const file of files) {
      if (photos.length + busy >= MAX_PHOTOS) { skipped++; continue; }
      if (!/^image\//.test(file.type) && !/\.(jpe?g|png|webp|heic|heif|gif)$/i.test(file.name)) { failed++; continue; }
      busy++; renderNote();
      try {
        const blob = await toJpeg(file);
        photos.push({ blob, url: URL.createObjectURL(blob) });
      } catch { failed++; }
      busy--; renderThumbs(); renderNote();
    }
    const msgs = [];
    if (skipped) msgs.push(T.photoMax.replace("{n}", MAX_PHOTOS));
    if (failed) msgs.push(T.photoBad);
    if (msgs.length) showStatus(msgs.join(" "), "warn");
  }

  // Redraw every photo as a fresh JPEG: smaller upload, correct rotation,
  // and nothing but plain image pixels gets sent.
  async function toJpeg(file) {
    let src, w, h;
    try {
      src = await createImageBitmap(file, { imageOrientation: "from-image" });
      w = src.width; h = src.height;
    } catch {
      src = await new Promise((res, rej) => {
        const img = new Image();
        img.onload = () => res(img);
        img.onerror = rej;
        img.src = URL.createObjectURL(file);
      });
      w = src.naturalWidth; h = src.naturalHeight;
    }
    if (!w || !h) throw new Error("empty image");
    const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(src, 0, 0, canvas.width, canvas.height);
    if (src.close) src.close();
    const blob = await new Promise(res => canvas.toBlob(res, "image/jpeg", QUALITY));
    if (!blob) throw new Error("encode failed");
    return blob;
  }

  function renderThumbs() {
    grid.innerHTML = "";
    photos.forEach((p, i) => {
      const fig = document.createElement("figure");
      const img = document.createElement("img");
      img.src = p.url; img.alt = T.photoAlt.replace("{n}", i + 1);
      const rm = document.createElement("button");
      rm.type = "button"; rm.className = "rm"; rm.setAttribute("aria-label", T.photoRemove);
      rm.innerHTML = "&times;";
      rm.addEventListener("click", () => { URL.revokeObjectURL(p.url); photos.splice(i, 1); renderThumbs(); renderNote(); });
      fig.append(img, rm);
      grid.appendChild(fig);
    });
    grid.hidden = photos.length === 0;
  }

  function renderNote() {
    photoNote.textContent = busy ? T.photoWorking
      : photos.length ? T.photoCount.replace("{n}", photos.length).replace("{max}", MAX_PHOTOS)
      : "";
  }

  /* ── sending ────────────────────────────── */

  form.addEventListener("submit", async e => {
    e.preventDefault();
    clearStatus();
    if (busy) { showStatus(T.photoWorking, "warn"); return; }

    form.querySelectorAll("[aria-invalid]").forEach(el => el.removeAttribute("aria-invalid"));
    const bad = Array.from(form.querySelectorAll("[required]")).filter(el => !el.checkValidity());
    if (bad.length) {
      bad.forEach(el => el.setAttribute("aria-invalid", "true"));
      bad[0].focus();
      showStatus(T.missing, "error");
      return;
    }

    const fd = new FormData(form);
    fd.delete("photos-picker");
    photos.forEach((p, i) => fd.append("photos", p.blob, `foto-${i + 1}.jpg`));

    submit.disabled = true;
    submit.textContent = T.sending;
    try {
      const r = await fetch("/api/quote", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (r.ok && data.ok) {
        const name = (fd.get("name") || "").toString().split(" ")[0];
        document.getElementById("quote-done-name").textContent = name;
        form.hidden = true;
        document.getElementById("quote-done").hidden = false;
        document.getElementById("quote-done").focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
      showStatus(T.errors[data.error] || T.errors.server, "error");
      if (data.fields) data.fields.forEach(f => { const el = form.elements[f]; if (el) el.setAttribute("aria-invalid", "true"); });
      if (window.turnstile) window.turnstile.reset();
    } catch {
      showStatus(T.errors.network, "error");
    } finally {
      submit.disabled = false;
      submit.textContent = T.send;
    }
  });

  function showStatus(msg, kind) { status.textContent = msg; status.className = "form-status " + kind; status.hidden = false; }
  function clearStatus() { status.hidden = true; status.textContent = ""; }
})();
