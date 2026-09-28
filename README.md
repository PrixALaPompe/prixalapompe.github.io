# Prix à la Pompe

Carte des prix de l'essence et du gazole dans toutes les stations-service de France métropolitaine, avec l'évolution des prix depuis 2017 et une page par ville, département et carburant.

**Site :** https://prixalapompe.github.io/

## Fonctionnement

Tout tourne gratuitement sur GitHub :

- `.github/workflows/update.yml` s'exécute toutes les 30 minutes.
- `scripts/build_data.py` lit le flux officiel [prix-carburants.gouv.fr](https://www.prix-carburants.gouv.fr/rubrique/opendata/) (mis à jour toutes les 10 min). L'historique depuis 2017 vient de [prix-essence-nord](https://github.com/MikeColombet/prix-essence-nord), et les noms des stations de [hass-prixcarburant](https://github.com/Aohzan/hass-prixcarburant) (OpenStreetMap).
- `scripts/build_site.py` génère la carte (`index.html`) et environ 6 000 pages : villes, départements, carburants, enseignes, autoroute, bilans hebdomadaires, widget à intégrer. Il produit aussi `sitemap.xml`, `robots.txt` et `llms.txt`, puis le workflow publie le tout sur GitHub Pages.

## Référencement

Pour vérifier le site dans Google Search Console ou Bing Webmaster Tools, ajoute le code de vérification dans *Settings → Secrets and variables → Actions → Variables* :

- `GOOGLE_SITE_VERIFICATION` : le code de la balise meta proposée par Google
- `BING_SITE_VERIFICATION` : le code de la balise meta proposée par Bing

Relance ensuite le workflow (*Actions → Mise à jour des prix → Run workflow*).

## Local

```bash
pip install numpy
python scripts/build_data.py _build
SITE_URL=http://localhost:8000 python scripts/build_site.py _build _site
cd _site && python -m http.server
```
