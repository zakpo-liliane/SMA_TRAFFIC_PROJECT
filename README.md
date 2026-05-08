# Systeme Multi-Agent de Regulation du Trafic

Ce projet simule une regulation de trafic inspiree d'un cahier des charges SMA pour Abidjan.
La boucle principale repose sur SUMO, des agents de type `Intersection`, `Vehicle` et `Crisis`,
une communication `ACLMessage`, des KPI exportes en CSV et un stockage PostgreSQL optionnel.

## Exigences couvertes

- SUMO comme moteur de simulation.
- Agents `Intersection`, `Vehicle` et `Crisis`.
- Structure BDI legere: `beliefs`, `desires`, `intentions`.
- Echanges inter-agents via `ACLMessage` et `MessageBus`.
- Optimisation locale des feux via Q-Learning.
- Routage initial et dynamique des vehicules via Dijkstra.
- Coordination locale type green wave et aide Contract Net.
- Scenarios `heure de pointe` et `incident sur Pont De Gaulle`.
- KPI exportes: temps d'attente moyen, longueur moyenne des files, temps de trajet moyen, messages echanges.
- Historisation PostgreSQL: metriques, messages, evenements de scenario, etats d'agents.

## Lancer le projet

Prerequis:

- SUMO installe et `SUMO_HOME` configure.
- Python avec `traci`, `psycopg2`, `networkx`, `matplotlib`.
- PostgreSQL facultatif. Sans base disponible, la simulation continue quand meme.
- Variables d'environnement possibles: `TRAFFIC_DB_HOST`, `TRAFFIC_DB_PORT`, `TRAFFIC_DB_NAME`, `TRAFFIC_DB_USER`, `TRAFFIC_DB_PASSWORD`.

Execution:

```bash
python run.py
```
La duree de demonstration par defaut est de 300 steps pour garder une execution fluide.

Interface de pilotage desktop :

```bash
python dashboard.py
```

Exemple de configuration PostgreSQL sous PowerShell avant execution:

```powershell
$env:TRAFFIC_DB_HOST="localhost"
$env:TRAFFIC_DB_PORT="5432"
$env:TRAFFIC_DB_NAME="traffic_sma"
$env:TRAFFIC_DB_USER="postgres"
$env:TRAFFIC_DB_PASSWORD="postgres"
python run.py
```

Pour utiliser l'interface graphique SUMO:

```python
from core.simulation_manager import SimulationManager

sim = SimulationManager(use_gui=True, max_steps=1000)
sim.start()
sim.run()
```

## Sorties

- Log SUMO: `logs/sumo.log`
- Resultats CSV: `results/simulation.csv`
- Visualisation: `python plot.py`
- Interface SUMO lisible: labels des carrefours et repères visibles dans `main_sma.py`

## Limites actuelles

- Le reseau SUMO fourni est compact et ne represente pas toute la topologie d'Abidjan.
- La coordination multi-intersections est pleinement exploitee seulement si plusieurs feux sont presents dans le reseau.

## Fichiers utilitaires

- `main.py`: execution headless.
- `main_sma.py`: execution avec SUMO GUI.
- `plot.py`: affichage des KPI exportes.
- `dashboard.py`: centre de controle graphique pour lancer la simulation, suivre les logs, lire les KPI et verifier PostgreSQL.
  Il inclut aussi une vue SQL recente, des jauges KPI, une carte live des zones colorees selon la congestion, des alertes rouge/orange/vert et des raccourcis pour ouvrir SUMO GUI, le CSV et le log.
- `Query Tool.sql`: schema PostgreSQL correspondant aux journaux produits.
