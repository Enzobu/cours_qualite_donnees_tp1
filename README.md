# TD1 — Qualité des données  
## Criminalité à Cambridge (2009–2024)

Ce projet a pour objectif de mettre en œuvre un **processus global de qualité des données** à partir d’un jeu de données de crimes déclarés dans la ville de Cambridge, en vue de produire des indicateurs fiables d’aide à la décision.

L’ensemble du projet est **exécutable par un tiers** grâce à un environnement Dockerisé.

---

## 1. Contexte

Dans le cadre de cette mission, nous intervenons comme **consultant data** pour la ville de Cambridge (service Sécurité).  
Les données fournies proviennent de **systèmes opérationnels hétérogènes** et couvrent la période 2009–2024.

Avant toute exploitation (indicateurs, cartographie), un **audit de qualité des données** est nécessaire afin :
- d’évaluer leur fiabilité,
- d’identifier les problèmes de qualité,
- de définir et appliquer des règles de traitement adaptées.

---

## 2. Environnement & exécution

### Prérequis
- Docker
- Docker Compose (v2)

### Structure du projet

```
.
├── data/
│   ├── crime_reports_broken.csv
│   └── BOUNDARY_CDDNeighborhoods.geojson
├── src/
│   ├── main.py
│   ├── map.py
│   └── inspect_geojson.py
├── tests/
│   └── test_main.py
├── logs/
├── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### Installation

Clonez le répo git

### Lancer le projet

```bash
docker compose up --build
```

Ce lancement :
1. exécute les tests unitaires (`pytest`)
2. lance le script principal de nettoyage
3. génère les logs dans `logs/`
4. exporte le fichier nettoyé `data/crime_reports_clean.csv`
4. exporte la map `data/map.html`

---

## 3. Profilage et exploration des données

Les actions suivantes sont réalisées :
- chargement du dataset
- affichage du nombre de lignes et de colonnes
- identification des types de données
- calcul du nombre de valeurs manquantes par colonne
- identification de plusieurs problèmes de qualité :
  - doublons exacts
  - identifiants non uniques
  - valeurs manquantes (Crime, Neighborhood, Reporting Area)
  - dates invalides
  - incohérences temporelles
  - valeurs hors référentiel

Le jeu de données initial contient **10 506 lignes** et **7 colonnes**.

### Types des colonnes
Les colonnes sont majoritairement de type texte (`object`), y compris pour des données temporelles et numériques, ce qui indique une absence de typage strict en amont.

### Valeurs manquantes
Des valeurs manquantes ont été identifiées, notamment :
- `Crime`
- `Neighborhood`
- `Reporting Area`
- `Location`

### Problèmes de qualité identifiés
L’exploration initiale a permis d’identifier plusieurs problèmes de qualité :
- présence de doublons exacts,
- identifiants `File Number` non uniques,
- valeurs manquantes sur des champs critiques,
- dates de signalement invalides,
- incohérences temporelles entre la date de signalement et la date du crime,
- quartiers hors référentiel officiel,
- zones de signalement non conformes.

---

## 4. Dictionnaire des données

| Colonne | Type | Définition | Exemple |
|-------|------|-----------|---------|
| File Number | string | Identifiant du dossier de police. Doit être unique par crime. | 2016-02477 |
| Date of Report | datetime | Date et heure de déclaration du crime. | 2016-04-14 19:11:00 |
| Crime Date Time | string | Intervalle de temps durant lequel le crime a eu lieu. | 04/13/2016 20:00 - 04/14/2016 06:30 |
| Crime | string | Catégorie du crime déclaré. | Larceny from MV |
| Reporting Area | integer | Zone administrative interne de la police. | 403 |
| Neighborhood | string | Quartier officiel de Cambridge. | Area 4 |
| reporting_area_group | integer | Groupe de zones (centaines) pour la cartographie. | 4 |

---

## 5. Audit de la qualité des données

Les indicateurs suivants sont calculés sur le dataset initial :
- Taux de complétude (Crime, File Number, Neighborhood)
- Taux d’unicité de `File Number`
- Taux de doublons exacts
- Taux de dates invalides (`Date of Report`)
- Taux d’incohérences temporelles  
  (`Date of Report` < début de `Crime Date Time`)
- Taux de valeurs non conformes (`Reporting Area`, `Neighborhood`)

### Seuils d’acceptation (exemples)
- Complétude ≥ 95 %
- Unicité de File Number ≥ 99 %
- Dates invalides ≤ 1 %
- Doublons exacts ≤ 0.1 %

---

## 6. Traitement des données

Les règles de nettoyage appliquées sont les suivantes :
- Doublons exacts : suppression
- Doublons de File Number : conservation de la ligne la plus complète
- Crime manquant : suppression de la ligne
- Date de signalement invalide : suppression
- Incohérence temporelle : correction
- Reporting Area invalide : mise à NA
- Neighborhood hors référentiel : mise à NA
- Enrichissement :
  - création de `reporting_area_group`
  - contrôle des valeurs aberrantes

---

## 7. Monitoring de la qualité

| Indicateur | Avant | Après |
|-----------|-------|-------|
| Complétude Crime | 95.003 % | 100 % |
| Unicité File Number | 95.184 % | 100 % |
| Doublons exacts | 1.942 % | 0 % |
| Dates invalides | 0.980 % | 0 % |

---

## 8. Cartographie — Choroplèthe

Une carte choroplèthe interactive représentant le nombre de crimes par quartier est générée à partir du dataset nettoyé.

Fichier généré :
```
data/map.html
```

---

## 9. Réponse à la question finale

**Pourquoi le terme « quartier le plus dangereux » peut-il être trompeur avec un indicateur en volume brut ?**

Un indicateur en volume brut ne tient pas compte de la population, de la surface ou de la fréquentation du quartier.  
Un quartier très fréquenté peut donc présenter un nombre élevé de crimes sans être plus dangereux qu’un quartier résidentiel moins peuplé.  
Une analyse pertinente devrait normaliser les données (par habitant, par type de crime, etc.).

---

## 10. Bonus
- Tests automatisés avec pytest
- Journalisation des traitements
- Environnement Docker reproductible