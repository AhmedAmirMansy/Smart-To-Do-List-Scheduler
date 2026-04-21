# Smart-To-Do-List-Scheduler
Time management is a major challenge for students and professionals alike. A simple “to-do  list” only records tasks, but it does not tell us when to do them or in what order. In this project,  you will design and implement a smart scheduler that converts a list of tasks (with deadlines,  durations, and priorities) into an optimized daily plan.  
Objective Function:
Max Z = w1 * sum(p_i * S_i) + w2 * sum(S_i) - w3 * sum(p_i * Tard_i)
The GUI allows the user to enter tasks, define availability slots, adjust objective weights,
solve the MILP, and visualize the resulting schedule.
GUI overview:
<img width="877" height="525" alt="image" src="https://github.com/user-attachments/assets/683185c3-51a8-4263-a33c-e875036513e5" />
1. Entering Tasks
At the top of the interface, tasks can be added or edited by filling in the following fields:
• Task ID: A unique identifier, such as T1, Gym, Math HW.
• Duration (minutes): Length of the task in minutes. The system converts this into 15-
minute slots.
• Earliest Start (HH:MM): The allowed earliest start time.
• Deadline (HH:MM): The latest allowed completion time. Tardiness is computed
relative to this.
• Priority p_i: A numeric value indicating task importance.
• Fixed Start (optional): If selected, the task must start exactly at the specified time.
After filling the required fields, click Add / Update Task to insert the task into the task table.
2. Adjusting Slot Availability (A_t)
Availability slots A_t determine which time slots are usable throughout the day:
• 1 → Slot is available
• 0 → Slot is blocked
The GUI allows three types of availability modifications:
• Toggle individual slots: Clicking the checkbox for each slot (08:00, 08:15, …).
• Block interval: Enter a “From” and “To” time to block all slots in that range.
• Set Work Window: Defines general working hours for the day.
This setting directly enforces the constraint that no task can be scheduled in a blocked
slot.
3. Setting Objective Weights (w1, w2, w3)
The objective function:
Max Z = w1 * sum(p_i * S_i) + w2 * sum(S_i) - w3 * sum(p_i * Tard_i)
Weights control the scheduling behavior:
• w1: Priority reward
• w2: Reward for scheduling more tasks
• w3: Penalty on tardiness
Common settings:
• High-priority focus: w1=10, w2=2, w3=5
• Balanced: w1=5, w2=5, w3=10
• Anti-lateness: w1=2, w2=1, w3=20
4. Viewing Tasks
All entered tasks appear in the task table, showing:
• Task ID
• Duration
• Earliest Start
• Deadline
• Priority
• Fixed (yes/no)
• Fixed Start Time (if any)
Selecting a task loads its details back into the input form for editing.
The user can remove tasks using the Remove Selected button.
5. Solving the Optimization Problem
After entering all tasks, availability, and objective weights, click Solve (PuLP CBC) to trigger
the MILP solver.
Constraints enforced:
• Task assignment: sum_t x_{i,t} = S_i
• Slot capacity / availability: sum_{i,k} x_{i,k} <= A_t
• Earliest start constraints
• Completion time: C_i = sum_t (t + d_i - 1) * x_{i,t}
• Tardiness: Tard_i = max(C_i - D_i, 0)
• End-of-day limit: C_i <= T_last
• Fixed start constraints (if selected)
6. Reading the Schedule Output
The output panel displays:
• Optimization status (Optimal, Feasible, Infeasible)
• Objective value
• All scheduled tasks in chronological order, showing start and end times
Tasks that cannot be feasibly scheduled are automatically excluded.
7. Visualization
The right panel displays a Gantt-style visualization:
• Each scheduled task is shown as a colored bar.
• Blocked slots (A_t = 0) appear visually distinct.
• Optional heatmap of slot occupancy may be enabled.
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
• Some tasks may be intentionally excluded to avoid lateness
<img width="878" height="526" alt="image" src="https://github.com/user-attachments/assets/94e0517a-7fd6-42cd-b569-914218ab7af5" />
