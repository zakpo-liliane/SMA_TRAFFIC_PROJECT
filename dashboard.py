import csv
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import psycopg2
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BASE_DIR = Path(__file__).resolve().parent
RESULTS_CSV = BASE_DIR / "results" / "simulation.csv"
LOG_FILE = BASE_DIR / "logs" / "sumo.log"


class TrafficControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Abidjan Traffic Control Center")
        self.root.geometry("1320x780")
        self.root.configure(bg="#efe7da")
        self.root.minsize(1080, 680)

        self.process = None
        self.log_queue = queue.Queue()

        self.mode_var = tk.StringVar(value="gui")
        self.steps_var = tk.StringVar(value="300")
        self.db_host_var = tk.StringVar(value=os.getenv("TRAFFIC_DB_HOST", "localhost"))
        self.db_port_var = tk.StringVar(value=os.getenv("TRAFFIC_DB_PORT", "5432"))
        self.db_name_var = tk.StringVar(value=os.getenv("TRAFFIC_DB_NAME", "traffic_sma"))
        self.db_user_var = tk.StringVar(value=os.getenv("TRAFFIC_DB_USER", "postgres"))
        self.db_password_var = tk.StringVar(value=os.getenv("TRAFFIC_DB_PASSWORD", "postgres"))
        self.status_var = tk.StringVar(value="Pret")
        self.run_mode_label = tk.StringVar(value="Aucune simulation active")
        self.db_info = tk.StringVar(value="Pas de lecture recente.")
        self.focus_zone_var = tk.StringVar(value="Toutes")
        self.alert_blink_state = False
        self.clock_var = tk.StringVar(value="")
        self.live_badge_var = tk.StringVar(value="SYSTEME EN VEILLE")
        self.zone_detail_var = tk.StringVar(value="Selectionne une zone pour lire son niveau de congestion.")
        self.animation_phase = 0
        self.ticker_messages = [
            "Pilotage SMA en direct",
            "Paysage SUMO enrichi et supervision premium",
            "Coordination ACL et Contract Net surveillees",
            "PostgreSQL connecte aux KPI et aux etats d'agents",
        ]
        self.ticker_index = 0
        self.ticker_var = tk.StringVar(value=self.ticker_messages[0])

        self.metric_vars = {
            "avg_wait": tk.StringVar(value="0.0 s"),
            "avg_queue": tk.StringVar(value="0.0"),
            "avg_trip": tk.StringVar(value="0.0 s"),
            "messages": tk.StringVar(value="0"),
            "vehicles": tk.StringVar(value="0"),
            "arrived": tk.StringVar(value="0"),
        }

        self.gauge_specs = {
            "avg_wait": {"label": "Attente", "unit": "s", "max": 30.0, "color": "#9b4d1d"},
            "avg_queue": {"label": "File", "unit": "", "max": 20.0, "color": "#1e698f"},
            "avg_trip": {"label": "Trajet", "unit": "s", "max": 80.0, "color": "#4d7f36"},
            "messages": {"label": "ACL", "unit": "", "max": 6000.0, "color": "#8b2d62"},
        }
        self.gauge_canvases = {}
        self.zone_snapshot = {}

        self._build_styles()
        self._build_layout()
        self._build_charts()
        self.refresh_dashboard()
        self.root.after(250, self._poll_logs)
        self.root.after(2500, self._refresh_timer)
        self.root.after(1000, self._tick_clock)
        self.root.after(2200, self._rotate_ticker)
        self.root.after(350, self._animate_dashboard)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TFrame", background="#fff8ee", relief="flat")
        style.configure("Panel.TFrame", background="#10202e")
        style.configure("Title.TLabel", background="#10202e", foreground="#fff8ee", font=("Bahnschrift SemiBold", 30))
        style.configure("Subtitle.TLabel", background="#10202e", foreground="#d8d0c2", font=("Bahnschrift", 11))
        style.configure("Section.TLabel", background="#fff8ee", foreground="#182433", font=("Bahnschrift SemiBold", 14))
        style.configure("Muted.TLabel", background="#fff8ee", foreground="#726d66", font=("Bahnschrift", 10))
        style.configure("Accent.TButton", font=("Bahnschrift SemiBold", 11), padding=10)
        style.map("Accent.TButton", background=[("active", "#2f86be"), ("!disabled", "#0e628f")], foreground=[("!disabled", "white")])
        style.configure("Ghost.TButton", font=("Bahnschrift", 10), padding=8)
        style.map("Ghost.TButton", background=[("active", "#edd9b5"), ("!disabled", "#e5d0aa")], foreground=[("!disabled", "#10202e")])
        style.configure("Light.TButton", font=("Bahnschrift", 10), padding=7)
        style.map("Light.TButton", background=[("active", "#f5e9d4"), ("!disabled", "#f1e2c5")], foreground=[("!disabled", "#10202e")])
        style.configure("TEntry", padding=7, fieldbackground="white")
        style.configure("SQL.Treeview", rowheight=24, font=("Consolas", 9), background="#fffdf8", fieldbackground="#fffdf8")
        style.configure("SQL.Treeview.Heading", font=("Bahnschrift SemiBold", 10))
        style.configure("TNotebook", background="#fff8ee", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Bahnschrift", 10), padding=(10, 6))

    def _build_layout(self):
        header = ttk.Frame(self.root, style="Panel.TFrame", padding=(28, 24))
        header.pack(fill="x")
        header_top = ttk.Frame(header, style="Panel.TFrame")
        header_top.pack(fill="x")
        ttk.Label(header_top, text="Abidjan Traffic Control Center", style="Title.TLabel").pack(side="left", anchor="w")
        tk.Label(header_top, textvariable=self.clock_var, bg="#10202e", fg="#f5dd9b", font=("Bahnschrift SemiBold", 18)).pack(side="right", anchor="e")
        ttk.Label(
            header,
            text="Centre de pilotage pour lancer SUMO, suivre les KPI, lire PostgreSQL et superviser les scenarios.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            header,
            text="Realise par Zakpo Liliane et Bamba Mariam",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))
        tk.Label(header, textvariable=self.live_badge_var, bg="#10202e", fg="#8fd8ff", font=("Bahnschrift SemiBold", 10)).pack(anchor="e", pady=(2, 0))
        ticker = tk.Frame(header, bg="#17384f", height=34)
        ticker.pack(fill="x", pady=(12, 0))
        tk.Label(ticker, textvariable=self.ticker_var, bg="#17384f", fg="#eef4f2", font=("Bahnschrift", 11)).pack(anchor="w", padx=12, pady=6)

        viewport = tk.Frame(self.root, bg="#efe7da")
        viewport.pack(fill="both", expand=True, padx=12, pady=12)

        self.body_canvas = tk.Canvas(viewport, bg="#efe7da", highlightthickness=0)
        self.body_scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.body_canvas.yview)
        self.body_canvas.configure(yscrollcommand=self.body_scrollbar.set)
        self.body_scrollbar.pack(side="right", fill="y")
        self.body_canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(self.body_canvas, bg="#efe7da")
        self.body_canvas_window = self.body_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", self._on_body_configure)
        self.body_canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel()

        body.grid_columnconfigure(0, weight=0, minsize=365)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(body, style="Card.TFrame", padding=18)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.main = ttk.Frame(body, style="Card.TFrame", padding=18)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)
        self.main.grid_rowconfigure(3, weight=1)

        self._build_sidebar()
        self._build_top_metrics()
        self._build_center_zone()
        self._build_bottom_zone()

    def _build_sidebar(self):
        ttk.Label(self.sidebar, text="Pilotage", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self.sidebar, text="Mode de simulation", style="Muted.TLabel").pack(anchor="w", pady=(12, 4))

        mode_frame = ttk.Frame(self.sidebar, style="Card.TFrame")
        mode_frame.pack(fill="x")
        ttk.Radiobutton(mode_frame, text="SUMO GUI", value="gui", variable=self.mode_var).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Headless", value="headless", variable=self.mode_var).pack(anchor="w")

        ttk.Label(self.sidebar, text="Nombre de steps", style="Muted.TLabel").pack(anchor="w", pady=(14, 4))
        ttk.Entry(self.sidebar, textvariable=self.steps_var).pack(fill="x")

        controls = ttk.Frame(self.sidebar, style="Card.TFrame")
        controls.pack(fill="x", pady=(16, 4))
        ttk.Button(controls, text="Lancer", style="Accent.TButton", command=self.start_simulation).pack(fill="x")
        ttk.Button(controls, text="Arreter", style="Ghost.TButton", command=self.stop_simulation).pack(fill="x", pady=(8, 0))
        ttk.Button(controls, text="Actualiser KPI", style="Ghost.TButton", command=self.refresh_dashboard).pack(fill="x", pady=(8, 0))

        quick = ttk.Frame(self.sidebar, style="Card.TFrame")
        quick.pack(fill="x", pady=(12, 4))
        ttk.Button(quick, text="Ouvrir SUMO GUI", style="Light.TButton", command=self.launch_sumo_gui_direct).pack(fill="x")
        ttk.Button(quick, text="Ouvrir CSV", style="Light.TButton", command=lambda: self.open_path(RESULTS_CSV)).pack(fill="x", pady=(8, 0))
        ttk.Button(quick, text="Ouvrir log SUMO", style="Light.TButton", command=lambda: self.open_path(LOG_FILE)).pack(fill="x", pady=(8, 0))

        ttk.Separator(self.sidebar).pack(fill="x", pady=16)
        ttk.Label(self.sidebar, text="Focus carte", style="Section.TLabel").pack(anchor="w")
        focus_values = ("Toutes", "Yopougon", "Plateau", "Abobo", "Marcory", "Pont_HKB", "Pont_De_Gaulle")
        focus_box = ttk.Combobox(self.sidebar, textvariable=self.focus_zone_var, values=focus_values, state="readonly")
        focus_box.pack(fill="x", pady=(10, 0))
        focus_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_dashboard())

        ttk.Separator(self.sidebar).pack(fill="x", pady=16)
        ttk.Label(self.sidebar, text="PostgreSQL", style="Section.TLabel").pack(anchor="w")

        self._labeled_entry(self.sidebar, "Host", self.db_host_var)
        self._labeled_entry(self.sidebar, "Port", self.db_port_var)
        self._labeled_entry(self.sidebar, "Base", self.db_name_var)
        self._labeled_entry(self.sidebar, "Utilisateur", self.db_user_var)
        self._labeled_entry(self.sidebar, "Mot de passe", self.db_password_var, show="*")

        db_actions = ttk.Frame(self.sidebar, style="Card.TFrame")
        db_actions.pack(fill="x", pady=(14, 0))
        ttk.Button(db_actions, text="Tester PostgreSQL", style="Ghost.TButton", command=self.test_database).pack(fill="x")
        ttk.Button(db_actions, text="Actualiser SQL", style="Ghost.TButton", command=self.refresh_sql_views).pack(fill="x", pady=(8, 0))

        status_card = tk.Frame(self.sidebar, bg="#0d5c8b", padx=14, pady=14)
        status_card.pack(fill="x", pady=(18, 0))
        tk.Label(status_card, text="Statut", bg="#0d5c8b", fg="#cfe7f2", font=("Bahnschrift", 10)).pack(anchor="w")
        tk.Label(status_card, textvariable=self.status_var, bg="#0d5c8b", fg="white", font=("Bahnschrift SemiBold", 18)).pack(anchor="w", pady=(4, 0))
        tk.Label(status_card, textvariable=self.run_mode_label, bg="#0d5c8b", fg="#dbeaf5", font=("Bahnschrift", 10), justify="left").pack(anchor="w", pady=(6, 0))

    def _labeled_entry(self, parent, label, var, show=None):
        ttk.Label(parent, text=label, style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        entry = ttk.Entry(parent, textvariable=var, show=show)
        entry.pack(fill="x")
        return entry

    def _build_top_metrics(self):
        ttk.Label(self.main, text="Vue d'ensemble", style="Section.TLabel").grid(row=0, column=0, sticky="w")

        cards = tk.Frame(self.main, bg="#fff8ee")
        cards.grid(row=1, column=0, sticky="ew", pady=(12, 14))
        for index in range(6):
            cards.grid_columnconfigure(index, weight=1)

        self._metric_card(cards, 0, "Temps d'attente", self.metric_vars["avg_wait"], "#9b4d1d")
        self._metric_card(cards, 1, "File moyenne", self.metric_vars["avg_queue"], "#1e698f")
        self._metric_card(cards, 2, "Temps de trajet", self.metric_vars["avg_trip"], "#4d7f36")
        self._metric_card(cards, 3, "Messages ACL", self.metric_vars["messages"], "#8b2d62")
        self._metric_card(cards, 4, "Vehicules actifs", self.metric_vars["vehicles"], "#44546a")
        self._metric_card(cards, 5, "Arrivees", self.metric_vars["arrived"], "#7a6a1f")

    def _metric_card(self, parent, column, title, variable, accent):
        card = tk.Frame(parent, bg="#f8f2e7", padx=12, pady=12)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        tk.Frame(card, bg=accent, height=5).pack(fill="x")
        tk.Label(card, text=title, bg="#f8f2e7", fg="#6a5a48", font=("Bahnschrift", 11)).pack(anchor="w", pady=(12, 2))
        tk.Label(card, textvariable=variable, bg="#f8f2e7", fg="#15202b", font=("Bahnschrift SemiBold", 19)).pack(anchor="w")

    def _build_center_zone(self):
        center = tk.Frame(self.main, bg="#fff8ee")
        center.grid(row=2, column=0, sticky="nsew")
        center.grid_columnconfigure(0, weight=3)
        center.grid_columnconfigure(1, weight=2)
        center.grid_rowconfigure(0, weight=1)

        chart_card = tk.Frame(center, bg="#f8f2e7", padx=14, pady=14)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(chart_card, text="Evolution du trafic", bg="#f8f2e7", fg="#15202b", font=("Bahnschrift SemiBold", 14)).pack(anchor="w")
        self.chart_container = tk.Frame(chart_card, bg="#f8f2e7")
        self.chart_container.pack(fill="both", expand=True, pady=(8, 0))

        right = tk.Frame(center, bg="#fff8ee")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)

        db_card = tk.Frame(right, bg="#f8f2e7", padx=12, pady=12)
        db_card.grid(row=0, column=0, sticky="ew")
        tk.Label(db_card, text="Base PostgreSQL", bg="#f8f2e7", fg="#15202b", font=("Bahnschrift SemiBold", 14)).pack(anchor="w")
        tk.Label(db_card, textvariable=self.db_info, bg="#f8f2e7", fg="#56616b", justify="left", anchor="w", font=("Bahnschrift", 10)).pack(fill="x", pady=(8, 0))

        live_card = tk.Frame(right, bg="#10202e", padx=14, pady=14)
        live_card.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        tk.Label(live_card, text="Mode live premium", bg="#10202e", fg="#f3e7cb", font=("Bahnschrift SemiBold", 14)).pack(anchor="w")
        tk.Label(live_card, textvariable=self.zone_detail_var, bg="#10202e", fg="#b9cdda", justify="left", anchor="w", font=("Bahnschrift", 10)).pack(fill="x", pady=(6, 0))
        premium_tabs = ttk.Notebook(live_card)
        premium_tabs.pack(fill="both", expand=True, pady=(10, 0))

        map_tab = ttk.Frame(premium_tabs, style="Card.TFrame")
        premium_tabs.add(map_tab, text="Carte live")
        self.map_canvas = tk.Canvas(map_tab, bg="#0d1722", highlightthickness=0, width=420, height=260)
        self.map_canvas.pack(fill="both", expand=True)

        alerts_tab = ttk.Frame(premium_tabs, style="Card.TFrame")
        premium_tabs.add(alerts_tab, text="Alertes")
        self.alert_canvas = tk.Canvas(alerts_tab, bg="#10202e", highlightthickness=0, height=96)
        self.alert_canvas.pack(fill="x", pady=(4, 8))

        gauges_grid = tk.Frame(alerts_tab, bg="#10202e")
        gauges_grid.pack(fill="both", expand=True)
        for index, key in enumerate(self.gauge_specs):
            gauges_grid.grid_columnconfigure(index % 2, weight=1)
            frame = tk.Frame(gauges_grid, bg="#10202e")
            frame.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            canvas = tk.Canvas(frame, width=150, height=122, bg="#10202e", highlightthickness=0)
            canvas.pack()
            self.gauge_canvases[key] = canvas

    def _build_bottom_zone(self):
        bottom = tk.Frame(self.main, bg="#fff8ee")
        bottom.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        sql_card = tk.Frame(bottom, bg="#f8f2e7", padx=12, pady=12)
        sql_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(sql_card, text="Dernieres lignes SQL", bg="#f8f2e7", fg="#15202b", font=("Bahnschrift SemiBold", 14)).pack(anchor="w")
        self.sql_notebook = ttk.Notebook(sql_card)
        self.sql_notebook.pack(fill="both", expand=True, pady=(8, 0))
        self.sql_views = {}
        self._add_sql_tab("metrics", "Metrics", ("step", "vehicle_count", "avg_wait", "avg_queue", "messages_exchanged"))
        self._add_sql_tab("messages", "Messages", ("sender", "receiver", "performative"))
        self._add_sql_tab("events", "Events", ("step", "event_type"))

        log_card = tk.Frame(bottom, bg="#101820", padx=12, pady=12)
        log_card.grid(row=0, column=1, sticky="nsew")
        tk.Label(log_card, text="Journal d'execution", bg="#101820", fg="#f7e8c1", font=("Consolas", 12, "bold")).pack(anchor="w")
        self.log_text = tk.Text(
            log_card,
            bg="#101820",
            fg="#e6f0f1",
            insertbackground="white",
            font=("Consolas", 10),
            relief="flat",
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, pady=(8, 0))

    def _add_sql_tab(self, key, title, columns):
        frame = ttk.Frame(self.sql_notebook, style="Card.TFrame")
        self.sql_notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings", style="SQL.Treeview")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=120, anchor="w")
        tree.pack(fill="both", expand=True)
        self.sql_views[key] = tree

    def _build_charts(self):
        self.figure = Figure(figsize=(7.4, 3.6), dpi=100, facecolor="#f8f2e7")
        self.axis_left = self.figure.add_subplot(111)
        self.axis_left.set_facecolor("#f8f2e7")
        self.axis_right = self.axis_left.twinx()
        self.axis_right.set_facecolor("#f8f2e7")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _on_body_configure(self, _event):
        self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.body_canvas.itemconfigure(self.body_canvas_window, width=event.width)

    def _bind_mousewheel(self):
        self.body_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.body_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.body_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if hasattr(event, "delta") and event.delta:
            self.body_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.body_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.body_canvas.yview_scroll(1, "units")

    def start_simulation(self):
        self._launch_simulation(use_gui=self.mode_var.get() == "gui")

    def launch_sumo_gui_direct(self):
        self.mode_var.set("gui")
        self._launch_simulation(use_gui=True)

    def _launch_simulation(self, use_gui):
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Simulation", "Une simulation est deja en cours.")
            return
        try:
            max_steps = int(self.steps_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Le nombre de steps doit etre un entier.")
            return

        env = os.environ.copy()
        env["TRAFFIC_DB_HOST"] = self.db_host_var.get()
        env["TRAFFIC_DB_PORT"] = self.db_port_var.get()
        env["TRAFFIC_DB_NAME"] = self.db_name_var.get()
        env["TRAFFIC_DB_USER"] = self.db_user_var.get()
        env["TRAFFIC_DB_PASSWORD"] = self.db_password_var.get()

        code = (
            "from core.simulation_manager import SimulationManager; "
            f"sim=SimulationManager(use_gui={str(use_gui)}, max_steps={max_steps}); "
            "sim.start(); sim.run()"
        )
        self.process = subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.status_var.set("Simulation en cours")
        self.run_mode_label.set(f"{'SUMO GUI' if use_gui else 'Headless'} • {max_steps} steps")
        self._append_log(f"> lancement {'SUMO GUI' if use_gui else 'headless'} avec {max_steps} steps")
        threading.Thread(target=self._stream_process_output, daemon=True).start()

    def stop_simulation(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status_var.set("Simulation arretee")
            self.run_mode_label.set("Execution interrompue")
            self._append_log("> simulation arretee par l'utilisateur")
        else:
            messagebox.showinfo("Simulation", "Aucune simulation active.")

    def _stream_process_output(self):
        for line in self.process.stdout:
            self.log_queue.put(line.rstrip())
        return_code = self.process.wait()
        self.log_queue.put(f"> process termine avec code {return_code}")
        self.status_var.set("Pret")
        self.run_mode_label.set("Aucune simulation active")

    def _poll_logs(self):
        while not self.log_queue.empty():
            self._append_log(self.log_queue.get())
        self.root.after(250, self._poll_logs)

    def _append_log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _refresh_timer(self):
        self.alert_blink_state = not self.alert_blink_state
        self.refresh_dashboard()
        self.root.after(2500, self._refresh_timer)

    def _animate_dashboard(self):
        self.animation_phase = (self.animation_phase + 1) % 1000
        self.live_badge_var.set("SYSTEME EN SURVEILLANCE ACTIVE" if self.process and self.process.poll() is None else "SYSTEME EN VEILLE")
        if hasattr(self, "map_canvas"):
            self._update_live_map(self._load_live_rows())
        self.root.after(350, self._animate_dashboard)

    def _tick_clock(self):
        self.clock_var.set(datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _rotate_ticker(self):
        if self.process and self.process.poll() is None:
            self.ticker_var.set(f"Simulation active • {self.run_mode_label.get()}")
        else:
            self.ticker_index = (self.ticker_index + 1) % len(self.ticker_messages)
            self.ticker_var.set(self.ticker_messages[self.ticker_index])
        self.root.after(2200, self._rotate_ticker)

    def refresh_dashboard(self):
        rows = self._load_live_rows()
        self._update_metrics(rows)
        self._update_chart(rows)
        self._update_gauges(rows)
        self._update_db_info()
        self._update_live_map(rows)
        self._update_alerts(rows)
        self.refresh_sql_views()

    def _load_live_rows(self):
        db_rows = self._load_db_rows(limit=180)
        if db_rows:
            return db_rows
        return self._load_csv_rows()

    def _load_db_rows(self, limit=120):
        try:
            with self._db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT step, avg_wait, avg_queue, avg_trip_time, vehicle_count, messages_exchanged
                        FROM simulation_metrics
                        ORDER BY step DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                    rows = list(reversed(cur.fetchall()))
        except Exception:
            return []

        formatted_rows = []
        previous_vehicle_count = 0
        for step, avg_wait, avg_queue, avg_trip_time, vehicle_count, messages_exchanged in rows:
            vehicle_count = int(vehicle_count or 0)
            arrived = max(0, previous_vehicle_count - vehicle_count)
            formatted_rows.append(
                {
                    "step": int(step or 0),
                    "avg_waiting_time": float(avg_wait or 0.0),
                    "avg_queue_length": float(avg_queue or 0.0),
                    "avg_trip_time": float(avg_trip_time or 0.0),
                    "vehicles_in_network": vehicle_count,
                    "arrived": arrived,
                    "messages_exchanged": int(messages_exchanged or 0),
                }
            )
            previous_vehicle_count = vehicle_count
        return formatted_rows

    def _load_csv_rows(self):
        if not RESULTS_CSV.exists():
            return []
        with open(RESULTS_CSV, encoding="utf-8") as file_obj:
            return list(csv.DictReader(file_obj))

    def _update_metrics(self, rows):
        if not rows:
            for key, fallback in [("avg_wait", "0.0 s"), ("avg_queue", "0.0"), ("avg_trip", "0.0 s"), ("messages", "0"), ("vehicles", "0"), ("arrived", "0")]:
                self.metric_vars[key].set(fallback)
            return
        latest = rows[-1]
        self.metric_vars["avg_wait"].set(f"{latest['avg_waiting_time']} s")
        self.metric_vars["avg_queue"].set(latest["avg_queue_length"])
        self.metric_vars["avg_trip"].set(f"{latest['avg_trip_time']} s")
        self.metric_vars["messages"].set(latest["messages_exchanged"])
        self.metric_vars["vehicles"].set(latest["vehicles_in_network"])
        self.metric_vars["arrived"].set(latest["arrived"])

    def _update_chart(self, rows):
        self.axis_left.clear()
        self.axis_right.clear()
        self.axis_left.set_facecolor("#f8f2e7")
        self.axis_right.set_facecolor("#f8f2e7")
        self.axis_left.spines["top"].set_visible(False)
        self.axis_right.spines["top"].set_visible(False)
        self.axis_left.set_title("Attente, files et messages", color="#15202b", fontsize=12, fontweight="bold")
        self.axis_left.grid(alpha=0.18)

        if rows:
            steps = [int(row["step"]) for row in rows]
            waits = [float(row["avg_waiting_time"]) for row in rows]
            queues = [float(row["avg_queue_length"]) for row in rows]
            messages = [int(row["messages_exchanged"]) for row in rows]
            self.axis_left.plot(steps, waits, color="#9b4d1d", linewidth=2.3, label="Attente")
            self.axis_left.plot(steps, queues, color="#1e698f", linewidth=2.2, label="File")
            self.axis_right.plot(steps, messages, color="#8b2d62", linewidth=1.8, linestyle="--", label="Messages")
            self.axis_left.legend(loc="upper left", frameon=False)
            self.axis_right.legend(loc="upper right", frameon=False)

        self.canvas.draw_idle()

    def _update_gauges(self, rows):
        values = {
            "avg_wait": 0.0,
            "avg_queue": 0.0,
            "avg_trip": 0.0,
            "messages": 0.0,
        }
        if rows:
            latest = rows[-1]
            values = {
                "avg_wait": float(latest["avg_waiting_time"]),
                "avg_queue": float(latest["avg_queue_length"]),
                "avg_trip": float(latest["avg_trip_time"]),
                "messages": float(latest["messages_exchanged"]),
            }

        for key, canvas in self.gauge_canvases.items():
            spec = self.gauge_specs[key]
            value = values[key]
            self._draw_gauge(canvas, spec["label"], value, spec["max"], spec["color"], spec["unit"])

    def _update_live_map(self, rows):
        if not hasattr(self, "map_canvas"):
            return
        self.zone_snapshot = self._compute_zone_snapshot(rows)
        c = self.map_canvas
        c.delete("all")
        c.create_rectangle(0, 0, 440, 320, fill="#0d1722", outline="")
        c.create_text(18, 18, anchor="w", text="Carte de congestion", fill="#f5e9cf", font=("Bahnschrift SemiBold", 13))

        roads = [
            ((65, 150), (160, 150)),
            ((160, 150), (255, 150)),
            ((255, 150), (355, 95)),
            ((255, 150), (355, 205)),
            ((160, 55), (160, 150)),
            ((160, 245), (160, 150)),
            ((255, 55), (255, 150)),
            ((255, 245), (255, 150)),
        ]
        for start, end in roads:
            c.create_line(*start, *end, fill="#33516a", width=8, capstyle="round")
            self._draw_route_flow(c, start, end)

        positions = {
            "WestEntry": (55, 150),
            "Yopougon": (160, 150),
            "Plateau": (255, 150),
            "Abobo": (255, 55),
            "Marcory": (255, 245),
            "Pont_HKB": (370, 95),
            "Pont_De_Gaulle": (370, 205),
            "NorthY": (160, 55),
            "SouthY": (160, 245),
        }

        focus_zone = self.focus_zone_var.get()

        for zone, (x, y) in positions.items():
            color, value = self.zone_snapshot.get(zone, ("#5d6d7e", 0.0))
            if focus_zone != "Toutes" and zone != focus_zone:
                color = self._fade_color(color)
            if color == "#d1495b" and self.alert_blink_state:
                outline = "#fff4d6"
                width = 4
            else:
                outline = ""
                width = 0
            c.create_oval(x - 22, y - 22, x + 22, y + 22, fill=color, outline="")
            if width:
                c.create_oval(x - 27, y - 27, x + 27, y + 27, outline=outline, width=width)
            c.create_text(x, y, text=str(int(value)), fill="white", font=("Bahnschrift SemiBold", 11))
            c.create_text(x, y + 34, text=zone, fill="#f3ead9", font=("Bahnschrift", 9))

        if focus_zone != "Toutes" and focus_zone in positions:
            x, y = positions[focus_zone]
            c.create_rectangle(x - 42, y - 42, x + 42, y + 42, outline="#ffe9a8", width=3)
            c.create_text(300, 24, text=f"Focus: {focus_zone}", fill="#ffe9a8", font=("Bahnschrift SemiBold", 11))
            color, value = self.zone_snapshot.get(focus_zone, ("#5d6d7e", 0.0))
            detail_state = "critique" if color == "#d1495b" else "surveillance" if color == "#e59f22" else "fluide"
            self.zone_detail_var.set(
                f"Zone {focus_zone} | congestion estimee: {value:.1f} | etat: {detail_state}.\n"
                "Le focus eclaircit la carte pour suivre ce corridor prioritaire."
            )
        else:
            hottest = max(self.zone_snapshot.items(), key=lambda item: item[1][1]) if self.zone_snapshot else ("Aucune", ("#5d6d7e", 0.0))
            self.zone_detail_var.set(
                f"Zone la plus chargee: {hottest[0]} | niveau estime: {hottest[1][1]:.1f}.\n"
                "Les impulsions lumineuses montrent le sens dominant des flux sur le reseau."
            )

        legend_x = 24
        legend_y = 275
        for idx, (label, color) in enumerate([("fluide", "#2d9b5f"), ("surveillance", "#e59f22"), ("critique", "#d1495b")]):
            lx = legend_x + idx * 120
            c.create_oval(lx, legend_y, lx + 12, legend_y + 12, fill=color, outline="")
            c.create_text(lx + 18, legend_y + 6, anchor="w", text=label, fill="#f3ead9", font=("Bahnschrift", 9))

    def _update_alerts(self, rows):
        if not hasattr(self, "alert_canvas"):
            return
        c = self.alert_canvas
        c.delete("all")
        c.create_text(16, 14, anchor="w", text="Etat des alertes", fill="#f5e9cf", font=("Bahnschrift SemiBold", 12))

        if rows:
            latest = rows[-1]
            avg_wait = float(latest["avg_waiting_time"])
            avg_queue = float(latest["avg_queue_length"])
            vehicles = int(latest["vehicles_in_network"])
        else:
            avg_wait = avg_queue = 0.0
            vehicles = 0

        alerts = [
            ("Reseau", *self._alert_level(avg_queue, 2.5, 6.0)),
            ("Attente", *self._alert_level(avg_wait, 3.0, 8.0)),
            ("Charge", *self._alert_level(vehicles, 20.0, 60.0)),
        ]

        for index, (label, state, color) in enumerate(alerts):
            x = 35 + index * 120
            blink_fill = "#fff4d6" if color == "#d1495b" and self.alert_blink_state else color
            c.create_oval(x, 42, x + 24, 66, fill=blink_fill, outline="")
            c.create_text(x + 34, 46, anchor="w", text=label, fill="#d6dde3", font=("Bahnschrift SemiBold", 10))
            c.create_text(x + 34, 62, anchor="w", text=state, fill="#ffffff", font=("Bahnschrift", 10))

    def _alert_level(self, value, warning, critical):
        if value >= critical:
            return "rouge", "#d1495b"
        if value >= warning:
            return "orange", "#e59f22"
        return "vert", "#2d9b5f"

    def _compute_zone_snapshot(self, rows):
        base = {
            "WestEntry": ("#2d9b5f", 0.0),
            "Yopougon": ("#2d9b5f", 0.0),
            "Plateau": ("#2d9b5f", 0.0),
            "Abobo": ("#2d9b5f", 0.0),
            "Marcory": ("#2d9b5f", 0.0),
            "Pont_HKB": ("#2d9b5f", 0.0),
            "Pont_De_Gaulle": ("#2d9b5f", 0.0),
            "NorthY": ("#2d9b5f", 0.0),
            "SouthY": ("#2d9b5f", 0.0),
        }
        try:
            with self._db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT agent_id, state
                        FROM agent_state_snapshots
                        WHERE agent_type = 'intersection'
                        ORDER BY id DESC
                        LIMIT 10
                        """
                    )
                    for agent_id, state in cur.fetchall():
                        tls_id = state.get("tls_id")
                        queue = float(state.get("queue_length", 0.0))
                        color = self._zone_color(queue)
                        if tls_id == "Yopougon":
                            for zone in ("WestEntry", "Yopougon", "NorthY", "SouthY", "Abobo"):
                                base[zone] = (color, queue)
                        elif tls_id == "Plateau":
                            for zone in ("Plateau", "Marcory", "Pont_HKB", "Pont_De_Gaulle"):
                                base[zone] = (color, queue)
                    return base
        except Exception:
            if rows:
                queue = float(rows[-1]["avg_queue_length"])
                color = self._zone_color(queue)
                for zone in base:
                    base[zone] = (color, queue)
            return base

    def _zone_color(self, queue_value):
        if queue_value >= 6:
            return "#d1495b"
        if queue_value >= 2.5:
            return "#e59f22"
        return "#2d9b5f"

    def _fade_color(self, color):
        mapping = {
            "#d1495b": "#7e4b53",
            "#e59f22": "#8a6d3c",
            "#2d9b5f": "#456b56",
        }
        return mapping.get(color, "#4d5e6a")

    def _draw_route_flow(self, canvas, start, end):
        phase = (self.animation_phase % 20) / 20.0
        for offset in (0.0, 0.5):
            t = (phase + offset) % 1.0
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#ffe39b", outline="")

    def _draw_gauge(self, canvas, label, value, maximum, color, unit):
        canvas.delete("all")
        cx, cy, radius = 75, 78, 50
        start, extent = 150, 240
        canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start, extent=extent, outline="#2d3f4d", width=14, style="arc")
        ratio = 0 if maximum <= 0 else max(0.0, min(value / maximum, 1.0))
        canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start, extent=extent * ratio, outline=color, width=14, style="arc")
        canvas.create_text(cx, 34, text=label, fill="#f3e7cb", font=("Bahnschrift", 11))
        display = f"{value:.1f}{unit}" if unit else f"{int(value)}"
        canvas.create_text(cx, cy + 2, text=display, fill="white", font=("Bahnschrift SemiBold", 18))
        canvas.create_text(cx, cy + 28, text=f"max {maximum:.0f}{unit}", fill="#b7c3cb", font=("Bahnschrift", 9))

    def _db_connect(self):
        return psycopg2.connect(
            host=self.db_host_var.get(),
            port=self.db_port_var.get(),
            dbname=self.db_name_var.get(),
            user=self.db_user_var.get(),
            password=self.db_password_var.get(),
            connect_timeout=3,
        )

    def test_database(self):
        try:
            with self._db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT current_database(), current_user")
                    db_name, user_name = cur.fetchone()
            messagebox.showinfo("PostgreSQL", f"Connexion OK sur {db_name} avec {user_name}.")
        except Exception as exc:
            messagebox.showerror("PostgreSQL", f"Connexion echouee:\n{exc}")

    def _update_db_info(self):
        try:
            with self._db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            (SELECT COUNT(*) FROM simulation_metrics),
                            (SELECT COUNT(*) FROM agent_messages),
                            (SELECT COUNT(*) FROM scenario_events),
                            (SELECT COUNT(*) FROM agent_state_snapshots)
                        """
                    )
                    metrics_rows, messages_rows, events_rows, states_rows = cur.fetchone()
            self.db_info.set(
                "Connexion active\n"
                f"simulation_metrics : {metrics_rows}\n"
                f"agent_messages    : {messages_rows}\n"
                f"scenario_events   : {events_rows}\n"
                f"agent_states      : {states_rows}"
            )
        except Exception:
            self.db_info.set("Base non joignable pour le moment.\nVerifie les parametres PostgreSQL.")

    def refresh_sql_views(self):
        try:
            with self._db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT step, vehicle_count, avg_wait, avg_queue, messages_exchanged
                        FROM simulation_metrics
                        ORDER BY id DESC
                        LIMIT 8
                        """
                    )
                    self._fill_tree("metrics", cur.fetchall())

                    cur.execute(
                        """
                        SELECT sender, receiver, performative
                        FROM agent_messages
                        ORDER BY id DESC
                        LIMIT 8
                        """
                    )
                    self._fill_tree("messages", cur.fetchall())

                    cur.execute(
                        """
                        SELECT step, event_type
                        FROM scenario_events
                        ORDER BY id DESC
                        LIMIT 8
                        """
                    )
                    self._fill_tree("events", cur.fetchall())
        except Exception:
            for key in self.sql_views:
                self._fill_tree(key, [])

    def _fill_tree(self, key, rows):
        tree = self.sql_views[key]
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=row)

    def open_path(self, path):
        try:
            if not Path(path).exists():
                messagebox.showinfo("Fichier", f"Introuvable:\n{path}")
                return
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Ouverture", f"Impossible d'ouvrir:\n{exc}")

    def on_close(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Quitter", "Une simulation tourne encore. Fermer quand meme ?"):
                return
            self.process.terminate()
        if hasattr(self, "body_canvas"):
            self.body_canvas.unbind_all("<MouseWheel>")
            self.body_canvas.unbind_all("<Button-4>")
            self.body_canvas.unbind_all("<Button-5>")
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TrafficControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
