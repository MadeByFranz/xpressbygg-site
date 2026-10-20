#!/usr/bin/env python3
"""Generate the quote-request pages (sv/fi/en) from the matching home page's styles."""
import json, re, sys, html
from pathlib import Path

ROOT = Path(sys.argv[1])

LANGS = {
  "sv": dict(home="/", src="index.html", out="offert/index.html", path="/offert/", html_lang="sv"),
  "fi": dict(home="/fi/", src="fi/index.html", out="fi/tarjous/index.html", path="/fi/tarjous/", html_lang="fi"),
  "en": dict(home="/en/", src="en/index.html", out="en/quote/index.html", path="/en/quote/", html_lang="en"),
}
QUOTE_PATHS = {k: v["path"] for k, v in LANGS.items()}

TEXT = {
 "sv": dict(
  title="Begär offert | Xpress Bygg",
  desc="Beskriv ditt projekt och skicka bilder. Bastur, terrasser, fasader och tak i Raseborg med omnejd. Platsbesök och offert utan kostnad.",
  nav=["Tjänster", "Så jobbar vi", "Varför vi"], cta="Begär offert",
  label="Begär offert", h1a="Berätta vad", h1b="du planerar.",
  intro="Beskriv projektet och bifoga gärna bilder på platsen eller en skiss med ungefärliga mått. Ju mer vi vet, desto bättre blir första samtalet.",
  steps_label="Så går det till",
  steps=[("Du skickar förfrågan", "Formuläret tar ett par minuter."),
         ("Vi hör av oss", "Vi går igenom ditt projekt och kontaktar dig för att boka ett platsbesök.", "Hemort Raseborg. Vi betjänar Raseborg med omnejd."),
         ("Fast offert", "Efter besöket får du en skriftlig offert med material, arbete och tidtabell.")],
  perks=["Platsbesök och offerter utan kostnad", "Vi jobbar på svenska, finska och engelska", "Hemort Raseborg. Vi betjänar Raseborg med omnejd"],
  f_name="Namn", f_phone="Telefon", f_email="E-post", f_address="Adress där arbetet ska utföras",
  f_address_ph="Gatuadress, postnummer och ort",
  f_work="Vad gäller det?", work=["Bastu", "Terrass", "Fasad", "Tak", "Annat"],
  f_timing="När vill du att arbetet görs?", optional="valfritt",
  timing=["Inom 3 månader", "I år", "Nästa år", "Planerar bara än så länge"], timing_none="Välj tidsram",
  f_message="Beskriv projektet",
  f_message_ph="Vad vill du bygga eller renovera? Ungefärliga mått, material, nuvarande skick, önskemål…",
  f_photos="Bilder", drop_main="Lägg till bilder", drop_sub="Dra hit eller klicka. Foton av platsen, skisser med mått. Högst 8 bilder.",
  privacy="Vi använder dina uppgifter bara för att svara på din förfrågan.",
  send="Skicka förfrågan", sending="Skickar…",
  done_h="Tack", done_p="Din förfrågan är skickad. Vi går igenom den och hör av oss för att boka ett platsbesök.",
  done_back="Tillbaka till startsidan",
  js=dict(photoMax="Högst {n} bilder per förfrågan.", photoBad="En bild kunde inte läsas. Använd JPG eller PNG.",
          photoAlt="Bild {n}", photoRemove="Ta bort bild", photoWorking="Förbereder bilder…",
          photoCount="{n} av {max} bilder", missing="Fyll i de markerade fälten.",
          errors=dict(missing="Fyll i de markerade fälten.", photo_type="En av bilderna kunde inte skickas. Försök med en annan bild.",
                      photo_too_large="En bild är för stor. Försök med en mindre bild.", too_large="Bilderna är för stora tillsammans. Ta bort några och försök igen.",
                      rate="Du har skickat flera förfrågningar på kort tid. Vänta en stund och försök igen.",
                      human_check="Bekräfta att du är en människa och försök igen.",
                      config="Formuläret fungerar inte just nu. Försök igen senare.",
                      server="Något gick fel när förfrågan skickades. Försök igen om en stund.",
                      network="Ingen anslutning. Kontrollera internet och försök igen.")),
 ),
 "fi": dict(
  title="Pyydä tarjous | Xpress Bygg",
  desc="Kuvaile projektisi ja lähetä kuvia. Saunat, terassit, julkisivut ja katot Raaseporissa ja lähialueilla. Katselmus ja tarjous veloituksetta.",
  nav=["Palvelut", "Näin toimimme", "Miksi me"], cta="Pyydä tarjous",
  label="Pyydä tarjous", h1a="Kerro, mitä olet", h1b="suunnittelemassa.",
  intro="Kuvaile projekti ja liitä mielellään kuvia kohteesta tai luonnos karkeine mittoineen. Mitä enemmän tiedämme, sitä parempi ensimmäinen keskustelu.",
  steps_label="Näin se etenee",
  steps=[("Lähetät pyynnön", "Lomakkeen täyttäminen vie pari minuuttia."),
         ("Otamme yhteyttä", "Käymme projektisi läpi ja sovimme kanssasi katselmuksen.", "Kotipaikka Raasepori. Palvelemme Raaseporissa ja lähialueilla."),
         ("Kiinteä tarjous", "Katselmuksen jälkeen saat kirjallisen tarjouksen materiaaleineen, töineen ja aikatauluineen.")],
  perks=["Katselmukset ja tarjoukset veloituksetta", "Palvelemme suomeksi, ruotsiksi ja englanniksi", "Kotipaikka Raasepori. Palvelemme Raaseporissa ja lähialueilla"],
  f_name="Nimi", f_phone="Puhelin", f_email="Sähköposti", f_address="Työkohteen osoite",
  f_address_ph="Katuosoite, postinumero ja paikkakunta",
  f_work="Mitä työ koskee?", work=["Sauna", "Terassi", "Julkisivu", "Katto", "Muu"],
  f_timing="Milloin työ pitäisi tehdä?", optional="vapaaehtoinen",
  timing=["Kolmen kuukauden sisällä", "Tänä vuonna", "Ensi vuonna", "Vasta suunnittelen"], timing_none="Valitse aikataulu",
  f_message="Kuvaile projekti",
  f_message_ph="Mitä haluat rakentaa tai remontoida? Karkeat mitat, materiaalit, nykyinen kunto, toiveet…",
  f_photos="Kuvat", drop_main="Lisää kuvia", drop_sub="Vedä tähän tai klikkaa. Kuvia kohteesta, luonnoksia mittoineen. Enintään 8 kuvaa.",
  privacy="Käytämme tietojasi vain pyyntöösi vastaamiseen.",
  send="Lähetä pyyntö", sending="Lähetetään…",
  done_h="Kiitos", done_p="Pyyntösi on lähetetty. Käymme sen läpi ja otamme yhteyttä katselmuksen sopimiseksi.",
  done_back="Takaisin etusivulle",
  js=dict(photoMax="Enintään {n} kuvaa per pyyntö.", photoBad="Kuvaa ei voitu lukea. Käytä JPG- tai PNG-kuvaa.",
          photoAlt="Kuva {n}", photoRemove="Poista kuva", photoWorking="Valmistellaan kuvia…",
          photoCount="{n}/{max} kuvaa", missing="Täytä merkityt kentät.",
          errors=dict(missing="Täytä merkityt kentät.", photo_type="Yhtä kuvista ei voitu lähettää. Kokeile toista kuvaa.",
                      photo_too_large="Kuva on liian suuri. Kokeile pienempää kuvaa.", too_large="Kuvat ovat yhteensä liian suuria. Poista muutama ja yritä uudelleen.",
                      rate="Olet lähettänyt useita pyyntöjä lyhyessä ajassa. Odota hetki ja yritä uudelleen.",
                      human_check="Vahvista, että olet ihminen, ja yritä uudelleen.",
                      config="Lomake ei juuri nyt toimi. Yritä myöhemmin uudelleen.",
                      server="Pyynnön lähettämisessä tapahtui virhe. Yritä hetken kuluttua uudelleen.",
                      network="Ei yhteyttä. Tarkista internetyhteys ja yritä uudelleen.")),
 ),
 "en": dict(
  title="Get a quote | Xpress Bygg",
  desc="Describe your project and send photos. Saunas, decks, facades and roofs in Raseborg and surrounding areas. Free site visit and quote.",
  nav=["Services", "How we work", "Why us"], cta="Get a quote",
  label="Get a quote", h1a="Tell us what", h1b="you're planning.",
  intro="Describe the project and add photos of the site or a sketch with rough dimensions if you have them. The more we know, the better the first conversation.",
  steps_label="What happens next",
  steps=[("You send the request", "The form takes a couple of minutes."),
         ("We get in touch", "We go through your project and contact you to book a site visit.", "Based in Raseborg, serving Raseborg and surrounding areas."),
         ("Fixed quote", "After the visit you get a written quote with materials, labour and schedule.")],
  perks=["Site visits and quotes free of charge", "We work in English, Finnish and Swedish", "Based in Raseborg, serving Raseborg &amp; surrounding areas"],
  f_name="Name", f_phone="Phone", f_email="Email", f_address="Address of the work site",
  f_address_ph="Street address, postcode and town",
  f_work="What is it about?", work=["Sauna", "Decking", "Facade", "Roof", "Other"],
  f_timing="When should the work be done?", optional="optional",
  timing=["Within 3 months", "This year", "Next year", "Just planning for now"], timing_none="Choose a timeframe",
  f_message="Describe the project",
  f_message_ph="What do you want to build or renovate? Rough dimensions, materials, current condition, wishes…",
  f_photos="Photos", drop_main="Add photos", drop_sub="Drag here or click. Photos of the site, sketches with dimensions. Up to 8 photos.",
  privacy="We only use your details to answer your request.",
  send="Send request", sending="Sending…",
  done_h="Thank you", done_p="Your request has been sent. We'll go through it and get in touch to book a site visit.",
  done_back="Back to the home page",
  js=dict(photoMax="Up to {n} photos per request.", photoBad="A photo couldn't be read. Use a JPG or PNG.",
          photoAlt="Photo {n}", photoRemove="Remove photo", photoWorking="Preparing photos…",
          photoCount="{n} of {max} photos", missing="Fill in the highlighted fields.",
          errors=dict(missing="Fill in the highlighted fields.", photo_type="One of the photos couldn't be sent. Try a different photo.",
                      photo_too_large="A photo is too large. Try a smaller one.", too_large="The photos are too large together. Remove a few and try again.",
                      rate="You've sent several requests in a short time. Wait a moment and try again.",
                      human_check="Confirm you're human and try again.",
                      config="The form isn't working right now. Try again later.",
                      server="Something went wrong sending your request. Try again in a moment.",
                      network="No connection. Check your internet and try again.")),
 ),
}

FORM_CSS = r"""
/* ── QUOTE PAGE ───────────────────────── */
.quote{padding:130px 28px 100px}
.quote-inner{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1.15fr);gap:72px;align-items:start}
.quote-side{position:sticky;top:110px}
.quote-side h1{font-size:clamp(40px,4.6vw,66px);margin-top:14px}
.quote-side h1 .line{display:block;white-space:nowrap}
.quote-side h1 .accent{color:var(--accent)}
.quote-intro{margin-top:22px;color:var(--muted);font-size:16px;max-width:440px}
.quote-steps{margin-top:40px;border-top:1px solid var(--line)}
.quote-steps .label{display:block;margin:22px 0 6px}
.qstep{display:grid;grid-template-columns:44px 1fr;gap:6px;padding:14px 0;border-bottom:1px solid var(--line)}
.qstep b{font-family:'Saira Condensed',sans-serif;font-style:italic;font-weight:800;font-size:30px;line-height:1;color:var(--accent)}
.qstep h3{font-family:'Saira',sans-serif;font-weight:600;font-size:13px;letter-spacing:.1em;text-transform:uppercase}
.qstep p{font-size:14px;color:var(--muted);margin-top:2px}

.qform,.quote-done{background:#F7F8FA;border:1px solid var(--line);padding:38px 38px 34px}
.qform[hidden],.quote-done[hidden]{display:none}
.qgrid{display:grid;grid-template-columns:1fr 1fr;gap:20px 18px}
.qfield{display:flex;flex-direction:column;gap:7px;min-width:0}
.qfield.full{grid-column:1/-1}
.qform label,.qform legend{font-family:'Saira',sans-serif;font-weight:600;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink)}
.qform .opt{color:var(--muted);font-weight:500;letter-spacing:.06em;text-transform:none;font-family:'Figtree',sans-serif;font-size:12px}
.qform input[type=text],.qform input[type=tel],.qform input[type=email],.qform select,.qform textarea{
  font:inherit;font-size:16px;color:var(--ink);background:#fff;
  border:1px solid rgba(20,22,26,.22);border-radius:0;padding:12px 14px;width:100%;
  transition:border-color .15s, box-shadow .15s;
}
.qform textarea{min-height:170px;resize:vertical;line-height:1.55}
.qform select{appearance:none;background-image:linear-gradient(45deg,transparent 50%,var(--ink) 50%),linear-gradient(135deg,var(--ink) 50%,transparent 50%);background-position:calc(100% - 20px) 50%,calc(100% - 15px) 50%;background-size:5px 5px;background-repeat:no-repeat;padding-right:40px}
.qform input:focus,.qform select:focus,.qform textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(10,132,255,.18)}
.qform [aria-invalid=true]{border-color:#D7263D !important;box-shadow:0 0 0 3px rgba(215,38,61,.12)}
.qform fieldset{border:none;padding:0;margin:0;min-width:0}
.qform legend{margin-bottom:9px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{position:relative}
.chip input{position:absolute;opacity:0;inset:0;cursor:pointer}
.chip span{
  display:inline-flex;align-items:center;gap:8px;
  font-family:'Saira Condensed',sans-serif;font-style:italic;font-weight:700;font-size:18px;letter-spacing:.03em;text-transform:uppercase;
  padding:8px 16px 8px 14px;background:#fff;border:1px solid rgba(20,22,26,.22);color:var(--ink);
  transition:background .15s,color .15s,border-color .15s;cursor:pointer;
}
.chip span svg{width:.7em;height:.7em;opacity:.35;transition:opacity .15s}
.chip input:checked + span{background:var(--ink);border-color:var(--ink);color:#fff}
.chip input:checked + span svg{opacity:1}
.chip input:focus-visible + span{outline:3px solid var(--accent);outline-offset:2px}

.attach{border:1px solid rgba(20,22,26,.22);border-top:none;background:#fff;margin-top:-7px}
.drop{
  display:flex;align-items:center;gap:14px;padding:14px;cursor:pointer;
  border-top:1px dashed rgba(20,22,26,.22);background:#FBFBFC;transition:background .15s;
}
.drop:hover,.drop.over{background:#EEF5FF}
.drop:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}
.drop .ico{width:40px;height:40px;flex-shrink:0;display:grid;place-items:center;background:var(--ink);color:#fff;
  clip-path:polygon(6px 0,100% 0,calc(100% - 6px) 100%,0 100%)}
.drop .ico svg{width:20px;height:20px}
.drop strong{display:block;font-family:'Saira',sans-serif;font-weight:600;font-size:13px;letter-spacing:.1em;text-transform:uppercase}
.drop small{display:block;color:var(--muted);font-size:13px;line-height:1.4;margin-top:2px}
.thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:8px;padding:12px 14px 14px;border-top:1px solid rgba(20,22,26,.1)}
.thumbs[hidden]{display:none}
.thumbs figure{position:relative;aspect-ratio:1;background:var(--panel);overflow:hidden}
.thumbs img{width:100%;height:100%;object-fit:cover;display:block}
.thumbs .rm{position:absolute;top:4px;right:4px;width:26px;height:26px;border:none;background:rgba(20,22,26,.78);color:#fff;font-size:18px;line-height:1;cursor:pointer;display:grid;place-items:center}
.thumbs .rm:hover{background:#D7263D}
.photo-note{font-size:13px;color:var(--muted);min-height:1.2em;margin-top:8px}
.human-check{margin-top:4px}
.human-check[hidden]{display:none}
.qfoot{margin-top:26px;display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap}
.qfoot p{font-size:13px;color:var(--muted);max-width:300px}
.qform button[type=submit]{border:none;cursor:pointer;font:inherit}
.qform button[type=submit].btn{font-family:'Saira',sans-serif;font-weight:600;font-size:13px;letter-spacing:.16em;text-transform:uppercase;padding:16px 34px}
.qform button[disabled]{opacity:.6;cursor:progress}
.form-status{margin-top:18px;padding:12px 14px;font-size:14px;border-left:3px solid}
.form-status[hidden]{display:none}
.form-status.error{background:#FDECEE;border-color:#D7263D;color:#7A1020}
.form-status.warn{background:#FFF6E0;border-color:#E0A100;color:#6A4A00}
.hp{position:absolute !important;left:-10000px !important;width:1px;height:1px;overflow:hidden}

.quote-done{text-align:left;padding:54px 42px}
.quote-done:focus{outline:none}
.quote-done .tick{width:56px;height:56px;margin-bottom:22px}
.quote-done h2{font-size:clamp(40px,5vw,64px)}
.quote-done h2 .accent{color:var(--accent)}
.quote-done p{margin-top:16px;color:var(--muted);font-size:16px;max-width:460px}
.quote-done .btn{margin-top:30px}

@media(max-width:880px){
  .quote{padding:110px 20px 72px}
  .quote-inner{grid-template-columns:minmax(0,1fr);gap:40px}
  .quote-side h1{font-size:clamp(28px,8.4vw,46px)}
  .quote-side{position:static}
  .qform,.quote-done{padding:26px 18px 24px}
  .quote-done h2{font-size:clamp(34px,10vw,48px)}
}
@media(max-width:560px){
  .qgrid{grid-template-columns:1fr}
}
"""

XM = '<svg class="xmark" viewBox="0 0 100 98" aria-hidden="true"><use href="#xglyph" fill="var(--accent)"/></svg>'
CHIP_X = '<svg viewBox="0 0 100 98" aria-hidden="true"><use href="#xglyph" fill="currentColor"/></svg>'


def build(code):
    L, t = LANGS[code], TEXT[code]
    src = (ROOT / L["src"]).read_text()
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    defs = re.search(r'(<svg width="0" height="0".*?</svg>)', src, re.S).group(1)
    home = L["home"]
    canonical = "https://xpressbygg.com" + L["path"]
    alt = "\n".join(f'<link rel="alternate" hreflang="{c}" href="https://xpressbygg.com{p}">' for c, p in QUOTE_PATHS.items())
    alt += f'\n<link rel="alternate" hreflang="x-default" href="https://xpressbygg.com{QUOTE_PATHS["sv"]}">'
    lang_links = "\n          ".join(
        f'<a href="{QUOTE_PATHS[c]}" hreflang="{c}"' + (' aria-current="true"' if c == code else f' lang="{c}"') + f'>{c.upper()}</a>'
        for c in ("sv", "fi", "en"))
    def step(i, s):
        extra = f'<p>{s[2]}</p>' if len(s) > 2 else ''
        return f'<div class="qstep"><b>{i}</b><div><h3>{s[0]}</h3><p>{s[1]}</p>{extra}</div></div>'
    steps = "\n".join(step(i, s) for i, s in enumerate(t["steps"], 1))
    perks = "\n".join(f"<div>{XM}{p}</div>" for p in t["perks"])
    chips = "\n".join(
        f'<label class="chip"><input type="checkbox" name="work" value="{html.escape(w)}"><span>{CHIP_X}{html.escape(w)}</span></label>'
        for w in t["work"])
    timing = f'<option value="">{t["timing_none"]}</option>' + "".join(f'<option>{html.escape(x)}</option>' for x in t["timing"])
    js_text = dict(t["js"], lang=code, send=t["send"], sending=t["sending"])

    page = f"""<!DOCTYPE html>
<html lang="{L['html_lang']}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{t['desc']}">
<meta property="og:title" content="{t['title']}">
<meta property="og:description" content="{t['desc']}">
<meta property="og:image" content="/logo.png">
<link rel="canonical" href="{canonical}">
{alt}
<title>{t['title']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Saira+Condensed:ital,wght@0,600;0,800;1,700;1,800&family=Saira:wght@500;600&family=Figtree:wght@400;500;600&display=swap" rel="stylesheet">
<style>{style}{FORM_CSS}</style>
</head>
<body>

{defs}

<header>
  <div class="nav-inner">
    <a class="brand" href="{home}" aria-label="Xpress Bygg">
      <svg class="brand-x" viewBox="0 0 100 98" aria-hidden="true"><use href="#xglyph" fill="var(--accent)" transform="skewX(-6) translate(6,0)"/></svg>
      <span class="brand-word"><b>PRESS</b><i>BYGG</i></span>
    </a>
    <nav aria-label="Main">
      <ul>
        <li class="hide-m"><a href="{home}#services">{t['nav'][0]}</a></li>
        <li class="hide-m"><a href="{home}#process">{t['nav'][1]}</a></li>
        <li class="hide-m"><a href="{home}#why">{t['nav'][2]}</a></li>
        <li><a class="nav-cta" href="{L['path']}" aria-current="page">{t['cta']}</a></li>
        <li class="lang" aria-label="Language">
          {lang_links}
        </li>
      </ul>
    </nav>
  </div>
</header>

<main class="quote" id="top">
  <div class="quote-inner">
    <aside class="quote-side">
      <span class="label">{t['label']}</span>
      <h1 class="display" id="quote-h1"><span class="line">{t['h1a']}</span><span class="line accent">{t['h1b']}</span></h1>
      <p class="quote-intro">{t['intro']}</p>
      <div class="quote-steps">
        <span class="label">{t['steps_label']}</span>
        {steps}
      </div>
    </aside>

    <div>
      <form class="qform" id="quote-form" novalidate>
        <input type="hidden" name="lang" value="{code}">
        <input type="hidden" name="t" value="">
        <div class="hp" aria-hidden="true"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>

        <div class="qgrid">
          <div class="qfield full">
            <label for="q-name">{t['f_name']}</label>
            <input id="q-name" type="text" name="name" autocomplete="name" required maxlength="120">
          </div>
          <div class="qfield">
            <label for="q-phone">{t['f_phone']}</label>
            <input id="q-phone" type="tel" name="phone" autocomplete="tel" required maxlength="40">
          </div>
          <div class="qfield">
            <label for="q-email">{t['f_email']}</label>
            <input id="q-email" type="email" name="email" autocomplete="email" required maxlength="160">
          </div>
          <div class="qfield full">
            <label for="q-address">{t['f_address']}</label>
            <input id="q-address" type="text" name="address" autocomplete="street-address" required maxlength="240" placeholder="{t['f_address_ph']}">
          </div>
          <fieldset class="qfield full">
            <legend>{t['f_work']} <span class="opt">({t['optional']})</span></legend>
            <div class="chips">
            {chips}
            </div>
          </fieldset>
          <div class="qfield full">
            <label for="q-timing">{t['f_timing']} <span class="opt">({t['optional']})</span></label>
            <select id="q-timing" name="timing">{timing}</select>
          </div>
          <div class="qfield full">
            <label for="q-message">{t['f_message']}</label>
            <textarea id="q-message" name="message" required maxlength="5000" placeholder="{t['f_message_ph']}"></textarea>
            <div class="attach">
              <div class="drop" id="drop" role="button" tabindex="0" aria-describedby="photo-note">
                <span class="ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h3l2-3h6l2 3h3v13H4z"/><circle cx="12" cy="13" r="3.5"/></svg></span>
                <span><strong>{t['drop_main']} <span class="opt">({t['optional']})</span></strong><small>{t['drop_sub']}</small></span>
              </div>
              <div class="thumbs" id="thumbs" hidden></div>
            </div>
            <input id="photo-input" type="file" name="photos-picker" accept="image/*" multiple hidden>
            <div class="photo-note" id="photo-note" aria-live="polite"></div>
          </div>
          <div class="qfield full human-check" id="human-check" hidden></div>
        </div>

        <div class="form-status" id="form-status" role="alert" hidden></div>

        <div class="qfoot">
          <p>{t['privacy']}</p>
          <button type="submit" class="btn btn-solid">{t['send']}</button>
        </div>
      </form>

      <div class="quote-done" id="quote-done" tabindex="-1" hidden>
        <svg class="tick" viewBox="0 0 100 98" aria-hidden="true"><use href="#xglyph" fill="var(--accent)" transform="skewX(-6) translate(6,0)"/></svg>
        <h2 class="display">{t['done_h']}<span id="quote-done-name-wrap">, <span class="accent" id="quote-done-name"></span></span>!</h2>
        <p>{t['done_p']}</p>
        <a class="btn btn-ghost" href="{home}">{t['done_back']}</a>
      </div>
    </div>
  </div>
</main>

<footer>
  <div class="foot-inner">
    <span class="brand" style="color:#EDEFE8">
      <svg class="brand-x" viewBox="0 0 100 98" aria-hidden="true"><use href="#xglyph" fill="var(--accent)" transform="skewX(-6) translate(6,0)"/></svg>
      <span class="brand-word"><b>PRESS</b><i>BYGG</i></span>
    </span>
    <span class="label">{re.search(r'<footer>.*?<span class="label">(.*?)</span>', src, re.S).group(1)}</span>
    <span class="label">© <span id="yr">2026</span> Xpress Bygg</span>
  </div>
</footer>

<script type="application/json" id="quote-text">{json.dumps(js_text, ensure_ascii=False)}</script>
<script>
document.getElementById('yr').textContent = new Date().getFullYear();
// keep each heading line whole: shrink the text until the longest line fits
(function(){{
  const h = document.getElementById('quote-h1');
  function fit(){{
    h.style.fontSize = '';
    const max = h.parentElement.clientWidth;
    let size = parseFloat(getComputedStyle(h).fontSize), guard = 40;
    const widest = () => Math.max(...[...h.querySelectorAll('.line')].map(l => l.scrollWidth));
    while (widest() > max && size > 20 && guard--) {{ size *= 0.95; h.style.fontSize = size + 'px'; }}
  }}
  fit(); addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
}})();
</script>
<script src="/assets/quote.js" defer></script>
</body>
</html>
"""
    out = ROOT / L["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print("wrote", out)


for c in LANGS:
    build(c)
