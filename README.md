# Proplog Interpreter

Description@Joshua

This repository contains:
 
* a file format for Proplog programs, based on the CNF `.csv` format used by
  Brute-SAT ([FORMAT.md](FORMAT.md));
* example problems derived from logic puzzles ([examples/](examples/));
* a wff generator that writes random Proplog programs, each labeled
  satisfiable or not by **Brute-SAT**, with a satisfying assignment when one
  exists;
* a linear-time Proplog solver;
* timing results comparing the two solvers on 287 problems, and charts.


## Requirements
 
* Python 3.9 or newer (tested on 3.11 and 3.13).
* `matplotlib` for the charts: `pip install matplotlib`.
* Linux or macOS: Brute-SAT's timeout uses `SIGALRM`, which Windows does not have.
## Quick start
 
Rebuild every dataset, result and chart (about 2-3 minutes; nearly all of it is
Brute-SAT):
 
```
python3 run_all.py
```
 
Or run the steps individually:
 
```
python3 proplog_to_CSV.py examples/picnic.pl          # .pl -> examples/picnic.pl.csv
python3 run_brute.py examples/picnic.pl.csv           # label it with Brute-SAT
python3 proplog_solver.py --problem examples/picnic.pl.csv --verbose
```
 
## Results
 
On all **263** problems that Brute-SAT could solve, the two solvers give the
same answer. On the 24 large problems, every `S` assignment the Proplog solver
returned was checked against every clause.
 
**Speedup** is how many times faster Proplog is than Brute-SAT on the same
problem (Brute-SAT's time divided by Proplog's time). These were run on Ricky-Bobby
Taking the median over the problems:
 
| Problems | Median speedup |
|---|---|
| All 263 problems both solvers solved | **103x** |
| Problems with 15 or more atoms | **24,404x** |
 
The speedup grows with size because Brute-SAT's work doubles with every extra
atom while Proplog's barely changes. The slowest problem for Brute-SAT
(18 atoms) took it 1.35 seconds; Proplog solved it in microseconds.