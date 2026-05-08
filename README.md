# Systeme Multi-Agent de Regulation du Trafic

Ce projet simule une regulation du trafic routier pour Abidjan a l'aide d'un systeme multi-agent connecte a SUMO. La simulation combine des agents de carrefour, de vehicule et de gestion de crise, avec export des indicateurs en CSV et stockage PostgreSQL optionnel.

## Vue d'ensemble

- Simulation de trafic basee sur SUMO et `traci`
- Agents `Intersection`, `Vehicle` et `Crisis`
- Structure BDI legere avec `beliefs`, `desires` et `intentions`
- Communication inter-agents via `ACLMessage` et `MessageBus`
- Optimisation locale des feux via Q-Learning
- Routage initial et dynamique via Dijkstra
- Coordination locale de type green wave et Contract Net
- Scenarios inclus: heure de pointe et incident sur le Pont De Gaulle
- Export des KPI en CSV
- Journalisation PostgreSQL facultative

## Structure du projet

- `agents/`: logique des agents et comportements
- `communication/`: messages ACL et bus de communication
- `coordination/`: mecanismes de coordination entre intersections
- `core/`: gestion de la simulation
- `database/`: journalisation PostgreSQL
- `environment/`: generation de trafic
- `metrics/` et `evaluation/`: collecte et exploitation des KPI
- `routing/`: calcul et mise a jour des trajets
- `scenarios/`: perturbations et cas de test
- `sumo/`: reseau, routes et configuration SUMO

## Prerequis

- Python 3
- SUMO installe
- Variable d'environnement `SUMO_HOME` configuree
- Dependances Python:
  - `traci`
  - `psycopg2`
  - `networkx`
  - `matplotlib`
- PostgreSQL optionnel

## Lancement

Execution headless:

```bash
python run.py
```

Execution via le point d'entree principal:

```bash
python main.py
```

Execution avec interface desktop:

```bash
python dashboard.py
```

La simulation utilise par defaut `300` steps.

## Exemple de configuration PostgreSQL

Sous PowerShell:

```powershell
$env:TRAFFIC_DB_HOST="localhost"
$env:TRAFFIC_DB_PORT="5432"
$env:TRAFFIC_DB_NAME="traffic_sma"
$env:TRAFFIC_DB_USER="postgres"
$env:TRAFFIC_DB_PASSWORD="postgres"
python run.py
```

Si PostgreSQL n'est pas disponible, la simulation continue sans journalisation en base.

## Lancer SUMO GUI depuis Python

```python
from core.simulation_manager import SimulationManager

sim = SimulationManager(use_gui=True, max_steps=1000)
sim.start()
sim.run()
```

## Sorties generees

- Log SUMO: `logs/sumo.log`
- Resultats CSV: `results/simulation.csv`
- Visualisation des KPI: `python plot.py`

## Fichiers utiles

- `main.py`: execution headless simple
- `main_sma.py`: execution avec SUMO GUI
- `run.py`: lancement headless rapide
- `plot.py`: affichage des KPI exportes
- `dashboard.py`: centre de controle graphique avec suivi des logs, KPI, lecture PostgreSQL et supervision visuelle
- `Query Tool.sql`: schema SQL correspondant aux journaux produits

## Limites actuelles

- Le reseau SUMO fourni reste compact et ne couvre pas toute la topologie d'Abidjan
- La coordination multi-intersections est surtout visible si plusieurs feux sont actifs dans le reseau
