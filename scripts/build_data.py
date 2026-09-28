#!/usr/bin/env python3
"""Regenere les donnees de « Prix à la Pompe ».

Usage : python3 build_data.py <dossier_sortie>

Prix actuels : flux instantane officiel prix-carburants.gouv.fr (toutes les
10 min), complete par le miroir public github.com/MikeColombet/prix-essence-nord
(historique depuis 2017, mis a jour toutes les 12 h). Ecrit :
  <sortie>/data/stations.json  dernier prix de chaque station (<= 30 jours)
  <sortie>/data/history.json   moyenne nationale quotidienne depuis 2017
  <sortie>/data/st/<dep>.json   prix de chaque station sur 120 jours, par departement
Noms et enseignes : github.com/Aohzan/hass-prixcarburant (stations_name.json).
Dependances : git, python3, numpy. Duree : 2 a 3 minutes.
"""
import gzip, json, glob, os, sys, subprocess, tempfile
from datetime import datetime, date
from multiprocessing import Pool
import numpy as np

F = ["Gazole", "SP95", "E10", "SP98", "E85", "GPLc"]
FI = {k: i for i, k in enumerate(F)}
D0 = date(2017, 1, 1).toordinal()
VALID_DAYS = 30  # un prix declare reste valable 30 jours au plus


def brand_family(b):
    if not b:
        return ""
    l = b.lower()
    rules = [("total", "TotalEnergies"), ("intermarch", "Intermarché"), ("système u", "Système U"),
             ("systeme u", "Système U"), ("super u", "Système U"), ("hyper u", "Système U"),
             ("leclerc", "E.Leclerc"), ("carrefour", "Carrefour"), ("avia", "Avia"), ("esso", "Esso"),
             ("elan", "Elan"), ("auchan", "Auchan"), ("agip", "Eni"), ("eni", "Eni"), ("shell", "Shell"),
             ("dyneff", "Dyneff"), ("atac", "Atac"), ("vito", "Vito"), ("netto", "Netto"),
             ("match", "Match"), ("casino", "Casino"), ("géant", "Casino"), ("spar", "Spar"),
             ("indépendant", "Indépendant"), ("independant", "Indépendant"), ("bp", "BP")]
    for k, v in rules:
        if (k == "bp" and l.split()[:1] == ["bp"]) or (k != "bp" and k in l):
            return v
    return b.strip()


def load_names():
    path = os.path.join(tempfile.mkdtemp(), "hass")
    try:
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        "https://github.com/Aohzan/hass-prixcarburant", path], check=True)
        return json.load(open(os.path.join(path, "custom_components", "prix_carburant", "stations_name.json")))
    except Exception as e:  # les noms sont un bonus : on continue sans
        print("noms indisponibles :", e)
        return {}


OFFICIAL_URL = "https://donnees.roulez-eco.fr/opendata/instantane"


def _price(v):
    v = (v or "").strip().replace(",", ".")
    if not v:
        return None
    try:
        return float(v) if "." in v else int(v) / 1000
    except ValueError:
        return None


def parse_official(xml_bytes):
    """Flux instantane officiel (XML) -> {id: station}. Metropole uniquement."""
    import xml.etree.ElementTree as ET
    out = {}
    root = ET.fromstring(xml_bytes)
    for pdv in root.iter("pdv"):
        cp = (pdv.get("cp") or "").strip()
        if not cp or cp[:2] in ("97", "98") or len(cp) != 5:
            continue
        try:
            lat = float(pdv.get("latitude")) / 100000
            lon = float(pdv.get("longitude")) / 100000
        except (TypeError, ValueError):
            continue
        if not (41 < lat < 51.5 and -5.5 < lon < 10):
            continue
        prices = {}
        for pr in pdv.findall("prix"):
            nom, maj, val = pr.get("nom"), pr.get("maj"), _price(pr.get("valeur"))
            if nom in FI and maj and val:
                prices[nom] = (val, maj.replace("T", " ")[:19])
        h = pdv.find("horaires")
        out[pdv.get("id")] = {
            "lat": lat, "lon": lon, "cp": cp,
            "ville": (pdv.findtext("ville") or "").strip(),
            "adresse": (pdv.findtext("adresse") or "").strip(),
            "prices": prices,
            "services": [(s.text or "").strip() for s in pdv.findall("services/service") if (s.text or "").strip()],
            "h24": 1 if (h is not None and h.get("automate-24-24") == "1") else 0,
            "pop": 1 if (pdv.get("pop") or "").upper() == "A" else 0,
        }
    return out


def fetch_official():
    """Telecharge le flux instantane (mis a jour toutes les 10 min). None si indisponible."""
    import io, zipfile, urllib.request
    try:
        req = urllib.request.Request(OFFICIAL_URL, headers={"User-Agent": "prix-a-la-pompe/1.0 (site open data)"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
            res = parse_official(z.read(name))
        print(f"flux officiel : {len(res)} stations")
        return res
    except Exception as e:
        print("flux officiel indisponible, on utilise le miroir :", e)
        return None


def build_stations(repo, names, official=None):
    now = datetime.utcnow()
    merged = {}
    mirror_newest = ""
    for f in sorted(glob.glob(os.path.join(repo, "stations", "*.json.gz"))):
        for s in json.load(gzip.open(f)):
            for v in s["prices"].values():
                mirror_newest = max(mirror_newest, v["maj_officielle"].replace("T", " ")[:19])
            merged[str(s["id"])] = {
                "lat": s["latitude"], "lon": s["longitude"], "cp": s["cp"],
                "ville": s["ville"] or "", "adresse": s["adresse"] or "",
                "prices": {k: (float(v["prix_eur"]), v["maj_officielle"].replace("T", " ")[:19])
                           for k, v in s["prices"].items() if k in FI},
                "services": [], "h24": 0, "pop": 0}
    for sid, o in (official or {}).items():
        m = merged.get(sid)
        if not m:
            merged[sid] = o
            continue
        for k, (val, ts) in o["prices"].items():
            if k not in m["prices"] or ts >= m["prices"][k][1]:
                m["prices"][k] = (val, ts)
        m["services"], m["h24"], m["pop"] = o["services"], o["h24"], o["pop"]
        m["lat"], m["lon"] = o["lat"], o["lon"]
    svc_index, svc_names = {}, []
    rows, newest = [], ""
    for sid, s in merged.items():
        p, d, ok = [], [], False
        for k in F:
            v = s["prices"].get(k)
            if v:
                val, ts = v
                try:
                    age = (now - datetime.fromisoformat(ts)).days
                except ValueError:
                    age = 999
                pr = round(val * 1000)
                if age <= VALID_DAYS and 500 < pr < 4000:
                    p.append(pr); d.append(max(age, 0)); ok = True
                    newest = max(newest, ts)
                    continue
            p.append(0); d.append(-1)
        if not ok:
            continue
        sv = []
        for name in s["services"]:
            if name not in svc_index:
                svc_index[name] = len(svc_names); svc_names.append(name)
            sv.append(svc_index[name])
        adr = " ".join(s["adresse"].split()).title()
        nm = names.get(sid, {})
        rows.append([round(s["lat"], 4), round(s["lon"], 4), s["cp"],
                     " ".join(s["ville"].split()).title(), adr, p, d, sid,
                     (nm.get("name") or "").strip(), brand_family(nm.get("brand")), sv, s["h24"], s.get("pop", 0)])
    rows.sort(key=lambda r: r[2])
    return rows, newest, now, svc_names, mirror_newest


def work(args):
    files, N = args
    W = N + VALID_DAYS + 2
    cache = {}
    segd = [[] for _ in F]; sege = [[] for _ in F]; segp = [[] for _ in F]
    for fp in files:
        per = {}
        for k, p, ts in json.load(gzip.open(fp)):
            i = FI.get(k)
            if i is None:
                continue
            key = ts[:10]
            d = cache.get(key)
            if d is None:
                try:
                    d = date.fromisoformat(key).toordinal() - D0
                except ValueError:
                    d = -1
                cache[key] = d
            if d < 0 or d >= N:
                continue
            try:
                pv = float(p)
            except ValueError:
                continue
            if 0.3 < pv < 4:
                per.setdefault(i, {})[d] = pv
        for i, m in per.items():
            ds = sorted(m)
            for j, d in enumerate(ds):
                e = ds[j + 1] if j + 1 < len(ds) else W - 1
                segd[i].append(d); sege[i].append(min(e, d + VALID_DAYS)); segp[i].append(m[d])
    S = np.zeros((6, W)); C = np.zeros((6, W))
    for i in range(6):
        d = np.array(segd[i], dtype=np.int64); e = np.array(sege[i], dtype=np.int64)
        p = np.array(segp[i], dtype=float)
        S[i] += np.bincount(d, p, W) - np.bincount(e, p, W)
        C[i] += np.bincount(d, None, W) - np.bincount(e, None, W)
    return S, C


def build_history(repo, last_day):
    N = last_day.toordinal() - D0 + 1
    files = sorted(glob.glob(os.path.join(repo, "data", "*", "*.json.gz")))
    k = (os.cpu_count() or 2) * 2
    with Pool(os.cpu_count() or 2) as pool:
        res = pool.map(work, [(files[i::k], N) for i in range(k)])
    S = np.cumsum(sum(r[0] for r in res), 1)[:, :N]
    C = np.cumsum(sum(r[1] for r in res), 1)[:, :N]
    hist = {key: [round(S[i, j] / C[i, j] * 1000, 1) if C[i, j] >= 300 else None
                  for j in range(N)] for i, key in enumerate(F)}
    return {"start": date.fromordinal(D0).isoformat(), "end": last_day.isoformat(), "f": hist}


def build_station_history(repo, last_day, out, keep_ids, days=120):
    """data/st/<dep>.json : {id: {indexCarburant: [[jour, prix_millieme], ...]}}.
    jour = nombre de jours depuis (last_day - days) ; seuls les changements de prix sont gardes."""
    start = last_day.toordinal() - days
    os.makedirs(os.path.join(out, "data", "st"), exist_ok=True)
    for ddir in sorted(glob.glob(os.path.join(repo, "data", "*"))):
        dep = os.path.basename(ddir); res = {}
        for fp in glob.glob(os.path.join(ddir, "*.json.gz")):
            sid = os.path.basename(fp)[:-8]
            if sid not in keep_ids:
                continue
            series = {}
            for k, p, ts in json.load(gzip.open(fp)):
                i = FI.get(k)
                if i is None:
                    continue
                try:
                    d = date.fromisoformat(ts[:10]).toordinal() - start
                    pv = round(float(p) * 1000)
                except ValueError:
                    continue
                if d >= -400:
                    series.setdefault(i, []).append((d, pv))
            o = {}
            for i, s in series.items():
                s.sort(); pts = []; prev = None
                before = [x for x in s if x[0] < 0]
                if before:
                    prev = before[-1][1]; pts.append([0, prev])
                for d, pv in s:
                    if 0 <= d <= days and pv != prev:
                        pts.append([d, pv]); prev = pv
                if any(0 <= d for d, _ in s):
                    o[i] = pts
            if o:
                res[sid] = o
        with open(os.path.join(out, "data", "st", dep + ".json"), "w") as fh:
            json.dump({"start": date.fromordinal(start).isoformat(), "s": res}, fh, separators=(",", ":"))


def main():
    """Options par variables d'environnement :
    CACHE_DIR  dossier ou garder l'historique calcule (evite de le recalculer
               tant que le miroir n'a pas change).
    NO_OFFICIAL=1  ne pas interroger le flux officiel."""
    import shutil
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    os.makedirs(os.path.join(out, "data"), exist_ok=True)
    repo = os.path.join(tempfile.mkdtemp(), "repo")
    subprocess.run(["git", "clone", "-q", "--depth", "1",
                    "https://github.com/MikeColombet/prix-essence-nord", repo], check=True)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    official = None if os.environ.get("NO_OFFICIAL") else fetch_official()
    rows, newest, now, svc_names, mirror_newest = build_stations(repo, load_names(), official)
    if len(rows) < 5000:
        sys.exit(f"ERREUR : seulement {len(rows)} stations, donnees jugees incompletes, rien n'est ecrit.")

    cache = os.environ.get("CACHE_DIR")
    cached = cache and os.path.exists(os.path.join(cache, "sha")) and open(os.path.join(cache, "sha")).read().strip() == sha
    if cached:
        print("historique repris du cache (miroir inchange)")
        hist = json.load(open(os.path.join(cache, "history.json")))
        shutil.rmtree(os.path.join(out, "data", "st"), ignore_errors=True)
        shutil.copytree(os.path.join(cache, "st"), os.path.join(out, "data", "st"))
    else:
        last_day = datetime.fromisoformat(mirror_newest).date()
        hist = build_history(repo, last_day)
        build_station_history(repo, last_day, out, {r[7] for r in rows})
        if cache:
            os.makedirs(cache, exist_ok=True)
            shutil.rmtree(os.path.join(cache, "st"), ignore_errors=True)
            shutil.copytree(os.path.join(out, "data", "st"), os.path.join(cache, "st"))
            json.dump(hist, open(os.path.join(cache, "history.json"), "w"), separators=(",", ":"))
            open(os.path.join(cache, "sha"), "w").write(sha)

    # Point du jour : moyenne actuelle de toutes les stations (flux le plus recent)
    today = datetime.fromisoformat(newest).date()
    end = date.fromisoformat(hist["end"])
    gap = (today - end).days
    for i, k in enumerate(F):
        arr = hist["f"][k]
        vals = [r[5][i] for r in rows if r[5][i]]
        live = round(sum(vals) / len(vals), 1) if len(vals) >= 300 else None
        if gap > 0:
            arr.extend([arr[-1]] * (gap - 1) + [live if live else arr[-1]])
        elif live:
            arr[-1] = live
    if gap > 0:
        hist["end"] = today.isoformat()

    with open(os.path.join(out, "data", "stations.json"), "w") as fh:
        json.dump({"u": newest, "built": now.strftime("%Y-%m-%d %H:%M"), "sv": svc_names, "s": rows},
                  fh, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(out, "data", "history.json"), "w") as fh:
        json.dump(hist, fh, separators=(",", ":"))
    print(f"OK stations={len(rows)} noms={sum(1 for r in rows if r[8])} derniere_maj={newest} "
          f"flux_officiel={'oui' if official else 'non'} historique={hist['start']}..{hist['end']}")


if __name__ == "__main__":
    main()
