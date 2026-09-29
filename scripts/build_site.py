#!/usr/bin/env python3
"""Construit le site statique « Prix à la Pompe » (GitHub Pages).

Usage : SITE_URL=https://pseudo.github.io/prix-a-la-pompe python3 build_site.py <donnees> <sortie>

<donnees> : dossier produit par build_data.py (contient data/stations.json, ...)
<sortie>  : dossier publie (index.html, pages villes / departements / carburants,
            sitemap.xml, robots.txt, donnees de la carte).
Bibliotheque standard uniquement.
"""
import json, os, re, sys, shutil, unicodedata, math, html, glob
from datetime import datetime, date, timedelta
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = os.environ.get("SITE_URL", "https://example.github.io/prix-a-la-pompe").rstrip("/")
BASE = urlparse(SITE_URL).path.rstrip("/")          # ex. /prix-a-la-pompe
GSC = os.environ.get("GOOGLE_SITE_VERIFICATION", "")
BING = os.environ.get("BING_SITE_VERIFICATION", "")
SITE_NAME = "Prix à la Pompe"

FUELS = [  # cle donnees, libelle, slug de page, nom complet
    ("Gazole", "Gazole", "prix-gazole", "gazole"),
    ("SP95", "SP95", "prix-sp95", "SP95"),
    ("E10", "SP95-E10", "prix-sp95-e10", "SP95-E10"),
    ("SP98", "SP98", "prix-sp98", "SP98"),
    ("E85", "E85", "prix-e85", "E85 (superéthanol)"),
    ("GPLc", "GPLc", "prix-gpl", "GPL carburant"),
]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
E = html.escape


def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def eur(m, digits=3):
    return f"{m / 1000:.{digits}f}".replace(".", ",") + " €"


def ct(v):
    return f"{abs(v) / 10:.1f}".replace(".", ",")


def fmt2(x):
    return f"{x:.2f}".replace(".", ",")


def fr_date(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def ago(d):
    return "aujourd'hui" if d == 0 else "hier" if d == 1 else f"il y a {d} j"


def url(path):
    return BASE + path


def dep_of(cp):
    d = cp[:2]
    if d == "20":
        return "2A" if int(cp) < 20200 else "2B"
    return d


def km(a, b, c, d):
    r = math.pi / 180
    x = math.sin((c - a) * r / 2) ** 2 + math.cos(a * r) * math.cos(c * r) * math.sin((d - b) * r / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


# ------------------------------------------------------------------ gabarit
HEADER_NAV = [("Carte", "/"), ("Gazole", "/prix-gazole/"), ("SP95-E10", "/prix-sp95-e10/"),
              ("SP98", "/prix-sp98/"), ("Enseignes", "/enseignes/"), ("Départements", "/departements/"),
              ("Actualités", "/actualites/")]
TANK = 50  # litres, pour les exemples de plein


def share_bar(path, text):
    u = SITE_URL + path
    from urllib.parse import quote
    q, t = quote(u, safe=""), quote(text, safe="")
    return (f'<div class="share"><span>Partager :</span>'
            f'<a href="https://wa.me/?text={t}%20{q}" rel="noopener" target="_blank">WhatsApp</a>'
            f'<a href="https://www.facebook.com/sharer/sharer.php?u={q}" rel="noopener" target="_blank">Facebook</a>'
            f'<a href="https://twitter.com/intent/tweet?text={t}&url={q}" rel="noopener" target="_blank">X</a>'
            f'<button type="button" data-copy="{E(u)}">Copier le lien</button></div>')


COPY_JS = """<script>document.addEventListener('click',function(e){var b=e.target.closest('[data-copy]');if(!b)return;
var u=b.getAttribute('data-copy');(navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).then(function(){b.textContent='Lien copié'},function(){prompt('Copiez ce lien :',u)});});</script>"""


def page(path, title, desc, body, crumbs=None, jsonld=None, updated=None, share=True, robots="index,follow,max-image-preview:large"):
    canon = SITE_URL + path
    if share and body:
        body = body + share_bar(path, title)
    ld = list(jsonld or [])
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList",
                   "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                        "item": SITE_URL + p} for i, (n, p) in enumerate(crumbs)]})
    nav = "".join(f'<a href="{url(p)}">{E(n)}</a>' for n, p in HEADER_NAV)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs" aria-label="Fil d\'Ariane">' + " › ".join(
            (f'<a href="{url(p)}">{E(n)}</a>' if i < len(crumbs) - 1 else f"<span>{E(n)}</span>")
            for i, (n, p) in enumerate(crumbs)) + "</nav>"
    verif = (f'<meta name="google-site-verification" content="{E(GSC)}">' if GSC else "") + \
            (f'<meta name="msvalidate.01" content="{E(BING)}">' if BING else "")
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE_URL}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1F3A93">
<link rel="icon" href="{url('/assets/favicon.svg')}" type="image/svg+xml">
<link rel="manifest" href="{url('/manifest.webmanifest')}"><link rel="apple-touch-icon" href="{url('/assets/icon-180.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800;900&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap">
<link rel="stylesheet" href="{url('/assets/site.css')}">
{verif}
<script data-goatcounter="https://prixalapompe.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
{''.join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + '</script>' for x in ld)}
</head>
<body>
<header class="top"><div class="in">
<a class="logo" href="{url('/')}"><svg width="24" height="24" viewBox="0 0 26 26" fill="none" aria-hidden="true"><rect x="3" y="3" width="12" height="20" rx="2" stroke="currentColor" stroke-width="2"/><rect x="6" y="6.5" width="6" height="5" rx="1" fill="#D42A2F"/><path d="M15 9h3.5a2 2 0 0 1 2 2v8a1.5 1.5 0 0 0 3 0V8.5L20.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><b>{SITE_NAME}</b></a>
<nav class="nav">{nav}</nav></div></header>
<main class="wrap">
{bc}
{body}
</main>
<footer class="foot"><div class="wrap">
<p>Prix officiels déclarés par les stations sur <a href="https://www.prix-carburants.gouv.fr" rel="noopener">prix-carburants.gouv.fr</a> (Ministère de l'Économie), actualisés automatiquement{(' · relevé du ' + E(updated)) if updated else ''}.</p>
<p><a href="{url('/departements/')}">Tous les départements</a> · <a href="{url('/enseignes/')}">Prix par enseigne</a> · <a href="{url('/prix-carburant-autoroute/')}">Prix sur autoroute</a> · <a href="{url('/actualites/')}">Actualités des prix</a> · <a href="{url('/widget/')}">Widget pour votre site</a> · <a href="{url('/a-propos/')}">Sources et méthode</a></p>
</div></footer>
{COPY_JS}
</body>
</html>
"""


def price_table(rows_idx, S, fuels_k, dep_names=None, show_city=False, limit=None):
    head = "<th>Station</th>" + ("<th>Commune</th>" if show_city else "") + \
           "".join(f"<th>{E(FUELS[k][1])}</th>" for k in fuels_k) + "<th>Mise à jour</th>"
    mins = {k: min([S[i][5][k] for i in rows_idx if S[i][5][k]] or [0]) for k in fuels_k}
    out = []
    for i in rows_idx[:limit] if limit else rows_idx:
        s = S[i]
        nm = s[8] or f"Station {s[3]}"
        brand = f'<small>{E(s[9])}</small>' if s[9] else ""
        cells = ""
        for k in fuels_k:
            p = s[5][k]
            cls = ' class="best"' if p and p == mins[k] else ""
            cells += f"<td{cls}>{eur(p) if p else '—'}</td>"
        ages = [s[6][k] for k in fuels_k if s[5][k]]
        city = f'<td>{E(s[3])} <small>{E(s[2])}</small></td>' if show_city else ""
        out.append(f'<tr><td><a href="{url("/?st=" + s[7])}">{E(nm)}</a>{brand}<small>{E(s[4])}</small></td>{city}{cells}'
                   f'<td class="age">{ago(min(ages)) if ages else "—"}</td></tr>')
    return f'<div class="tw"><table class="pt"><thead><tr>{head}</tr></thead><tbody>{"".join(out)}</tbody></table></div>'


def spark_svg(values, w=720, h=180, color="#1F3A93"):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * .1 or 10
    lo, hi = lo - pad, hi + pad
    n = len(values)
    pts = []
    for j, v in enumerate(values):
        if v is None:
            continue
        pts.append(f"{j / (n - 1) * (w - 60) + 50:.1f},{(hi - v) / (hi - lo) * (h - 30) + 10:.1f}")
    ticks = ""
    for t in range(4):
        v = lo + (hi - lo) * t / 3
        y = (hi - v) / (hi - lo) * (h - 30) + 10
        lab = f"{v / 1000:.2f}".replace(".", ",")
        ticks += f'<line x1="50" x2="{w - 10}" y1="{y:.1f}" y2="{y:.1f}" class="g"/><text x="44" y="{y + 4:.1f}" text-anchor="end">{lab}</text>'
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Évolution du prix moyen sur 12 mois">{ticks}'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/></svg>')


def dept_history(src, days=120):
    """Moyenne quotidienne par departement sur `days` jours, a partir de data/st/*.json."""
    res, start = {}, None
    for fp in glob.glob(os.path.join(src, "data", "st", "*.json")):
        H = json.load(open(fp))
        start = H.get("start", start)
        sums = [[0] * (days + 1) for _ in range(6)]
        cnts = [[0] * (days + 1) for _ in range(6)]
        for series in H["s"].values():
            for ks, pts in series.items():
                k = int(ks)
                for j, (d0, p) in enumerate(pts):
                    end = min(pts[j + 1][0] if j + 1 < len(pts) else days + 1, d0 + 30, days + 1)
                    for dd in range(max(d0, 0), end):
                        sums[k][dd] += p; cnts[k][dd] += 1
        res[os.path.basename(fp)[:-5]] = [[round(s / c) if c >= 3 else None for s, c in zip(sums[k], cnts[k])] for k in range(6)]
    return res, (date.fromisoformat(start) if start else None)


def st_key(cp):
    return "20" if cp.startswith("20") else cp[:2]


def trend_sentence(series, label, where):
    vals = [v for v in series if v]
    if len(vals) < 20:
        return ""
    dv = vals[-1] - vals[0]
    if abs(dv) < 5:
        return f"En quatre mois, le prix moyen du {label} {where} est resté stable, autour de {eur(vals[-1])}."
    return (f"En quatre mois, le prix moyen du {label} {where} a {'augmenté' if dv > 0 else 'baissé'} de "
            f"<b>{ct(dv)} centimes</b> par litre, passant de {eur(vals[0])} à {eur(vals[-1])}.")


def mini_chart(series, start, w=720, h=170, label=""):
    vals = [v for v in series if v]
    if len(vals) < 20:
        return ""
    lo, hi = min(vals), max(vals)
    pad = max((hi - lo) * .15, 15)
    lo, hi = lo - pad, hi + pad
    n = len(series)
    X = lambda j: 56 + j / (n - 1) * (w - 70)
    Y = lambda v: 10 + (hi - v) / (hi - lo) * (h - 40)
    pts = " ".join(f"{X(j):.1f},{Y(v):.1f}" for j, v in enumerate(series) if v)
    g = ""
    for tk in range(4):
        v = lo + (hi - lo) * tk / 3
        g += f'<line x1="56" x2="{w - 14}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="g"/><text x="50" y="{Y(v) + 4:.1f}" text-anchor="end">{f"{v / 1000:.2f}".replace(".", ",")}</text>'
    if start:
        for j in range(0, n, 30):
            dd = start + timedelta(days=j)
            g += f'<text x="{X(j):.1f}" y="{h - 8}" text-anchor="middle">{dd.day} {MONTHS[dd.month - 1][:4]}.</text>'
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{E(label)}">{g}'
            f'<polyline points="{pts}" fill="none" stroke="#1F3A93" stroke-width="2.2" stroke-linejoin="round"/></svg>')


def extra_sections(idx, S, where, main_k, dep_series, hstart, dep_name, SV, brand_path):
    """Contenu propre a chaque lieu : economie sur un plein, enseignes, 24h/24, tendance, FAQ."""
    out, faq = [], []
    lab = FUELS[main_k][3]
    vals = sorted(S[i][5][main_k] for i in idx if S[i][5][main_k])
    fresh = [i for i in idx if S[i][5][main_k] and S[i][6][main_k] <= 7] or [i for i in idx if S[i][5][main_k]]
    cheapest = min(fresh, key=lambda i: S[i][5][main_k], default=None)
    if vals:
        avg = sum(vals) / len(vals)
        txt = (f"Avec un prix moyen de {eur(round(avg))}, un plein de {TANK} litres de {lab} coûte environ "
               f"<b>{avg * TANK / 1000:.0f} €</b> {where}.")
        if len(vals) > 1 and vals[-1] - vals[0] >= 10:
            gain = (vals[-1] - vals[0]) * TANK / 1000
            gs = f"{gain:.2f}".replace(".", ",")
            txt += (f" Entre la station la moins chère ({eur(vals[0])}) et la plus chère ({eur(vals[-1])}), "
                    f"l'écart atteint <b>{gs} €</b> sur un plein.")
        out.append(f'<h2>Combien coûte un plein {where} ?</h2><p class="prose">{txt}</p>')
        faq.append((f"Combien coûte un plein de {lab} {where} ?",
                    re.sub("<[^>]+>", "", txt)))
    if cheapest is not None:
        s = S[cheapest]
        ans = (f"Le {fr_date(date.today())}, la station la moins chère pour le {lab} {where} est "
               f"{s[8] or 'la station du ' + s[4]} ({s[4]}, {s[2]} {s[3]}), à {eur(s[5][main_k])} le litre.")
        faq.insert(0, (f"Quelle est la station la moins chère {where} ?", ans))
    # enseignes
    br = {}
    for i in idx:
        if S[i][9] and S[i][5][main_k]:
            br.setdefault(S[i][9], []).append(S[i][5][main_k])
    if len(br) >= 2:
        rows = sorted(((sum(v) / len(v), b, len(v)) for b, v in br.items()), key=lambda x: x[0])
        def blink(b):
            return f'<a href="{url(brand_path[b])}">{E(b)}</a>' if b in brand_path else E(b)
        tr = "".join(f'<tr><td>{blink(b)}</td><td>{n}</td><td>{eur(round(a))}</td></tr>' for a, b, n in rows)
        out.append(f'<h2>Prix du {E(lab)} par enseigne {where}</h2><div class="tw"><table class="pt"><thead><tr><th>Enseigne</th><th>Stations</th><th>Prix moyen</th></tr></thead><tbody>{tr}</tbody></table></div>')
        faq.append((f"Quelle enseigne est la moins chère {where} ?",
                    f"Pour le {lab}, l'enseigne la moins chère en moyenne {where} est {rows[0][1]} ({eur(round(rows[0][0]))}), "
                    f"et la plus chère {rows[-1][1]} ({eur(round(rows[-1][0]))})."))
    # 24h/24 et services
    h24 = [i for i in idx if len(S[i]) > 11 and S[i][11]]
    if h24:
        names = ", ".join(E(S[i][8] or ("station " + S[i][4])) for i in h24[:8])
        out.append(f'<h2>Stations ouvertes 24h/24 {where}</h2><p class="prose">{len(h24)} station{"s" if len(h24) > 1 else ""} '
                   f'{where} {"disposent" if len(h24) > 1 else "dispose"} d\'un automate de paiement par carte accessible 24h/24 : {names}{"…" if len(h24) > 8 else ""}.</p>')
        faq.append((f"Peut-on faire le plein 24h/24 {where} ?",
                    f"Oui, {len(h24)} station{'s' if len(h24) > 1 else ''} {where} {'ont' if len(h24) > 1 else 'a'} un automate 24h/24."))
    elif any(len(S[i]) > 11 for i in idx) and SV:
        faq.append((f"Peut-on faire le plein 24h/24 {where} ?",
                    f"Aucune station {where} ne déclare d'automate 24h/24 dans les données officielles."))
    svc = {}
    for i in idx:
        for j in (S[i][10] if len(S[i]) > 10 else []):
            if j < len(SV):
                svc[SV[j]] = svc.get(SV[j], 0) + 1
    if svc:
        top = sorted(svc.items(), key=lambda x: -x[1])[:10]
        out.append('<h2>Services disponibles</h2><ul class="chips">' +
                   "".join(f"<li>{E(n)} <small>{c}</small></li>" for n, c in top) + "</ul>")
    # tendance departement
    if dep_series:
        ser = dep_series[main_k]
        sent = trend_sentence(ser, lab, f"dans le département {dep_name}")
        if sent:
            out.append(f'<h2>Tendance sur 4 mois dans le département</h2><p class="prose">{sent}</p>' +
                       mini_chart(ser, hstart, label=f"Prix moyen du {lab} dans le département {dep_name} sur 4 mois"))
            faq.append((f"Le prix du {lab} augmente-t-il dans le département {dep_name} ?", re.sub("<[^>]+>", "", sent)))
    if faq:
        out.append('<h2>Questions fréquentes</h2><div class="faq">' +
                   "".join(f"<h3>{E(q)}</h3><p>{E(a)}</p>" for q, a in faq) + "</div>")
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]} if faq else None
    return "\n".join(out), ld


# ------------------------------------------------------------------ construction
def main():
    src, out = sys.argv[1], sys.argv[2]
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "web"), out)
    shutil.copytree(os.path.join(src, "data"), os.path.join(out, "data"), dirs_exist_ok=True)
    D = json.load(open(os.path.join(src, "data", "stations.json")))
    H = json.load(open(os.path.join(src, "data", "history.json")))
    deps_geo = json.load(open(os.path.join(ROOT, "web", "data", "deps.json")))
    DEPN = {f["properties"]["c"]: f["properties"]["n"] for f in deps_geo["features"]}
    S = D["s"]
    SV = D.get("sv", [])
    DH, hstart = dept_history(src)
    upd = datetime.fromisoformat(D["u"])
    upd_txt = f"{fr_date(upd)} à {upd:%Hh%M}"
    today = upd.date()
    urls = []  # (path, priority)

    # --- statistiques nationales
    nat = {}
    for k in range(6):
        v = sorted(s[5][k] for s in S if s[5][k])
        if v:
            nat[k] = {"avg": sum(v) / len(v), "min": v[0], "max": v[-1], "n": len(v)}
    hist = H["f"]

    def hchange(key, days):
        a = hist[key]
        now = next((x for x in reversed(a) if x is not None), None)
        old = next((x for x in reversed(a[:len(a) - days]) if x is not None), None)
        return (now - old) if now and old else None

    # --- regroupements
    by_dep, by_city = {}, {}
    for i, s in enumerate(S):
        by_dep.setdefault(dep_of(s[2]), []).append(i)
        key = (s[2], slug(s[3]))
        by_city.setdefault(key, []).append(i)
    city_path = {}
    city_name = {}
    for (cp, sl), idx in by_city.items():
        names = {}
        for i in idx:
            names[S[i][3]] = names.get(S[i][3], 0) + 1
        nm = max(names, key=names.get)
        city_name[(cp, sl)] = nm
        city_path[(cp, sl)] = f"/ville/{sl}-{cp}/"
    dep_path = {d: f"/departement/{d.lower()}-{slug(DEPN.get(d, d))}/" for d in by_dep}
    centroid = {k: (sum(S[i][0] for i in v) / len(v), sum(S[i][1] for i in v) / len(v)) for k, v in by_city.items()}

    # --- communes regroupant plusieurs codes postaux (Paris, Lyon, Marseille, grandes villes)
    def base_name(n):
        m = re.match(r"^(paris|lyon|marseille)\b", slug(n))
        return m.group(1).title() if m else n
    agg = {}
    for key, idx in by_city.items():
        bn = base_name(city_name[key])
        agg.setdefault((slug(bn), dep_of(key[0])), {"name": bn, "keys": []})["keys"].append(key)
    agg = {k: v for k, v in agg.items() if len(v["keys"]) > 1}
    slug_deps = {}
    for (sl, d) in agg:
        slug_deps.setdefault(sl, []).append(d)
    agg_path, city_parent = {}, {}
    for (sl, d), v in agg.items():
        agg_path[(sl, d)] = f"/ville/{sl}/" if len(slug_deps[sl]) == 1 else f"/ville/{sl}-{d.lower()}/"
        for k in v["keys"]:
            city_parent[k] = (sl, d)

    def dep_avg(d, k):
        v = [S[i][5][k] for i in by_dep.get(d, []) if S[i][5][k]]
        return sum(v) / len(v) if len(v) >= 3 else None

    def cmp_nat(v, k):
        if v is None or k not in nat:
            return ""
        d = v - nat[k]["avg"]
        return (f'<span class="down">▼ {ct(d)} ct sous la moyenne nationale</span>' if d < 0
                else f'<span class="up">▲ {ct(d)} ct au-dessus de la moyenne nationale</span>')

    # --- enseignes
    by_brand = {}
    for i, s in enumerate(S):
        if s[9] and s[9] not in ("Indépendant",):
            by_brand.setdefault(s[9], []).append(i)
    by_brand = {b: v for b, v in by_brand.items() if len(v) >= 15}
    brand_path = {b: f"/enseigne/{slug(b)}/" for b in by_brand}

    # ------------------------------------------------ pages villes
    keys = list(by_city)
    for key in keys:
        idx = by_city[key]
        cp, sl = key
        nm = city_name[key]
        d = dep_of(cp)
        fk = [k for k in range(6) if any(S[i][5][k] for i in idx)]
        main_k = 0 if 0 in fk else fk[0]
        idx.sort(key=lambda i: (S[i][5][main_k] or 9e9))
        best = next((i for i in idx if S[i][5][main_k] and S[i][6][main_k] <= 7), idx[0])
        lat, lon = centroid[key]
        near = sorted((km(lat, lon, *centroid[o]), o) for o in keys if o != key and abs(centroid[o][0] - lat) < .3 and abs(centroid[o][1] - lon) < .45)[:10]
        cards = ""
        for k in fk:
            v = [S[i][5][k] for i in idx if S[i][5][k]]
            avg = sum(v) / len(v)
            cards += (f'<div class="card"><h3>{E(FUELS[k][1])}</h3><p class="big">{eur(min(v))}</p>'
                      f'<p>le moins cher · moyenne {eur(round(avg))}</p><p class="cmp">{cmp_nat(avg, k)}</p></div>')
        bs = S[best]
        bname = bs[8] or f"la station {bs[4]}"
        lead = (f"Le {fr_date(today)}, le {FUELS[main_k][3]} le moins cher à {E(nm)} ({cp}) est affiché à "
                f"<b>{eur(bs[5][main_k])}</b> chez {E(bname)}. Comparez les prix des {len(idx)} "
                f"station{'s' if len(idx) > 1 else ''}-service de la commune, à partir des prix officiels déclarés par les stations.")
        near_html = "".join(f'<li><a href="{url(city_path[o])}">{E(city_name[o])} ({o[0]})</a> <small>{dist:.0f} km</small></li>' for dist, o in near)
        extra, faq_ld = extra_sections(idx, S, f"à {nm}", main_k, DH.get(st_key(cp)), hstart, DEPN.get(d, d), SV, brand_path)
        body = f"""<h1>Prix des carburants à {E(nm)} ({cp})</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url(f'/?cp={cp}')}">Voir sur la carte</a></p>
<section class="cards">{cards}</section>
<h2>Toutes les stations-service à {E(nm)}</h2>
{price_table(idx, S, fk)}
<p class="note">Le prix le plus bas de chaque carburant est surligné. Cliquez sur une station pour l'ouvrir sur la carte, avec l'évolution de ses prix.</p>
{extra}
{f'<h2>Communes voisines</h2><ul class="links">{near_html}</ul>' if near_html else ''}
{f'<p><a href="{url(agg_path[city_parent[key]])}">Toutes les stations de {E(agg[city_parent[key]]["name"])} →</a></p>' if key in city_parent else ''}
<p><a href="{url(dep_path[d])}">Prix des carburants dans le département {E(DEPN.get(d, d))} ({d}) →</a></p>"""
        title = f"Prix essence et gazole à {nm} ({cp}) : stations les moins chères"
        desc_bits = ", ".join(f"{FUELS[k][1]} dès {eur(min(S[i][5][k] for i in idx if S[i][5][k]))}" for k in fk[:3])
        desc = f"{desc_bits} à {nm} ({cp}) le {fr_date(today)}. Comparez les prix des {len(idx)} stations-service, mis à jour automatiquement."
        ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": f"Stations-service à {nm}",
               "itemListElement": [{"@type": "ListItem", "position": j + 1, "item": {
                   "@type": "GasStation", "name": S[i][8] or f"Station {S[i][3]}",
                   "brand": S[i][9] or None,
                   "address": {"@type": "PostalAddress", "streetAddress": S[i][4], "postalCode": S[i][2],
                               "addressLocality": S[i][3], "addressCountry": "FR"},
                   "geo": {"@type": "GeoCoordinates", "latitude": S[i][0], "longitude": S[i][1]}}}
                   for j, i in enumerate(idx[:30])]}]
        for x in ld[0]["itemListElement"]:
            if not x["item"]["brand"]:
                del x["item"]["brand"]
        if faq_ld:
            ld.append(faq_ld)
        write(out, city_path[key], page(city_path[key], title, desc, body,
              [("Accueil", "/"), (DEPN.get(d, d), dep_path[d])] +
              ([(agg[city_parent[key]]["name"], agg_path[city_parent[key]])] if key in city_parent else []) +
              [(f"{nm} ({cp})" if key in city_parent else nm, city_path[key])], ld, upd_txt))
        urls.append((city_path[key], "0.6"))

    # ------------------------------------------------ pages communes regroupees
    for ak, v in agg.items():
        nm, d = v["name"], ak[1]
        idx = [i for k in v["keys"] for i in by_city[k]]
        fk = [k for k in range(6) if any(S[i][5][k] for i in idx)]
        main_k = 0 if 0 in fk else fk[0]
        idx.sort(key=lambda i: (S[i][5][main_k] or 9e9))
        bs = S[next((i for i in idx if S[i][5][main_k] and S[i][6][main_k] <= 7), idx[0])]
        cards = ""
        for k in fk:
            vals = [S[i][5][k] for i in idx if S[i][5][k]]
            avg = sum(vals) / len(vals)
            cards += (f'<div class="card"><h3>{E(FUELS[k][1])}</h3><p class="big">{eur(min(vals))}</p>'
                      f'<p>le moins cher · moyenne {eur(round(avg))}</p><p class="cmp">{cmp_nat(avg, k)}</p></div>')
        cps = sorted(v["keys"])
        cplinks = "".join(f'<li><a href="{url(city_path[k])}">{E(city_name[k])} ({k[0]})</a> <small>{len(by_city[k])} st.</small></li>' for k in cps)
        lead = (f"Le {fr_date(today)}, le {FUELS[main_k][3]} le moins cher à {E(nm)} est affiché à <b>{eur(bs[5][main_k])}</b> "
                f"chez {E(bs[8] or 'la station ' + bs[4])} ({bs[2]}). Comparez les prix des {len(idx)} stations-service de {E(nm)}, "
                f"à partir des prix officiels déclarés par les stations.")
        extra, faq_ld = extra_sections(idx, S, f"à {nm}", main_k, DH.get(st_key(cps[0][0])), hstart, DEPN.get(d, d), SV, brand_path)
        body = f"""<h1>Prix des carburants à {E(nm)}</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url(f'/?lat={centroid[cps[0]][0]:.4f}&lon={centroid[cps[0]][1]:.4f}&z=12')}">Voir sur la carte</a></p>
<section class="cards">{cards}</section>
<h2>Les stations-service de {E(nm)}, de la moins chère à la plus chère</h2>
{price_table(idx, S, fk, show_city=True)}
{extra}
<h2>Par code postal</h2><ul class="links">{cplinks}</ul>
<p><a href="{url(dep_path[d])}">Prix des carburants dans le département {E(DEPN.get(d, d))} ({d}) →</a></p>"""
        title = f"Prix essence et gazole à {nm} : stations les moins chères"
        desc = ", ".join(f"{FUELS[k][1]} dès {eur(min(S[i][5][k] for i in idx if S[i][5][k]))}" for k in fk[:3]) + \
               f" à {nm} le {fr_date(today)}. Comparez les {len(idx)} stations-service, prix mis à jour automatiquement."
        write(out, agg_path[ak], page(agg_path[ak], title, desc, body,
              [("Accueil", "/"), (DEPN.get(d, d), dep_path[d]), (nm, agg_path[ak])], [faq_ld] if faq_ld else None, upd_txt))
        urls.append((agg_path[ak], "0.7"))

    # ------------------------------------------------ pages departements
    for d, idx in by_dep.items():
        dn = DEPN.get(d, d)
        rows = ""
        for k in range(6):
            a = dep_avg(d, k)
            if a is None:
                continue
            v = [S[i][5][k] for i in idx if S[i][5][k]]
            rows += f'<tr><td><a href="{url("/" + FUELS[k][2] + "/")}">{E(FUELS[k][1])}</a></td><td>{eur(round(a))}</td><td>{eur(min(v))}</td><td>{eur(nat[k]["avg"].__round__())}</td><td>{cmp_nat(a, k)}</td></tr>'
        tops = ""
        for k in (0, 2, 3):
            ids = sorted([i for i in idx if S[i][5][k]], key=lambda i: S[i][5][k])
            if ids:
                tops += f'<h2>{E(FUELS[k][1])} : les 10 stations les moins chères du département</h2>' + price_table(ids, S, [k], show_city=True, limit=10)
        cities = sorted({k for k in by_city if dep_of(k[0]) == d}, key=lambda k: city_name[k])
        clinks = "".join(f'<li><a href="{url(city_path[c])}">{E(city_name[c])}</a> <small>{c[0]} · {len(by_city[c])} st.</small></li>' for c in cities)
        a0 = dep_avg(d, 0)
        lead = (f"{len(idx)} stations-service dans le département {E(dn)} ({d}). "
                + (f"Le gazole y coûte en moyenne <b>{eur(round(a0))}</b> le {fr_date(today)}, " + cmp_nat(a0, 0).replace('<span class="down">', '').replace('<span class="up">', '').replace('</span>', '').replace("▼ ", "soit ").replace("▲ ", "soit ") + "." if a0 else ""))
        extra, faq_ld = extra_sections(idx, S, f"dans le département {dn}", 0, DH.get("20" if d in ("2A", "2B") else d), hstart, dn, SV, brand_path)
        body = f"""<h1>Prix des carburants : {E(dn)} ({d})</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt}</p>
<div class="tw"><table class="pt"><thead><tr><th>Carburant</th><th>Moyenne</th><th>Le moins cher</th><th>Moyenne France</th><th>Écart</th></tr></thead><tbody>{rows}</tbody></table></div>
{tops}
{extra}
<h2>Prix par commune</h2><ul class="links cols">{clinks}</ul>"""
        title = f"Prix carburant {dn} ({d}) : gazole, SP95-E10, SP98 moins chers"
        desc = (f"Prix moyen du gazole dans le département {dn} : {eur(round(a0))} le {fr_date(today)}. " if a0 else "") + \
               f"Stations les moins chères et prix par commune, {len(idx)} stations comparées."
        write(out, dep_path[d], page(dep_path[d], title, desc, body,
              [("Accueil", "/"), ("Départements", "/departements/"), (dn, dep_path[d])], [faq_ld] if faq_ld else None, upd_txt))
        urls.append((dep_path[d], "0.7"))

    # ------------------------------------------------ index departements
    rows = ""
    for d in sorted(by_dep, key=lambda x: x.replace("2A", "20A").replace("2B", "20B")):
        cells = "".join(f"<td>{eur(round(a)) if (a := dep_avg(d, k)) else '—'}</td>" for k in (0, 2, 3, 1))
        rows += f'<tr><td>{d}</td><td><a href="{url(dep_path[d])}">{E(DEPN.get(d, d))}</a></td>{cells}<td>{len(by_dep[d])}</td></tr>'
    body = f"""<h1>Prix des carburants par département</h1>
<p class="lead">Prix moyen de chaque carburant dans les {len(by_dep)} départements de France métropolitaine, calculé sur toutes les stations-service le {fr_date(today)}.</p>
<p class="upd">Relevé du {upd_txt}</p>
<div class="tw"><table class="pt sortable"><thead><tr><th>N°</th><th>Département</th><th>Gazole</th><th>SP95-E10</th><th>SP98</th><th>SP95</th><th>Stations</th></tr></thead><tbody>{rows}</tbody></table></div>"""
    write(out, "/departements/", page("/departements/", "Prix de l'essence et du gazole par département",
          "Comparez le prix moyen du gazole, du SP95-E10 et du SP98 dans chaque département de France, actualisé automatiquement à partir des données officielles.",
          body, [("Accueil", "/"), ("Départements", "/departements/")], None, upd_txt))
    urls.append(("/departements/", "0.8"))

    # ------------------------------------------------ pages carburants
    for k, (key, lab, sl, full) in enumerate(FUELS):
        if k not in nat:
            continue
        n = nat[k]
        ch = {lbl: hchange(key, dd) for lbl, dd in (("7 jours", 7), ("1 mois", 30), ("1 an", 365))}
        chg = " · ".join(f"{lbl} : " + (f'<span class="{"up" if v > 0 else "down"}">{"▲ +" if v > 0 else "▼ −"}{ct(v)} ct</span>' if v is not None else "—") for lbl, v in ch.items())
        last365 = hist[key][-365:]
        ids = sorted([i for i in range(len(S)) if S[i][5][k] and S[i][6][k] <= 7], key=lambda i: S[i][5][k])
        drows = sorted(((dep_avg(d, k), d) for d in by_dep if dep_avg(d, k)), key=lambda x: x[0])
        dt = "".join(f'<tr><td>{j + 1}</td><td><a href="{url(dep_path[d])}">{E(DEPN.get(d, d))} ({d})</a></td><td>{eur(round(a))}</td></tr>' for j, (a, d) in enumerate(drows))
        body = f"""<h1>Prix du {E(full)} aujourd'hui en France</h1>
<p class="lead">Le {fr_date(today)}, le {E(full)} coûte en moyenne <b>{eur(round(n['avg']))}</b> le litre en France métropolitaine, de {eur(n['min'])} à {eur(n['max'])} selon les stations ({n['n']:,} stations le proposent).</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url('/?carburant=' + key)}">Voir la carte du {E(lab)}</a></p>
<section class="cards"><div class="card"><h3>Moyenne nationale</h3><p class="big">{eur(round(n['avg']))}</p><p>{chg}</p></div>
<div class="card"><h3>Le moins cher</h3><p class="big">{eur(n['min'])}</p><p>{E(S[ids[0]][8] or S[ids[0]][3]) + ' · ' + E(S[ids[0]][3]) if ids else ''}</p></div>
<div class="card"><h3>Département le moins cher</h3><p class="big">{eur(round(drows[0][0])) if drows else '—'}</p><p>{E(DEPN.get(drows[0][1], '')) if drows else ''}</p></div></section>
<h2>Évolution du prix moyen sur 12 mois</h2>
{spark_svg(last365)}
<h2>Les 20 stations les moins chères de France</h2>
<p class="note">Prix mis à jour dans les 7 derniers jours.</p>
{price_table(ids, S, [k], show_city=True, limit=20)}
<h2>Prix moyen du {E(full)} par département</h2>
<div class="tw"><table class="pt"><thead><tr><th>Rang</th><th>Département</th><th>Prix moyen</th></tr></thead><tbody>{dt}</tbody></table></div>""".replace(f"{n['n']:,}", f"{n['n']:,}".replace(",", " "))
        title = f"Prix du {full} aujourd'hui : {eur(round(n['avg']))} en moyenne en France"
        desc = f"Prix moyen du {full} le {fr_date(today)} : {eur(round(n['avg']))}. Stations les moins chères, évolution sur 12 mois et classement des départements."
        write(out, f"/{sl}/", page(f"/{sl}/", title, desc, body, [("Accueil", "/"), (f"Prix du {lab}", f"/{sl}/")],
              [{"@context": "https://schema.org", "@type": "Dataset", "name": f"Prix du {full} en France",
                "description": desc, "url": SITE_URL + f"/{sl}/", "creator": {"@type": "Organization", "name": SITE_NAME},
                "isBasedOn": "https://www.prix-carburants.gouv.fr/rubrique/opendata/", "license": "https://www.etalab.gouv.fr/licence-ouverte-open-licence",
                "temporalCoverage": f"2017-01-01/{today.isoformat()}", "spatialCoverage": "France métropolitaine"}], upd_txt))
        urls.append((f"/{sl}/", "0.9"))

    # ------------------------------------------------ enseignes
    brows = []
    for b, idx in by_brand.items():
        avgs = {}
        for k in range(6):
            v = [S[i][5][k] for i in idx if S[i][5][k]]
            if len(v) >= 5:
                avgs[k] = sum(v) / len(v)
        brows.append((b, idx, avgs))
    brows.sort(key=lambda x: x[2].get(0, 9e9))
    for rank, (b, idx, avgs) in enumerate(brows):
        cards = "".join(f'<div class="card"><h3>{E(FUELS[k][1])}</h3><p class="big">{eur(round(a))}</p><p>prix moyen chez {E(b)}</p><p class="cmp">{cmp_nat(a, k)}</p></div>' for k, a in avgs.items())
        tops = ""
        for k in (0, 2, 3):
            ids = sorted([i for i in idx if S[i][5][k] and S[i][6][k] <= 7], key=lambda i: S[i][5][k])
            if ids:
                tops += f"<h2>{E(FUELS[k][1])} : les 15 stations {E(b)} les moins chères</h2>" + price_table(ids, S, [k], show_city=True, limit=15)
        dd = {}
        for i in idx:
            if S[i][5][0]:
                dd.setdefault(dep_of(S[i][2]), []).append(S[i][5][0])
        drows = sorted(((sum(v) / len(v), d, len(v)) for d, v in dd.items() if len(v) >= 3))
        dtab = "".join(f'<tr><td><a href="{url(dep_path[d])}">{E(DEPN.get(d, d))} ({d})</a></td><td>{n}</td><td>{eur(round(a))}</td></tr>' for a, d, n in drows)
        g = avgs.get(0)
        lead = (f"{len(idx)} stations {E(b)} en France métropolitaine. " +
                (f"Le {fr_date(today)}, le gazole y coûte en moyenne <b>{eur(round(g))}</b> le litre, "
                 f"ce qui place {E(b)} au <b>{rank + 1}<sup>e</sup> rang</b> des {len(brows)} enseignes les moins chères pour le gazole." if g else ""))
        body = f"""<h1>Prix des carburants chez {E(b)}</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url('/enseignes/')}">Comparer toutes les enseignes</a></p>
<section class="cards">{cards}</section>
{tops}
{f'<h2>Prix moyen du gazole chez {E(b)} par département</h2><div class="tw"><table class="pt"><thead><tr><th>Département</th><th>Stations</th><th>Prix moyen</th></tr></thead><tbody>{dtab}</tbody></table></div>' if dtab else ''}"""
        title = f"Prix carburant {b} aujourd'hui : gazole, SP95-E10, SP98"
        desc = (f"Gazole à {eur(round(g))} en moyenne chez {b} le {fr_date(today)}. " if g else "") + \
               f"Les stations {b} les moins chères et les prix par département, comparés aux autres enseignes."
        write(out, brand_path[b], page(brand_path[b], title, desc, body,
              [("Accueil", "/"), ("Enseignes", "/enseignes/"), (b, brand_path[b])], None, upd_txt))
        urls.append((brand_path[b], "0.8"))
    tr = ""
    for rank, (b, idx, avgs) in enumerate(brows):
        tr += (f'<tr><td>{rank + 1}</td><td><a href="{url(brand_path[b])}">{E(b)}</a></td><td>{len(idx)}</td>' +
               "".join(f"<td>{eur(round(avgs[k])) if k in avgs else '—'}</td>" for k in (0, 2, 3)) + "</tr>")
    cheap_b = brows[0][0] if brows else ""
    cheap_txt = f"En ce moment, <b>{E(cheap_b)}</b> est l'enseigne la moins chère pour le gazole." if cheap_b else ""
    body = f"""<h1>Quelle enseigne a le carburant le moins cher ?</h1>
<p class="lead">Classement des enseignes de stations-service selon le prix moyen du gazole le {fr_date(today)}, calculé sur toutes leurs stations en France métropolitaine. {cheap_txt}</p>
<p class="upd">Relevé du {upd_txt}</p>
<div class="tw"><table class="pt"><thead><tr><th>Rang</th><th>Enseigne</th><th>Stations</th><th>Gazole</th><th>SP95-E10</th><th>SP98</th></tr></thead><tbody>{tr}</tbody></table></div>
<p class="note">Enseignes de plus de 15 stations. Les noms et enseignes proviennent d'OpenStreetMap et sont connus pour environ 8 stations sur 10.</p>"""
    write(out, "/enseignes/", page("/enseignes/", "Carburant le moins cher : classement des enseignes (Leclerc, Intermarché, Total…)",
          f"Quelle enseigne vend le carburant le moins cher ? Prix moyen du gazole, du SP95-E10 et du SP98 chez Leclerc, Intermarché, Carrefour, TotalEnergies, Système U… le {fr_date(today)}.",
          body, [("Accueil", "/"), ("Enseignes", "/enseignes/")], None, upd_txt))
    urls.append(("/enseignes/", "0.9"))

    # ------------------------------------------------ autoroute
    A = [i for i, s in enumerate(S) if len(s) > 12 and s[12]]
    if len(A) >= 20:
        rows = ""
        for k in range(6):
            va = [S[i][5][k] for i in A if S[i][5][k]]
            vr = [s[5][k] for s in S if s[5][k] and not (len(s) > 12 and s[12])]
            if len(va) >= 5 and vr:
                a1, a2 = sum(va) / len(va), sum(vr) / len(vr)
                rows += f"<tr><td>{E(FUELS[k][1])}</td><td>{eur(round(a1))}</td><td>{eur(round(a2))}</td><td class=\"up\">+{ct(a1 - a2)} ct</td><td>+{fmt2((a1 - a2) * TANK / 1000)} €</td></tr>"
        ids = sorted([i for i in A if S[i][5][0]], key=lambda i: S[i][5][0])
        g_a = [S[i][5][0] for i in A if S[i][5][0]]
        g_r = [s[5][0] for s in S if s[5][0] and not (len(s) > 12 and s[12])]
        diff = (sum(g_a) / len(g_a) - sum(g_r) / len(g_r)) if g_a and g_r else 0
        body = f"""<h1>Prix du carburant sur autoroute</h1>
<p class="lead">Le {fr_date(today)}, le gazole coûte en moyenne <b>{ct(diff)} centimes de plus par litre</b> sur les aires d'autoroute qu'ailleurs, soit environ {str(round(diff * TANK / 1000, 2)).replace('.', ',')} € de plus pour un plein de {TANK} litres. Voici les prix des {len(A)} stations d'autoroute, de la moins chère à la plus chère.</p>
<p class="upd">Relevé du {upd_txt}</p>
<div class="tw"><table class="pt"><thead><tr><th>Carburant</th><th>Sur autoroute</th><th>Hors autoroute</th><th>Écart / litre</th><th>Écart / plein</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Conseil</h2><p class="prose">Sur un long trajet, faire le plein juste avant d'entrer sur l'autoroute ou à une sortie, dans une station de supermarché proche, revient presque toujours moins cher. Utilisez la <a href="{url('/')}">carte</a> pour repérer les stations proches des sorties.</p>
<h2>Les stations d'autoroute, de la moins chère à la plus chère (gazole)</h2>
{price_table(ids, S, [k for k in (0, 2, 3) if any(S[i][5][k] for i in A)], show_city=True)}"""
        write(out, "/prix-carburant-autoroute/", page("/prix-carburant-autoroute/", "Prix de l'essence et du gazole sur autoroute : l'écart avec les autres stations",
              f"Sur autoroute, le gazole coûte {ct(diff)} ct de plus par litre en moyenne le {fr_date(today)}. Prix de toutes les stations d'autoroute, de la moins chère à la plus chère.",
              body, [("Accueil", "/"), ("Autoroute", "/prix-carburant-autoroute/")], None, upd_txt))
        urls.append(("/prix-carburant-autoroute/", "0.9"))

    # ------------------------------------------------ actualites hebdomadaires
    h0 = date.fromisoformat(H["start"])
    nH = len(hist["Gazole"])
    last_day = h0 + timedelta(days=nH - 1)
    week_end = last_day - timedelta(days=(last_day.weekday() + 1) % 7)  # dernier dimanche complet
    weeks = []
    for w in range(26):
        e = week_end - timedelta(days=7 * w)
        s0 = e - timedelta(days=6)
        weeks.append((s0, e))

    def wavg(key, s0, e):
        a, b = (s0 - h0).days, (e - h0).days
        v = [x for x in hist[key][max(a, 0):b + 1] if x]
        return sum(v) / len(v) if v else None

    def wlabel(s0, e):
        return (f"du {s0.day} au {e.day} {MONTHS[e.month - 1]} {e.year}" if s0.month == e.month
                else f"du {s0.day} {MONTHS[s0.month - 1]} au {e.day} {MONTHS[e.month - 1]} {e.year}")
    news = []
    for s0, e in weeks:
        prev = (s0 - timedelta(days=7), e - timedelta(days=7))
        ly = (s0 - timedelta(days=364), e - timedelta(days=364))
        rows, head = "", ""
        g_now, g_prev = wavg("Gazole", s0, e), wavg("Gazole", *prev)
        if not g_now or not g_prev:
            continue
        for k, (key, lab, sl, full) in enumerate(FUELS):
            a, b, c = wavg(key, s0, e), wavg(key, *prev), wavg(key, *ly)
            if not a:
                continue
            d1 = f'<span class="{"up" if a > b else "down"}">{"▲ +" if a > b else "▼ −"}{ct(a - b)} ct</span>' if b else "—"
            d2 = f'<span class="{"up" if a > c else "down"}">{"▲ +" if a > c else "▼ −"}{ct(a - c)} ct</span>' if c else "—"
            rows += f'<tr><td><a href="{url("/" + sl + "/")}">{E(lab)}</a></td><td>{eur(round(a))}</td><td>{d1}</td><td>{d2}</td></tr>'
        dg = g_now - g_prev
        verb = "grimpe" if dg >= 20 else "augmente" if dg >= 5 else "augmente légèrement" if dg > 1 else "chute" if dg <= -20 else "baisse" if dg <= -5 else "recule légèrement" if dg < -1 else "reste stable"
        headline = f"Le gazole {verb}" + (f" de {ct(dg)} centime{'s' if abs(dg) >= 15 else ''}" if abs(dg) > 1 else "") + f" : {eur(round(g_now))} en moyenne"
        slug_w = f"/actualites/{e.isocalendar()[0]}-semaine-{e.isocalendar()[1]:02d}/"
        a0, b0 = (s0 - h0).days, (e - h0).days
        ser = hist["Gazole"][max(a0 - 49, 0):b0 + 1]
        body = f"""<h1>Prix des carburants {wlabel(s0, e)}</h1>
<p class="lead">{headline} sur la semaine {wlabel(s0, e)}, contre {eur(round(g_prev))} la semaine précédente. Voici l'évolution du prix moyen de chaque carburant en France métropolitaine, calculée sur toutes les stations-service.</p>
<div class="tw"><table class="pt"><thead><tr><th>Carburant</th><th>Prix moyen de la semaine</th><th>vs semaine précédente</th><th>vs il y a un an</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Le gazole sur les 8 dernières semaines</h2>
{mini_chart(ser, s0 - timedelta(days=49) if a0 >= 49 else h0, label="Prix moyen du gazole sur 8 semaines")}
<p class="prose">Pour trouver la station la moins chère près de chez vous aujourd'hui, consultez la <a href="{url('/')}">carte des prix</a> ou le <a href="{url('/enseignes/')}">classement des enseignes</a>.</p>"""
        write(out, slug_w, page(slug_w, f"Prix des carburants {wlabel(s0, e)} : {headline.lower()}",
              f"{headline} sur la semaine {wlabel(s0, e)}. Évolution du prix du gazole, du SP95-E10, du SP98, de l'E85 et du GPL en France.",
              body, [("Accueil", "/"), ("Actualités", "/actualites/"), (f"Semaine {wlabel(s0, e)}", slug_w)],
              [{"@context": "https://schema.org", "@type": "NewsArticle", "headline": f"Prix des carburants {wlabel(s0, e)}",
                "datePublished": (e + timedelta(days=1)).isoformat(), "dateModified": (e + timedelta(days=1)).isoformat(),
                "author": {"@type": "Organization", "name": SITE_NAME}, "publisher": {"@type": "Organization", "name": SITE_NAME},
                "image": SITE_URL + "/assets/og.png", "mainEntityOfPage": SITE_URL + slug_w}]))
        urls.append((slug_w, "0.6"))
        news.append((s0, e, headline, slug_w))
    items = "".join(f'<li><a href="{url(p_)}"><b>Semaine {wlabel(s0, e)}</b></a><br><span>{E(h)}</span></li>' for s0, e, h, p_ in news)
    body = f"""<h1>Actualités des prix des carburants</h1>
<p class="lead">Chaque semaine, le bilan de l'évolution des prix du gazole et de l'essence en France, calculé sur toutes les stations-service à partir des prix officiels.</p>
<ul class="news">{items}</ul>"""
    write(out, "/actualites/", page("/actualites/", "Actualités des prix des carburants : le bilan de chaque semaine",
          "Évolution des prix du gazole, du SP95-E10 et du SP98 semaine après semaine en France : hausses, baisses et comparaison avec l'an dernier.",
          body, [("Accueil", "/"), ("Actualités", "/actualites/")], None, upd_txt))
    urls.append(("/actualites/", "0.8"))

    # ------------------------------------------------ widget pour les sites partenaires
    body = f"""<h1>Widget des prix à intégrer sur votre site</h1>
<p class="lead">Mairie, club, blog local, commerce : affichez gratuitement les stations les moins chères de votre commune sur votre site. Les prix se mettent à jour tout seuls.</p>
<div class="wg">
  <label for="wcp">Code postal</label>
  <div class="wrow"><input id="wcp" inputmode="numeric" maxlength="5" value="75015"><select id="wfu" aria-label="Carburant">{''.join(f'<option value="{k}">{E(FUELS[k][1])}</option>' for k in range(6))}</select></div>
  <iframe id="wprev" title="Aperçu du widget" src="{url('/widget/embed.html?cp=75015&amp;c=0')}" width="100%" height="330" loading="lazy" style="border:1px solid var(--line);border-radius:12px;max-width:420px;display:block;margin-top:14px"></iframe>
  <label for="wcode" style="margin-top:16px;display:block">Code à coller sur votre site</label>
  <textarea id="wcode" rows="5" readonly></textarea>
  <button type="button" id="wcopy" class="btn">Copier le code</button>
</div>
<script>
(function(){{var cp=document.getElementById('wcp'),fu=document.getElementById('wfu'),pv=document.getElementById('wprev'),code=document.getElementById('wcode');
function up(){{var c=(cp.value||'').replace(/\\D/g,'').slice(0,5);var src='{SITE_URL}/widget/embed.html?cp='+c+'&c='+fu.value;
if(c.length===5)pv.src=src;
code.value='<iframe src="'+src+'" width="100%" height="330" style="border:0;max-width:420px" loading="lazy" title="Prix des carburants"></iframe>\\n<p style="font:12px sans-serif">Prix des carburants : <a href="{SITE_URL}/">Prix à la Pompe</a></p>';}}
cp.addEventListener('input',up);fu.addEventListener('change',up);up();
document.getElementById('wcopy').onclick=function(){{code.select();(navigator.clipboard?navigator.clipboard.writeText(code.value):Promise.reject()).then(function(){{document.getElementById('wcopy').textContent='Code copié'}},function(){{document.execCommand&&document.execCommand('copy')}})}};}})();
</script>"""
    write(out, "/widget/", page("/widget/", "Widget gratuit des prix des carburants pour votre site",
          "Affichez gratuitement sur votre site les stations-service les moins chères de votre commune, avec des prix mis à jour automatiquement.",
          body, [("Accueil", "/"), ("Widget", "/widget/")], None, upd_txt))
    urls.append(("/widget/", "0.4"))
    fuels_js = json.dumps([f[1] for f in FUELS], ensure_ascii=False)
    embed = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Prix des carburants</title>
<style>body{{margin:0;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;color:#161B2E;background:#fff}}
.h{{height:4px;background:linear-gradient(90deg,#1F3A93 0 33.3%,#fff 33.3% 66.6%,#D42A2F 66.6%)}}
.t{{padding:10px 12px 6px;font-weight:700;color:#1F3A93}}.t small{{display:block;font-weight:400;color:#5C6480}}
ol{{list-style:none;margin:0;padding:0 12px}}li{{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-top:1px solid #E8ECF4}}
li b{{font-weight:600}}li span{{display:block;font-size:12px;color:#5C6480}}li i{{font:600 15px ui-monospace,Menlo,monospace;font-style:normal;color:#1E8C6E;white-space:nowrap}}
a.f{{display:block;padding:8px 12px;font-size:12px;color:#1F3A93;text-decoration:none;border-top:1px solid #E8ECF4}}</style></head>
<body><div class="h"></div><div class="t" id="t">Chargement…</div><ol id="l"></ol><a class="f" id="f" href="{SITE_URL}/" target="_blank" rel="noopener">Tous les prix sur Prix à la Pompe →</a>
<script>
(function(){{var F={fuels_js};var q=new URLSearchParams(location.search),cp=(q.get('cp')||'').slice(0,5),k=Math.min(5,Math.max(0,+q.get('c')||0));
function km(a,b,c,d){{var r=Math.PI/180,x=Math.pow(Math.sin((c-a)*r/2),2)+Math.cos(a*r)*Math.cos(c*r)*Math.pow(Math.sin((d-b)*r/2),2);return 12742*Math.asin(Math.sqrt(x))}}
function e(s){{return String(s).replace(/[&<>"]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}})}}
fetch('../data/stations.json').then(function(r){{return r.json()}}).then(function(D){{var S=D.s,here=S.filter(function(s){{return s[2]===cp}});
if(!here.length){{document.getElementById('t').textContent='Code postal introuvable';return}}
var la=here.reduce(function(a,s){{return a+s[0]}},0)/here.length,lo=here.reduce(function(a,s){{return a+s[1]}},0)/here.length;
var list=S.filter(function(s){{return s[5][k]&&km(la,lo,s[0],s[1])<=8}}).sort(function(a,b){{return a[5][k]-b[5][k]}}).slice(0,6);
document.getElementById('t').innerHTML=e(F[k])+' le moins cher près de '+e(here[0][3])+'<small>Prix officiels · à 8 km maximum</small>';
document.getElementById('l').innerHTML=list.map(function(s){{return '<li><div><b>'+e(s[8]||('Station '+s[3]))+'</b><span>'+e(s[4])+', '+e(s[3])+'</span></div><i>'+(s[5][k]/1000).toFixed(3).replace('.',',')+' €</i></li>'}}).join('');
document.getElementById('f').href='{SITE_URL}/?cp='+cp;}}).catch(function(){{document.getElementById('t').textContent='Prix indisponibles'}});}})();
</script></body></html>"""
    write(out, "/widget/embed.html", embed, raw=True)

    # ------------------------------------------------ a propos
    body = f"""<h1>Sources et méthode</h1>
<div class="prose">
<p><b>{SITE_NAME}</b> affiche les prix des carburants de toutes les stations-service de France métropolitaine ({len(S):,} stations aujourd'hui) sur une carte, avec l'évolution des prix depuis 2017.</p>
<h2>D'où viennent les prix ?</h2>
<p>Les stations-service sont tenues par la loi de déclarer leurs prix. Ils sont publiés en données ouvertes par le Ministère de l'Économie sur <a href="https://www.prix-carburants.gouv.fr/rubrique/opendata/" rel="noopener">prix-carburants.gouv.fr</a>, sous Licence Ouverte. Le site se met à jour automatiquement plusieurs fois par heure à partir de ce flux officiel. L'historique depuis 2017 provient des archives du même service, via le projet ouvert <a href="https://github.com/MikeColombet/prix-essence-nord" rel="noopener">prix-essence-nord</a>.</p>
<h2>Comment sont calculées les moyennes ?</h2>
<p>La moyenne d'un jour est la moyenne des derniers prix déclarés par chaque station. Un prix non mis à jour depuis plus de 30 jours n'est plus pris en compte, et il n'est pas affiché sur la carte.</p>
<h2>Noms et enseignes des stations</h2>
<p>Le flux officiel ne contient ni le nom ni l'enseigne des stations. Ils proviennent d'OpenStreetMap, via le projet <a href="https://github.com/Aohzan/hass-prixcarburant" rel="noopener">hass-prixcarburant</a>, et sont connus pour environ 8 stations sur 10.</p>
<h2>Vos données</h2>
<p>L'adresse et les stations favorites que vous enregistrez dans « Mon espace » restent dans votre navigateur. Elles ne sont envoyées nulle part.</p>
</div>""".replace(f"{len(S):,}", f"{len(S):,}".replace(",", " "))
    write(out, "/a-propos/", page("/a-propos/", "Sources et méthode – Prix à la Pompe",
          "D'où viennent les prix des carburants affichés, comment sont calculées les moyennes et à quelle fréquence le site est mis à jour.",
          body, [("Accueil", "/"), ("Sources et méthode", "/a-propos/")], None, upd_txt))
    urls.append(("/a-propos/", "0.3"))

    # ------------------------------------------------ accueil (application + contenu indexable)
    tpl = open(os.path.join(ROOT, "scripts", "app_template.html")).read()
    tpl = re.sub(r"<title>.*?</title>\n?", "", tpl, count=1)
    tpl = tpl.replace("<style>\n/*LEAFLET_CSS*/\n</style>",
                      '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">')
    fuel_links = "".join(
        f'<a class="fl" href="{url("/" + sl + "/")}"><b>{E(lab)}</b><span>{eur(round(nat[k]["avg"]))}</span><small>moyenne France</small></a>'
        for k, (key, lab, sl, full) in enumerate(FUELS) if k in nat)
    places = [(len([i for k in v["keys"] for i in by_city[k]]), v["name"], agg_path[ak]) for ak, v in agg.items()]
    places += [(len(idx), city_name[k], city_path[k]) for k, idx in by_city.items() if k not in city_parent]
    big = sorted(places, key=lambda x: -x[0])[:48]
    big_links = "".join(f'<li><a href="{url(p)}">{E(n)}</a></li>' for c, n, p in sorted(big, key=lambda x: slug(x[1])))
    dep_links = "".join(f'<li><a href="{url(dep_path[d])}">{E(DEPN.get(d, d))} <small>({d})</small></a></li>'
                        for d in sorted(by_dep, key=lambda x: x.replace("2A", "20A").replace("2B", "20B")))
    seo = f"""<section class="trends seo" id="guide">
  <div class="sec-h"><div><h2>Prix des carburants en France</h2>
  <p>Le {fr_date(today)}, le gazole coûte en moyenne {eur(round(nat[0]['avg']))} le litre, le SP95-E10 {eur(round(nat[2]['avg']))} et le SP98 {eur(round(nat[3]['avg']))}. {SITE_NAME} compare les prix officiels de {len(S):,} stations-service, actualisés automatiquement tout au long de la journée.</p></div></div>
  <div class="fuel-links">{fuel_links}</div>
  <div class="seo-cols">
    <div><h3>Prix par ville</h3><ul class="seo-list">{big_links}</ul></div>
    <div><h3>Prix par département</h3><ul class="seo-list dense">{dep_links}</ul></div>
  </div>
  <p class="seo-more"><a href="{url('/enseignes/')}">Quelle enseigne est la moins chère ?</a> · <a href="{url('/prix-carburant-autoroute/')}">Prix sur autoroute</a> · <a href="{url('/actualites/')}">Actualités de la semaine</a> · <a href="{url('/departements/')}">Tous les départements</a> · <a href="{url('/widget/')}">Widget pour votre site</a> · <a href="{url('/a-propos/')}">Sources et méthode</a></p>
</section>""".replace(f"{len(S):,}", f"{len(S):,}".replace(",", " "))
    seo_css = """<style>
.seo .fuel-links{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.seo .fl{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;text-decoration:none;color:var(--ink);display:flex;flex-direction:column;gap:2px;box-shadow:var(--shadow)}
.seo .fl:hover{border-color:var(--accent)}
.seo .fl b{font-family:var(--font-display);font-size:18px;text-transform:uppercase;color:var(--bleu)}
.seo .fl span{font:600 20px var(--font-mono)}
.seo .fl small{color:var(--muted);font-size:12px}
.seo-cols{display:grid;grid-template-columns:1fr 2fr;gap:24px}
.seo-cols h3{margin:0 0 8px;font-size:15px;color:var(--bleu)}
.seo-list{list-style:none;margin:0;padding:0;columns:2;column-gap:20px;font-size:13px;line-height:1.9}
.seo-list.dense{columns:3}
.seo-list a{color:var(--ink-2);text-decoration:none}.seo-list a:hover{color:var(--accent);text-decoration:underline}
.seo-list small{color:var(--muted)}
.seo-more a{color:var(--accent)}
@media (max-width:860px){.seo .fuel-links{grid-template-columns:repeat(2,1fr)}.seo-cols{grid-template-columns:1fr}.seo-list.dense{columns:2}}
</style>"""
    home_title = "Prix de l'essence et du gazole aujourd'hui : carte des stations les moins chères"
    home_desc = (f"Gazole {eur(round(nat[0]['avg']))}, SP95-E10 {eur(round(nat[2]['avg']))}, SP98 {eur(round(nat[3]['avg']))} en moyenne le {fr_date(today)}. "
                 f"Trouvez la station-service la moins chère près de chez vous parmi {len(S)} stations, prix officiels actualisés en continu.")
    head = page("/", home_title, home_desc, "", None, [
        {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "inLanguage": "fr-FR"},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": SITE_NAME, "url": SITE_URL + "/",
         "applicationCategory": "TravelApplication", "operatingSystem": "Web", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
         "description": home_desc}])
    head = head[:head.index("<body>")].replace(f'<link rel="stylesheet" href="{url("/assets/site.css")}">\n', "")
    head = head.replace("</head>", f'<link rel="preload" href="{url("/data/stations.json")}" as="fetch" crossorigin>\n</head>')
    home = head + "<body>\n" + tpl.replace("<!--SEO-->", seo) + seo_css + "\n</body>\n</html>\n"
    write(out, "/", home)
    urls.insert(0, ("/", "1.0"))

    # ------------------------------------------------ 404, sitemap, robots
    write(out, "/404.html", page("/404.html", "Page introuvable – Prix à la Pompe", "Cette page n'existe pas.",
          f'<h1>Page introuvable</h1><p class="lead">Cette page n\'existe pas ou plus. <a href="{url("/")}">Retour à la carte des prix</a>.</p>'), raw=True)
    lm = today.isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{SITE_URL}{p}</loc><lastmod>{lm}</lastmod><changefreq>hourly</changefreq><priority>{pr}</priority></url>" for p, pr in urls]
    sm.append("</urlset>")
    open(os.path.join(out, "sitemap.xml"), "w").write("\n".join(sm))
    open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    open(os.path.join(out, ".nojekyll"), "w").write("")
    open(os.path.join(out, "llms.txt"), "w").write(
        f"# {SITE_NAME}\n\n> Prix officiels de l'essence et du gazole dans les {len(S)} stations-service de France métropolitaine, "
        f"actualisés toutes les 30 minutes (source : prix-carburants.gouv.fr).\n\n"
        f"- [Carte des stations]({SITE_URL}/)\n- [Prix du gazole aujourd'hui]({SITE_URL}/prix-gazole/)\n"
        f"- [Prix du SP95-E10]({SITE_URL}/prix-sp95-e10/)\n- [Prix du SP98]({SITE_URL}/prix-sp98/)\n"
        f"- [Classement des enseignes]({SITE_URL}/enseignes/)\n- [Prix sur autoroute]({SITE_URL}/prix-carburant-autoroute/)\n"
        f"- [Prix par département]({SITE_URL}/departements/)\n- [Actualités hebdomadaires]({SITE_URL}/actualites/)\n"
        f"- [Sources et méthode]({SITE_URL}/a-propos/)\n")
    print(f"OK pages={len(urls)} villes={len(by_city)} departements={len(by_dep)} site={SITE_URL}")


def write(out, path, content, raw=False):
    if raw or path.endswith(".html"):
        fp = os.path.join(out, path.lstrip("/"))
    else:
        fp = os.path.join(out, path.lstrip("/"), "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)


if __name__ == "__main__":
    main()
