# smart_scheduler_pdf_model.py
"""
Smart To-Do Scheduler GUI (Tkinter + PuLP + Matplotlib)
Implements the mathematical formulation from FINAL LINEAR M1 (user PDF)
- slot-based (default 15 minutes)
- variables: x_{i,t}, S_i, C_i, Tard_i
- constraints 1..7 from the PDF
- combined objective: w1 * sum(p_i S_i) + w2 * sum(S_i) - w3 * sum(p_i * Tard_i)
- availability At editable in GUI (per-slot)
"""

import tkinter as tk
from tkinter import ttk, messagebox, StringVar, BooleanVar, IntVar
from datetime import datetime, timedelta
from math import ceil
import pulp
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import random

matplotlib.use("TkAgg")


class SchedulerPDFGUI:
    def _init_(self, root):
        self.root = root
        self.root.title("Smart Scheduler — PDF Formulation")
        # styling
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Parameters (easy to change)
        self.SLOT_MIN = 15  # minutes per slot (matches PDF example)
        # Default planning window (set any day/time you like)
        self.DAY_START = datetime(2025, 11, 18, 8, 0)
        self.DAY_END = datetime(2025, 11, 18, 22, 0)

        # Derived
        self.T = int((self.DAY_END - self.DAY_START).total_seconds() // 60 // self.SLOT_MIN)
        self.W_day = list(range(1, self.T + 1))  # slots numbering 1..T
        self.TLAST = self.T

        # Data
        self.tasks_input = {}  # tid -> dict with duration_min, es, dl, p (priority), fixed, fixed_start
        # Availability vector At: 1 by default for all slots (editable)
        self.At = [1] * self.T

        # plot color map
        self.random_colors = {}

        # last solve outputs
        self._last_tasks = None
        self._last_schedule = None
        self._last_slot_occupancy = None
        self._tid_to_idx = None

        # Build UI
        self.create_widgets()

    # ---------------- UI ----------------
    def create_widgets(self):
        # Top area: task inputs + weights + availability controls
        top = ttk.Frame(self.root, padding=(6, 6))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Add / Edit Task (PDF model)", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=10, sticky=tk.W, pady=(0, 6))

        # Task input labels
        labels = ["ID", "Duration (min)", "Earliest (HH:MM)", "Deadline (HH:MM)", "Priority p_i", "Fixed", "Fixed Start (HH:MM)"]
        for c, txt in enumerate(labels):
            ttk.Label(top, text=txt).grid(row=1, column=c, sticky=tk.W)

        # Variables
        self.var_id = StringVar()
        self.var_duration = StringVar()
        self.var_es = StringVar()
        self.var_dl = StringVar()
        self.var_priority = StringVar()
        self.var_fixed = BooleanVar(value=False)
        self.var_fixed_start = StringVar()

        ttk.Entry(top, textvariable=self.var_id, width=8).grid(row=2, column=0, padx=2)
        ttk.Entry(top, textvariable=self.var_duration, width=12).grid(row=2, column=1, padx=2)
        ttk.Entry(top, textvariable=self.var_es, width=12).grid(row=2, column=2, padx=2)
        ttk.Entry(top, textvariable=self.var_dl, width=12).grid(row=2, column=3, padx=2)
        ttk.Entry(top, textvariable=self.var_priority, width=8).grid(row=2, column=4, padx=2)
        ttk.Checkbutton(top, variable=self.var_fixed, command=self.on_fixed_toggle).grid(row=2, column=5)
        self.entry_fixed_start = ttk.Entry(top, textvariable=self.var_fixed_start, width=12, state=tk.DISABLED)
        self.entry_fixed_start.grid(row=2, column=6, padx=2)

        ttk.Button(top, text="Add / Update Task", command=self.add_or_update_task).grid(row=2, column=7, padx=6)
        ttk.Button(top, text="Clear Inputs", command=self.clear_inputs).grid(row=2, column=8, padx=6)

        # Weights controls (w1, w2, w3)
        wframe = ttk.Frame(top)
        wframe.grid(row=3, column=0, columnspan=10, pady=(8, 6), sticky=tk.W)
        ttk.Label(wframe, text="Objective weights (w1 * priority_sum, w2 * #tasks, - w3 * priority * tardiness)").pack(anchor=tk.W)
        self.var_w1 = StringVar(value="10")
        self.var_w2 = StringVar(value="5")
        self.var_w3 = StringVar(value="20")
        ttk.Label(wframe, text="w1").pack(side=tk.LEFT, padx=(0,4))
        ttk.Entry(wframe, textvariable=self.var_w1, width=6).pack(side=tk.LEFT)
        ttk.Label(wframe, text="w2").pack(side=tk.LEFT, padx=(8,4))
        ttk.Entry(wframe, textvariable=self.var_w2, width=6).pack(side=tk.LEFT)
        ttk.Label(wframe, text="w3").pack(side=tk.LEFT, padx=(8,4))
        ttk.Entry(wframe, textvariable=self.var_w3, width=6).pack(side=tk.LEFT)

        # Availability editor (At)
        avail_frame = ttk.Labelframe(self.root, text="Slot availability (A_t) — edit to match PDF's At", padding=(6,6))
        avail_frame.pack(fill=tk.X, padx=6, pady=(4,6))

        # Buttons for blocking/unblocking intervals and quick presets
        control_row = ttk.Frame(avail_frame)
        control_row.pack(fill=tk.X, pady=(0,6))
        ttk.Button(control_row, text="Block interval", command=self.block_interval_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_row, text="Unblock interval", command=self.unblock_interval_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_row, text="Set All Available", command=self.set_all_available).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_row, text="Set Work Window (start/end)", command=self.set_work_window_dialog).pack(side=tk.LEFT, padx=4)

        # Compact scrollable grid of checkboxes for slots
        slots_frame = ttk.Frame(avail_frame)
        slots_frame.pack(fill=tk.X)
        canvas = tk.Canvas(slots_frame, height=80)
        scrollbar = ttk.Scrollbar(slots_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        self.slot_strip = ttk.Frame(canvas)
        self.slot_strip.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.slot_strip, anchor='nw')
        canvas.configure(xscrollcommand=scrollbar.set)
        canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.TOP, fill=tk.X)

        # Build slot checkboxes
        self.slot_vars = []
        for t in range(self.T):
            var = IntVar(value=self.At[t])
            cb = ttk.Checkbutton(self.slot_strip, text=self._slot_label(t+1), variable=var, command=self._update_At_from_checks)
            cb.pack(side=tk.LEFT, padx=2, pady=2)
            self.slot_vars.append(var)

        # Middle: treeview of tasks + action buttons
        middle = ttk.Frame(self.root, padding=(6,6))
        middle.pack(fill=tk.BOTH, expand=False)

        cols = ("ID", "Duration(min)", "ES", "DL", "Priority", "Fixed", "FixedStart")
        self.tree = ttk.Treeview(middle, columns=cols, show="headings", height=8, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor=tk.CENTER, width=110)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scr = ttk.Scrollbar(middle, orient=tk.VERTICAL, command=self.tree.yview)
        scr.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scr.set)

        btn_frame = ttk.Frame(middle)
        btn_frame.pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="Solve (PuLP CBC)", command=self.solve_and_visualize).pack(fill=tk.X, pady=3)

        # Bottom: text output and plot
        bottom = ttk.Frame(self.root, padding=(6,6))
        bottom.pack(fill=tk.BOTH, expand=True)

        left_out = ttk.Frame(bottom)
        left_out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(left_out, text="Schedule Output", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        self.text_out = tk.Text(left_out, height=10)
        self.text_out.pack(fill=tk.BOTH, expand=False, pady=(4,8))

        right_plot = ttk.Frame(bottom)
        right_plot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(right_plot, text="Visualization", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        self.fig, self.ax = plt.subplots(figsize=(8,4))
        plt.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_plot)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Visualization controls
        vis_frame = ttk.Frame(right_plot)
        vis_frame.pack(fill=tk.X, pady=(6,0))
        self.show_slots_var = BooleanVar(value=False)
        ttk.Checkbutton(vis_frame, text="Show slot occupancy heatmap", variable=self.show_slots_var).pack(side=tk.LEFT)
        ttk.Button(vis_frame, text="Refresh Plot", command=self.redraw_plot).pack(side=tk.LEFT, padx=6)

        # Status bar
        self.status = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # ---------------- UI helpers ----------------
    def _slot_label(self, slot_no):
        minutes = (slot_no - 1) * self.SLOT_MIN
        ts = self.DAY_START + timedelta(minutes=minutes)
        return ts.strftime("%H:%M")

    def _update_At_from_checks(self):
        for i, var in enumerate(self.slot_vars):
            self.At[i] = 1 if var.get() else 0

    def set_all_available(self):
        for i in range(self.T):
            self.At[i] = 1
            self.slot_vars[i].set(1)
        self.status.configure(text="All slots set available (At=1)")

    def set_work_window_dialog(self):
        # allow user to change DAY_START / DAY_END; changing these rebuilds slots
        dlg = tk.Toplevel(self.root)
        dlg.title("Set Work Window (HH:MM)")
        ttk.Label(dlg, text="Start (HH:MM)").grid(row=0, column=0, padx=6, pady=6)
        ttk.Label(dlg, text="End   (HH:MM)").grid(row=0, column=1, padx=6, pady=6)
        vs = StringVar(value=self.DAY_START.strftime("%H:%M"))
        ve = StringVar(value=self.DAY_END.strftime("%H:%M"))
        e_s = ttk.Entry(dlg, textvariable=vs)
        e_e = ttk.Entry(dlg, textvariable=ve)
        e_s.grid(row=1, column=0, padx=6, pady=6)
        e_e.grid(row=1, column=1, padx=6, pady=6)
        def apply_window():
            start = vs.get().strip()
            end = ve.get().strip()
            if not (self._valid_hhmm(start) and self._valid_hhmm(end)):
                messagebox.showerror("Format", "Start/End must be HH:MM")
                return
            hh, mm = map(int, start.split(":"))
            hh2, mm2 = map(int, end.split(":"))
            new_start = datetime(self.DAY_START.year, self.DAY_START.month, self.DAY_START.day, hh, mm)
            new_end = datetime(self.DAY_START.year, self.DAY_START.month, self.DAY_START.day, hh2, mm2)
            if new_end <= new_start:
                messagebox.showerror("Window", "End must be after Start")
                return
            self.DAY_START = new_start
            self.DAY_END = new_end
            # rebuild slots and availability (default all available)
            self.T = int((self.DAY_END - self.DAY_START).total_seconds() // 60 // self.SLOT_MIN)
            self.W_day = list(range(1, self.T + 1))
            self.TLAST = self.T
            # rebuild slot strip UI (destroy and recreate)
            for widget in self.slot_strip.winfo_children():
                widget.destroy()
            self.At = [1] * self.T
            self.slot_vars = []
            for t in range(self.T):
                var = IntVar(value=1)
                cb = ttk.Checkbutton(self.slot_strip, text=self._slot_label(t+1), variable=var, command=self._update_At_from_checks)
                cb.pack(side=tk.LEFT, padx=2, pady=2)
                self.slot_vars.append(var)
            self.status.configure(text=f"Work window set {self.DAY_START.strftime('%H:%M')} - {self.DAY_END.strftime('%H:%M')} ({self.T} slots)")
            dlg.destroy()
        ttk.Button(dlg, text="Apply", command=apply_window).grid(row=2, column=0, columnspan=2, pady=8)

    def block_interval_dialog(self):
        # dialog to block interval by HH:MM
        dlg = tk.Toplevel(self.root)
        dlg.title("Block interval (set At=0)")
        ttk.Label(dlg, text="From (HH:MM)").grid(row=0, column=0, padx=6, pady=6)
        ttk.Label(dlg, text="To   (HH:MM)").grid(row=0, column=1, padx=6, pady=6)
        vs = StringVar()
        ve = StringVar()
        ttk.Entry(dlg, textvariable=vs).grid(row=1, column=0, padx=6, pady=6)
        ttk.Entry(dlg, textvariable=ve).grid(row=1, column=1, padx=6, pady=6)
        def apply_block():
            s = vs.get().strip()
            e = ve.get().strip()
            if not (self._valid_hhmm(s) and self._valid_hhmm(e)):
                messagebox.showerror("Format", "Times must be HH:MM")
                return
            s_slot = self.hhmm_to_slot(s)
            e_slot = self.hhmm_to_slot(e)
            if e_slot < s_slot:
                messagebox.showerror("Range", "End before start")
                return
            for slot in range(s_slot, e_slot + 1):
                if 1 <= slot <= self.T:
                    self.At[slot - 1] = 0
                    self.slot_vars[slot - 1].set(0)
            self.status.configure(text=f"Blocked slots {s_slot}..{e_slot}")
            dlg.destroy()
        ttk.Button(dlg, text="Block", command=apply_block).grid(row=2, column=0, columnspan=2, pady=6)

    def unblock_interval_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Unblock interval (set At=1)")
        ttk.Label(dlg, text="From (HH:MM)").grid(row=0, column=0, padx=6, pady=6)
        ttk.Label(dlg, text="To   (HH:MM)").grid(row=0, column=1, padx=6, pady=6)
        vs = StringVar()
        ve = StringVar()
        ttk.Entry(dlg, textvariable=vs).grid(row=1, column=0, padx=6, pady=6)
        ttk.Entry(dlg, textvariable=ve).grid(row=1, column=1, padx=6, pady=6)
        def apply_unblock():
            s = vs.get().strip()
            e = ve.get().strip()
            if not (self._valid_hhmm(s) and self._valid_hhmm(e)):
                messagebox.showerror("Format", "Times must be HH:MM")
                return
            s_slot = self.hhmm_to_slot(s)
            e_slot = self.hhmm_to_slot(e)
            if e_slot < s_slot:
                messagebox.showerror("Range", "End before start")
                return
            for slot in range(s_slot, e_slot + 1):
                if 1 <= slot <= self.T:
                    self.At[slot - 1] = 1
                    self.slot_vars[slot - 1].set(1)
            self.status.configure(text=f"Unblocked slots {s_slot}..{e_slot}")
            dlg.destroy()
        ttk.Button(dlg, text="Unblock", command=apply_unblock).grid(row=2, column=0, columnspan=2, pady=6)


    def on_fixed_toggle(self):
        if self.var_fixed.get():
            self.entry_fixed_start.configure(state=tk.NORMAL)
        else:
            self.entry_fixed_start.configure(state=tk.DISABLED)
            self.var_fixed_start.set("")

    def clear_inputs(self):
        self.var_id.set("")
        self.var_duration.set("")
        self.var_es.set("")
        self.var_dl.set("")
        self.var_priority.set("")
        self.var_fixed.set(False)
        self.var_fixed_start.set("")
        self.entry_fixed_start.configure(state=tk.DISABLED)

    def on_tree_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self.var_id.set(vals[0])
        self.var_duration.set(vals[1])
        self.var_es.set(vals[2])
        self.var_dl.set(vals[3])
        self.var_priority.set(vals[4])
        fixed = True if vals[5] in (True, "True", 1) else False
        self.var_fixed.set(fixed)
        if fixed:
            self.entry_fixed_start.configure(state=tk.NORMAL)
            self.var_fixed_start.set(vals[6] if vals[6] not in (None, "None") else "")
        else:
            self.entry_fixed_start.configure(state=tk.DISABLED)
            self.var_fixed_start.set("")

    def add_or_update_task(self):
        tid = self.var_id.get().strip()
        if not tid:
            messagebox.showerror("Input error", "Task ID is required.")
            return
        try:
            duration = int(self.var_duration.get())
            if duration <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Input error", "Duration must be a positive integer (minutes).")
            return
        try:
            priority = float(self.var_priority.get())
        except Exception:
            messagebox.showerror("Input error", "Priority p_i must be numeric.")
            return
        es = self.var_es.get().strip()
        dl = self.var_dl.get().strip()
        fixed = bool(self.var_fixed.get())
        fixed_start = self.var_fixed_start.get().strip() if fixed else None

        # basic time format check
        for tstr in (es, dl, fixed_start) if fixed else (es, dl):
            if tstr:
                if not self._valid_hhmm(tstr):
                    messagebox.showerror("Time format", f"Time '{tstr}' is not valid (expected HH:MM).")
                    return

        # store task
        self.tasks_input[tid] = {
            "duration_min": duration,
            "es": es,
            "dl": dl,
            "p": priority,
            "fixed": fixed,
            "fixed_start": fixed_start
        }

        # update treeview
        for item in self.tree.get_children():
            if self.tree.item(item)["values"][0] == tid:
                self.tree.delete(item)
                break
        self.tree.insert("", "end", values=(tid, duration, es, dl, priority, fixed, fixed_start))
        self.clear_inputs()
        self.status.configure(text=f"Task '{tid}' added/updated")

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Remove", "No task selected.")
            return
        tid = self.tree.item(sel[0])["values"][0]
        if tid in self.tasks_input:
            del self.tasks_input[tid]
        self.tree.delete(sel[0])
        self.text_out.delete("1.0", tk.END)
        self.status.configure(text=f"Task '{tid}' removed")

    def _valid_hhmm(self, s):
        try:
            hh, mm = map(int, s.split(":"))
            return 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            return False

    # ---------------- Time/slot helpers ----------------
    def hhmm_to_slot(self, timestr):
        hh, mm = map(int, timestr.split(":"))
        dt = datetime(self.DAY_START.year, self.DAY_START.month, self.DAY_START.day, hh, mm)
        if dt < self.DAY_START:
            return 1
        if dt >= self.DAY_END:
            return self.T
        delta = dt - self.DAY_START
        return int(delta.total_seconds() // 60 // self.SLOT_MIN) + 1

    # ---------------- Core: build & solve MILP (PDF formulation) ----------------
    def solve_and_visualize(self):
        if not self.tasks_input:
            messagebox.showinfo("No tasks", "No tasks to schedule. Please add tasks first.")
            return

        # read weights
        try:
            w1 = float(self.var_w1.get())
            w2 = float(self.var_w2.get())
            w3 = float(self.var_w3.get())
        except Exception:
            messagebox.showerror("Weights", "Weights w1, w2, w3 must be numeric.")
            return

        # Preprocess tasks: convert to slots and feasible starts
        tasks = {}
        infeasible_tasks = []
        for tid, info in self.tasks_input.items():
            p_slots = ceil(info["duration_min"] / self.SLOT_MIN)  # di in slots
            # validate times
            try:
                es_slot = self.hhmm_to_slot(info["es"])
                dl_slot = self.hhmm_to_slot(info["dl"])
            except Exception:
                messagebox.showerror("Time format", f"Invalid earliest or deadline time for task {tid}.")
                return

            # compute feasible starts: t such that t >= es_slot and t + di - 1 <= TLAST and <= dl_slot
            latest_start = dl_slot - p_slots + 1
            feasible_starts = [t for t in range(es_slot, latest_start + 1) if 1 <= t <= self.T and (t + p_slots - 1) <= self.T]

            # if fixed start requested, enforce it
            fixed_start_slot = None
            if info["fixed"] and info["fixed_start"]:
                try:
                    fixed_start_slot = self.hhmm_to_slot(info["fixed_start"])
                except Exception:
                    messagebox.showerror("Time format", f"Invalid fixed start for task {tid}.")
                    return
                if fixed_start_slot not in feasible_starts:
                    feasible_starts = []  # impossible to schedule at the fixed start -> mark infeasible

            # store
            tasks[tid] = {
                "d": p_slots,
                "es": es_slot,
                "dl": dl_slot,
                "p": info["p"],
                "fixed": info["fixed"],
                "fixed_start": fixed_start_slot,
                "feasible_starts": feasible_starts
            }
            if not feasible_starts:
                infeasible_tasks.append(tid)

        # Build MILP
        prob = pulp.LpProblem("SmartScheduler_PDF", pulp.LpMaximize)

        # Variables:
        # x_{i,t} binary if task i starts at t (only create for feasible starts)
        x = {}
        for i, info in tasks.items():
            for t in info["feasible_starts"]:
                x[(i,t)] = pulp.LpVariable(f"x_{i}_{t}", cat="Binary")

        # S_i binary
        S = {i: pulp.LpVariable(f"S_{i}", cat="Binary") for i in tasks}

        # C_i continuous (completion slot), lower bound 0
        C = {i: pulp.LpVariable(f"C_{i}", lowBound=0, cat="Continuous") for i in tasks}

        # Tard_i continuous >= 0
        Tard = {i: pulp.LpVariable(f"Tard_{i}", lowBound=0, cat="Continuous") for i in tasks}

        # Constraint 1: sum_t x_{i,t} == S_i  (for each i)
        for i, info in tasks.items():
            prob += pulp.lpSum([x[(i,t)] for t in info["feasible_starts"]]) == S[i], f"assign_once_{i}"

        # Constraint 2: Non-overlap and availability
        # For each slot t in T: sum_{i} sum_{k = t-d_i+1 .. t} x_{i,k} <= A_t
        # Note: ensure k in feasible starts for that task
        for t in self.W_day:
            covering_terms = []
            for i, info in tasks.items():
                di = info["d"]
                k_min = t - di + 1
                # consider starts k in feasible_starts that would make i active in slot t
                for k in info["feasible_starts"]:
                    if k_min <= k <= t:  # k makes task i active in slot t
                        covering_terms.append(x[(i,k)])
            # A_t is At[t-1]
            At_val = self.At[t-1] if 0 <= t-1 < len(self.At) else 1
            if covering_terms:
                prob += pulp.lpSum(covering_terms) <= At_val, f"no_overlap_avail_slot_{t}"
            else:
                # no tasks possibly active at this slot -> trivially <= At_val, skip explicit constraint
                pass

        # Constraint 3: Earliest start time enforced implicitly by feasible_starts (we created x only for feasible starts).
        # To mirror the PDF we could also explicitly zero-out x for t < es, but done by construction.

        # Constraint 4: Completion time Ci = sum_t (t + d_i - 1) * x_{i,t}
        for i, info in tasks.items():
            terms = []
            for t in info["feasible_starts"]:
                terms.append((t + info["d"] - 1) * x[(i,t)])
            # If not scheduled, sum = 0 -> C_i should be 0 (PDF says Ci = sum ... ; that's enforced by equality)
            prob += C[i] == pulp.lpSum(terms), f"completion_def_{i}"

        # Constraint 5 & 6: Tardiness calculation: Tard_i >= C_i - D_i; Tard_i >= 0 (lowBound)
        for i, info in tasks.items():
            D_i = info["dl"]
            prob += Tard[i] >= C[i] - D_i, f"tardiness_def_{i}"
            # second constraint Tard_i >= 0 is enforced by lowBound in variable.

        # Constraint 7: Completion time limit Ci <= TLAST
        for i in tasks:
            prob += C[i] <= self.TLAST, f"completion_limit_{i}"

        # Additional: fixed-start handling: if fixed, ensure chosen start equals that slot when S_i=1
        # Enforce: x_{i,fs} == S_i and other x_{i,t} == 0 (handled by feasible_starts and explicit constraints)
        for i, info in tasks.items():
            if info["fixed"]:
                fs = info["fixed_start"]
                if fs and (i, fs) in x:
                    # link chosen start to S_i
                    prob += x[(i, fs)] == S[i], f"fixed_link_{i}"
                    # forbid other starts
                    for t in info["feasible_starts"]:
                        if t != fs:
                            prob += x[(i, t)] == 0, f"fixed_forbid_{i}_{t}"
                else:
                    # fixed impossible -> force S_i = 0
                    prob += S[i] == 0, f"fixed_impossible_{i}"

        # Objective: combine as in PDF (maximize)
        obj_priority_sum = pulp.lpSum([tasks[i]["p"] * S[i] for i in tasks])
        obj_count = pulp.lpSum([S[i] for i in tasks])
        obj_tard_pen = pulp.lpSum([tasks[i]["p"] * Tard[i] for i in tasks])

        prob += w1 * obj_priority_sum + w2 * obj_count - w3 * obj_tard_pen, "Combined_Objective"

        # Solve
        self.status.configure(text="Solving...")
        self.root.update_idletasks()
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=60)
        prob.solve(solver)
        status_text = pulp.LpStatus[prob.status]
        self.status.configure(text=f"Solver status: {status_text}")

        # Extract schedule: for each i, find t with x_{i,t} = 1
        schedule = []
        slot_occupancy = np.zeros((len(tasks), self.T), dtype=int)
        tid_to_idx = {}
        for idx, (i, info) in enumerate(tasks.items()):
            tid_to_idx[i] = idx
            # check S[i]
            s_val = pulp.value(S[i])
            if s_val is not None and s_val >= 0.5:
                chosen = None
                for t in info["feasible_starts"]:
                    if (i, t) in x and pulp.value(x[(i, t)]) is not None and pulp.value(x[(i, t)]) >= 0.5:
                        chosen = t
                        break
                if chosen is None:
                    # fallback: compute Ci and infer start = Ci - d + 1
                    Ci_val = pulp.value(C[i]) if pulp.value(C[i]) is not None else None
                    if Ci_val and info["d"] > 0:
                        chosen = int(round(Ci_val)) - info["d"] + 1
                if chosen is None:
                    continue
                start_dt = self.DAY_START + timedelta(minutes=(chosen - 1) * self.SLOT_MIN)
                end_dt = start_dt + timedelta(minutes=info["d"] * self.SLOT_MIN)
                Tard_val = pulp.value(Tard[i]) if pulp.value(Tard[i]) is not None else 0.0
                schedule.append((i, start_dt, end_dt, info["d"], info["p"], chosen, Tard_val))
                for sl in range(chosen - 1, chosen - 1 + info["d"]):
                    if 0 <= sl < self.T:
                        slot_occupancy[idx, sl] = 1

        # Display textual schedule and objective
        self.text_out.delete("1.0", tk.END)
        self.text_out.insert(tk.END, f"Status: {status_text}\n")
        try:
            obj_val = pulp.value(prob.objective)
            self.text_out.insert(tk.END, f"Objective value: {obj_val}\n\n")
        except Exception:
            pass

        if schedule:
            self.text_out.insert(tk.END, "Scheduled tasks:\n")
            for row in sorted(schedule, key=lambda r: r[1]):
                i, sdt, edt, pslots, pri, chosen, tard = row
                self.text_out.insert(tk.END, f" Task {i}: {sdt.strftime('%H:%M')} - {edt.strftime('%H:%M')}  ({pslots * self.SLOT_MIN} min, {pslots} slots)  p={pri}  tard={tard}\n")
        else:
            self.text_out.insert(tk.END, "No tasks scheduled.\n")

        if infeasible_tasks:
            self.text_out.insert(tk.END, f"\nTasks with no feasible starts (due to windows or fixed start): {infeasible_tasks}\n")

        # Save for plotting
        self._last_tasks = tasks
        self._last_schedule = schedule
        self._last_slot_occupancy = slot_occupancy
        self._tid_to_idx = tid_to_idx

        # Draw plot
        self.redraw_plot()

    # ---------------- Plotting (Gantt + optional heatmap) ----------------
    def redraw_plot(self):
        self.ax.clear()
        if not hasattr(self, "_last_schedule") or not self._last_schedule:
            self.ax.text(0.5, 0.5, "No schedule yet. Solve to visualize.", ha="center", va="center")
            # also show availability row visually (At)
            # draw occupancy rectangles for blocked slots
            for idx, a in enumerate(self.At):
                if a == 0:
                    left = idx * self.SLOT_MIN
                    self.ax.add_patch(matplotlib.patches.Rectangle((left, -0.8), self.SLOT_MIN, 0.4, color="red", alpha=0.25, edgecolor=None))
            self.canvas.draw()
            return

        schedule = self._last_schedule
        if schedule:
            schedule_sorted = sorted(schedule, key=lambda r: r[1])
            y_positions = list(range(len(schedule_sorted)))
            for idx, (i, sdt, edt, pslots, pri, chosen, tard) in enumerate(schedule_sorted):
                start_minutes = (sdt - self.DAY_START).total_seconds() / 60.0
                duration_minutes = (edt - sdt).total_seconds() / 60.0
                if i not in self.random_colors:
                    self.random_colors[i] = (random.random(), random.random(), random.random())
                color = self.random_colors[i]
                self.ax.barh(idx, duration_minutes, left=start_minutes, height=0.6, color=color, edgecolor="k")
                self.ax.text(start_minutes + duration_minutes / 2.0, idx, f"{i}", va="center", ha="center", color="white", fontsize=9, fontweight="bold")

            # x ticks at every hour (or appropriate interval)
            slot_ticks = []
            slot_labels = []
            for t in range(0, self.T + 1):
                minutes = t * self.SLOT_MIN
                slot_time = self.DAY_START + timedelta(minutes=minutes)
                if t % max(1, int(60 / self.SLOT_MIN)) == 0:
                    slot_ticks.append(minutes)
                    slot_labels.append(slot_time.strftime("%H:%M"))

            self.ax.set_yticks(y_positions)
            self.ax.set_yticklabels([f"{r[0]} ({r[1].strftime('%H:%M')})" for r in schedule_sorted])
            self.ax.set_xticks(slot_ticks)
            self.ax.set_xticklabels(slot_labels, rotation=45)
            self.ax.set_xlabel("Time")
            self.ax.set_title("Scheduled Tasks (Gantt-style)")
            self.ax.grid(axis="x", linestyle="--", alpha=0.5)
            self.ax.set_ylim(-1, len(schedule_sorted) + 0.5)

        # show availability row (blocked slots) and optional occupancy heatmap
        # draw blocked slot rectangles below bars
        ybase = -0.8
        height = 0.4
        for idx, a in enumerate(self.At):
            if a == 0:
                left_min = idx * self.SLOT_MIN
                self.ax.add_patch(matplotlib.patches.Rectangle((left_min, ybase), self.SLOT_MIN, height, color="red", alpha=0.25, edgecolor=None))
        if any(a == 0 for a in self.At):
            self.ax.plot([], [], color="red", alpha=0.25, linewidth=6, label="Blocked slot (At=0)")
            self.ax.legend(loc="upper right")

        if self.show_slots_var.get() and hasattr(self, "_last_slot_occupancy"):
            occ = self._last_slot_occupancy
            occ_any = occ.sum(axis=0) > 0 if occ.size else np.array([])
            if occ_any.size:
                ybase2 = -1.3
                height2 = 0.3
                for idx, val in enumerate(occ_any):
                    if val:
                        left_min = idx * self.SLOT_MIN
                        self.ax.add_patch(matplotlib.patches.Rectangle((left_min, ybase2), self.SLOT_MIN, height2, color="tab:gray", alpha=0.6, edgecolor=None))
                self.ax.plot([], [], color="tab:gray", alpha=0.6, linewidth=6, label="Occupied slot")
                self.ax.legend(loc="upper right")

        self.canvas.draw()


if _name_ == "_main_":
    root = tk.Tk()
    app = SchedulerPDFGUI(root)
    root.geometry("1200x800")
    root.mainloop()