#!/usr/bin/env python3
"""Construit le site statique « Prix à la Pompe » (GitHub Pages).

Usage : SITE_URL=https://pseudo.github.io/prix-a-la-pompe python3 build_site.py <donnees> <sortie>

<donnees> : dossier produit par build_data.py (contient data/stations.json, ...)
<sortie>  : dossier publie (index.html, pages villes / departements / carburants,
            sitemap.xml, robots.txt, donnees de la carte).
Bibliotheque standard uniquement.
"""
import json, os, re, sys, shutil, unicodedata, math, html
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
              ("SP98", "/prix-sp98/"), ("Départements", "/departements/")]


def page(path, title, desc, body, crumbs=None, jsonld=None, updated=None):
    canon = SITE_URL + path
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
<meta name="robots" content="index,follow,max-image-preview:large">
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
<p><a href="{url('/departements/')}">Tous les départements</a> · <a href="{url('/a-propos/')}">Sources et méthode</a> · Noms des stations : OpenStreetMap via hass-prixcarburant.</p>
</div></footer>
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
        best = idx[0]
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
        body = f"""<h1>Prix des carburants à {E(nm)} ({cp})</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url(f'/?cp={cp}')}">Voir sur la carte</a></p>
<section class="cards">{cards}</section>
<h2>Toutes les stations-service à {E(nm)}</h2>
{price_table(idx, S, fk)}
<p class="note">Le prix le plus bas de chaque carburant est surligné. Cliquez sur une station pour l'ouvrir sur la carte, avec l'évolution de ses prix.</p>
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
        bs = S[idx[0]]
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
        body = f"""<h1>Prix des carburants à {E(nm)}</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt} · <a class="btn" href="{url(f'/?lat={centroid[cps[0]][0]:.4f}&lon={centroid[cps[0]][1]:.4f}&z=12')}">Voir sur la carte</a></p>
<section class="cards">{cards}</section>
<h2>Les stations-service de {E(nm)}, de la moins chère à la plus chère</h2>
{price_table(idx, S, fk, show_city=True)}
<h2>Par code postal</h2><ul class="links">{cplinks}</ul>
<p><a href="{url(dep_path[d])}">Prix des carburants dans le département {E(DEPN.get(d, d))} ({d}) →</a></p>"""
        title = f"Prix essence et gazole à {nm} : stations les moins chères"
        desc = ", ".join(f"{FUELS[k][1]} dès {eur(min(S[i][5][k] for i in idx if S[i][5][k]))}" for k in fk[:3]) + \
               f" à {nm} le {fr_date(today)}. Comparez les {len(idx)} stations-service, prix mis à jour automatiquement."
        write(out, agg_path[ak], page(agg_path[ak], title, desc, body,
              [("Accueil", "/"), (DEPN.get(d, d), dep_path[d]), (nm, agg_path[ak])], None, upd_txt))
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
        body = f"""<h1>Prix des carburants : {E(dn)} ({d})</h1>
<p class="lead">{lead}</p>
<p class="upd">Relevé du {upd_txt}</p>
<div class="tw"><table class="pt"><thead><tr><th>Carburant</th><th>Moyenne</th><th>Le moins cher</th><th>Moyenne France</th><th>Écart</th></tr></thead><tbody>{rows}</tbody></table></div>
{tops}
<h2>Prix par commune</h2><ul class="links cols">{clinks}</ul>"""
        title = f"Prix carburant {dn} ({d}) : gazole, SP95-E10, SP98 moins chers"
        desc = (f"Prix moyen du gazole dans le département {dn} : {eur(round(a0))} le {fr_date(today)}. " if a0 else "") + \
               f"Stations les moins chères et prix par commune, {len(idx)} stations comparées."
        write(out, dep_path[d], page(dep_path[d], title, desc, body,
              [("Accueil", "/"), ("Départements", "/departements/"), (dn, dep_path[d])], None, upd_txt))
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
  <p class="seo-more"><a href="{url('/departements/')}">Tableau de tous les départements</a> · <a href="{url('/a-propos/')}">Sources et méthode</a></p>
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
