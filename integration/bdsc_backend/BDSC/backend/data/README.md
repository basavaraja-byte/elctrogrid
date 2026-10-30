# DispatchGrid Electrician-Only Synthetic Dataset

## Contents
- `electricians.csv`: 20 synthetic electricians, skills, eligible zones, shifts, starting coordinates.
- `electrical_jobs.csv`: 100 synthetic electrical service jobs. J100 is an intentional infeasible edge case.
- `travel_times.csv`: 14,400 pairwise travel estimates for 120 locations (20 homes + 100 job locations).
- `technician_unavailability.csv`: sample unavailability intervals.
- `disruption_scenarios.csv`: seven reproducible demo scenarios.
- `scenario_job_J101.csv`: urgent electrical job to insert when scenario D02 is triggered.

## Assumptions
All data and coordinates are synthetic and fictional. The 20 km x 20 km coordinate plane is not a real map.
Times are minutes after midnight: 480 = 08:00, 720 = 12:00, 1020 = 17:00.
Travel times use planar distance, a 1.25 road-detour multiplier, assumed 30 km/h average speed, and rounding up to 5-minute increments. These are repeatable demo estimates, not navigation data.
Skills are separated by `|`; technicians must possess every required skill. Feasibility requires skill and zone eligibility, travel, time-window compliance, shift compliance, and no appointment overlap.
Completed and in-progress jobs must remain protected during recovery. Hard constraints cannot be traded away for a better weighted score.
J100 should remain unassigned with a grounded explanation; do not force an assignment.

## Suggested demo
1. Generate a baseline schedule for the 100 electrical jobs.
2. Demonstrate nearest-feasible assignment and a rejected infeasible candidate.
3. Trigger D01 (E004 unavailable from noon), produce a recovery proposal, compare metrics.
4. Approve or reject the proposal in the Operations Manager dashboard.
5. Trigger D02 to insert critical job J101.
6. Show J100 unassigned with a precise reason.
7. Compare travel time, SLA compliance, unassigned jobs, and schedule changes before and after.

Synthetic hackathon data; freely usable for this prototype.
