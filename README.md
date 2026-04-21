# Smart-To-Do-List-Scheduler
Time management is a major challenge for students and professionals alike. A simple “to-do  list” only records tasks, but it does not tell us when to do them or in what order. In this project,  you will design and implement a smart scheduler that converts a list of tasks (with deadlines,  durations, and priorities) into an optimized daily plan.  
Objective Function:
Max Z = w1 * sum(p_i * S_i) + w2 * sum(S_i) - w3 * sum(p_i * Tard_i)
The GUI allows the user to enter tasks, define availability slots, adjust objective weights,
solve the MILP, and visualize the resulting schedule.
GUI overview:
<img width="877" height="525" alt="image" src="https://github.com/user-attachments/assets/683185c3-51a8-4263-a33c-e875036513e5" />
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Tkinter-GUI-FF6F00?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PuLP-Linear%20Programming-2C8EBB?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Matplotlib-Visualization-11557c?style=for-the-badge&logo=plotly&logoColor=white" />
</p>

# 📋 Smart To-Do List Scheduler with GUI

> An intelligent task scheduling application that uses **Mixed-Integer Linear Programming (MILP)** to optimally schedule your daily tasks — with a full **Tkinter GUI**, **Gantt chart visualization**, and support for priorities, deadlines, fixed-time tasks, and availability constraints.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Optimal Scheduling** | Uses PuLP's CBC solver to find the mathematically optimal schedule |
| ⏰ **Slot-Based Planning** | Divides your day into configurable time slots (default: 15 min) |
| 🎯 **Priority-Aware** | Higher-priority tasks are scheduled first with weighted objectives |
| 📌 **Fixed-Time Tasks** | Pin tasks to specific start times (e.g., meetings) |
| 🚫 **Availability Blocking** | Block off time intervals (lunch, breaks, unavailable periods) |
| ⚠️ **Tardiness Penalties** | Penalizes tasks that finish after their deadlines |
| 📊 **Gantt Chart** | Interactive Gantt-style visualization with blocked-slot highlighting |
| 🔥 **Slot Occupancy Heatmap** | Optional overlay showing which slots are occupied |
| ✏️ **Full CRUD** | Add, edit, and remove tasks through the GUI |
| ⚖️ **Tunable Weights** | Adjust objective weights (`w1`, `w2`, `w3`) to control scheduling behavior |

---

## 📸 How It Works

The scheduler implements a **mathematical optimization model** with the following formulation:

### Decision Variables

| Variable | Type | Meaning |
|----------|------|---------|
| `x_{i,t}` | Binary | 1 if task `i` starts at slot `t` |
| `S_i` | Binary | 1 if task `i` is scheduled |
| `C_i` | Continuous | Completion slot of task `i` |
| `Tard_i` | Continuous (≥ 0) | Tardiness of task `i` (slots past deadline) |

### Objective Function (Maximize)

```
Z = w1 × Σ(pᵢ × Sᵢ) + w2 × Σ(Sᵢ) − w3 × Σ(pᵢ × Tardᵢ)
```

| Term | Purpose |
|------|---------|
| `w1 × Σ(pᵢ × Sᵢ)` | Reward scheduling high-priority tasks |
| `w2 × Σ(Sᵢ)` | Reward scheduling as many tasks as possible |
| `w3 × Σ(pᵢ × Tardᵢ)` | Penalize tardiness, weighted by priority |

### Constraints

1. **Assignment** — Each task is assigned to at most one start slot
2. **Non-overlap & Availability** — No two tasks share a slot; tasks can only use available slots (`Aₜ = 1`)
3. **Earliest Start** — Tasks cannot start before their earliest start time
4. **Completion Time** — `Cᵢ = Σₜ (t + dᵢ − 1) × x_{i,t}`
5. **Tardiness** — `Tardᵢ ≥ Cᵢ − Dᵢ` (deadline)
6. **Non-negativity** — `Tardᵢ ≥ 0`
7. **Completion Limit** — `Cᵢ ≤ T_last`

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- The following Python packages:

```bash
pip install pulp matplotlib numpy
```

> **Note:** `tkinter` is included with most Python installations. If not, install it via your system package manager (e.g., `sudo apt install python3-tk` on Ubuntu).

### Run the Application

```bash
python smarttodolistschedulerwithgui.py
```

The GUI window will open at **1200×800** resolution.

---

## 🖥️ User Guide

### 1. Configure Your Work Window

Click **"Set Work Window (start/end)"** to define your planning day (default: `08:00` → `22:00`). This determines the total number of time slots.

### 2. Set Availability

Use the slot checkbox strip at the top to toggle individual time slots, or use the convenience buttons:

| Button | Action |
|--------|--------|
| **Block interval** | Set a range of slots as unavailable (`Aₜ = 0`) |
| **Unblock interval** | Re-enable a blocked range |
| **Set All Available** | Reset all slots to available |

### 3. Add Tasks

Fill in the task form:

| Field | Description | Example |
|-------|-------------|---------|
| **ID** | Unique task identifier | `Study` |
| **Duration (min)** | How long the task takes | `60` |
| **Earliest (HH:MM)** | Earliest allowed start time | `09:00` |
| **Deadline (HH:MM)** | Must finish by this time | `17:00` |
| **Priority pᵢ** | Importance weight (higher = more important) | `8` |
| **Fixed** | Check to pin to a specific time | ☑ |
| **Fixed Start (HH:MM)** | Required start time (if fixed) | `14:00` |

Click **"Add / Update Task"** to save. Select a task in the table to edit it, or click **"Remove Selected"** to delete.

### 4. Tune Objective Weights

Adjust the three weights to control scheduling behavior:

| Weight | Default | Effect |
|--------|---------|--------|
| **w1** | 10 | How much to prioritize high-priority tasks |
| **w2** | 5 | How much to maximize the number of scheduled tasks |
| **w3** | 20 | How harshly to penalize tardiness |

### 5. Solve & Visualize

Click **"Solve (PuLP CBC)"** to run the optimizer. The results appear in two places:

- **Schedule Output** (text) — Lists each scheduled task with start/end times, duration, priority, and tardiness
- **Visualization** (Gantt chart) — Color-coded horizontal bars showing the schedule, with red zones for blocked slots

Toggle **"Show slot occupancy heatmap"** and click **"Refresh Plot"** for an additional overlay.

---

## 📐 Example Scenario

```
Work Window:  08:00 - 22:00 (56 slots × 15 min)
Blocked:      12:00 - 13:00 (lunch break)

Tasks:
  ID: "Math HW"     | Duration: 90 min  | ES: 08:00 | DL: 14:00 | Priority: 9
  ID: "Gym"         | Duration: 60 min  | ES: 16:00 | DL: 20:00 | Priority: 5
  ID: "Team Call"   | Duration: 30 min  | ES: 10:00 | DL: 11:00 | Priority: 10 | Fixed: 10:00
  ID: "Read Paper"  | Duration: 45 min  | ES: 08:00 | DL: 22:00 | Priority: 3

Weights: w1=10, w2=5, w3=20
```

The solver will:
- Pin **Team Call** at 10:00 (fixed constraint)
- Schedule **Math HW** early to avoid tardiness (high priority)
- Respect the 12:00–13:00 lunch block
- Fit **Gym** and **Read Paper** in remaining slots

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **GUI Framework** | Tkinter (ttk themed widgets) |
| **Optimization Solver** | PuLP with CBC (COIN-OR Branch and Cut) |
| **Visualization** | Matplotlib (embedded in Tkinter via `FigureCanvasTkAgg`) |
| **Numerical Computing** | NumPy |
| **Language** | Python 3 |

---

## 📁 Project Structure

```
├── smarttodolistschedulerwithgui.py   # Main application (GUI + solver + visualization)
└── README.md                          # This file
```

The entire application is self-contained in a single Python file with the following architecture:

```
SchedulerPDFGUI (class)
├── __init__          → Initialize parameters, data structures, and UI
├── create_widgets    → Build the full Tkinter interface
├── Task Management   → add_or_update_task, remove_selected, on_tree_select
├── Availability      → block/unblock intervals, set_work_window, set_all_available
├── Time Helpers      → hhmm_to_slot, _slot_label, _valid_hhmm
├── Solver            → solve_and_visualize (builds & solves the MILP)
└── Visualization     → redraw_plot (Gantt chart + availability + heatmap)
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

This allows quick confirmation of a valid, conflict-free schedule.
Example Study Scenarios
Scenario 1: High Priority Focus
Weights: w1=1, w2=0, w3=0.5
• Prioritizes tasks with high importance values
• Fewer tasks may be scheduled
• Tardiness lightly discouraged
<img width="878" height="525" alt="image" src="https://github.com/user-attachments/assets/90b34603-d068-40d2-ba97-da9e839d3e06" />
Scenario 2: Balanced Scheduling
Weights: w1=0.5, w2=0.5, w3=1
• Balances priority, number of tasks, and lateness
• Medium-priority tasks are more likely to be included
• More tasks may be scheduled while respecting deadlines
<img width="878" height="527" alt="image" src="https://github.com/user-attachments/assets/df937cf2-20e5-4d7b-9bbe-1cbc6d971277" />
Scenario 3: Strong Anti-Lateness
Weights: w1=0.2, w2=0.1, w3=10
• Heavily penalizes tardiness
• Tasks must finish before deadlines


---

<p align="center">
  Built with ❤️ using Python, PuLP, and Tkinter
</p>
• Some tasks may be intentionally excluded to avoid lateness
<img width="878" height="526" alt="image" src="https://github.com/user-attachments/assets/94e0517a-7fd6-42cd-b569-914218ab7af5" />
