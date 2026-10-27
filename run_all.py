"""Rebuild every dataset, result and chart from scratch, in order.

    python3 run_all.py            # everything (about 2-3 minutes)
    python3 run_all.py --quick    # skip regenerating the random wffs

Steps:
  1. examples/*.pl              -> examples/puzzles.pl.csv           (make_examples.py)
  2. random Horn wffs           -> data/generated, multiquery, large (generate_wffs.py)
  3. Brute-SAT on labeled sets  -> results/brute_*_results.csv       (run_brute.py)
  4. Proplog on every set       -> results/proplog_*_results.csv     (proplog_solver.py)
  5. charts                     -> charts/*.png                      (plot_results.py)
The seeds are fixed, so step 2 always produces the same wffs.
"""
import subprocess
import sys

PY = sys.executable

GENERATE = [
    # 170 wffs, 2-18 atoms, one query each, half S / half U
    ['generate_wffs.py', '--sizes', '2-18', '--per-size', '10', '--seed', '0',
     '--out', 'data/generated.pl.csv'],
    # 90 wffs, 2-16 atoms, up to 3 queries each
    ['generate_wffs.py', '--sizes', '2-16', '--per-size', '6', '--max-queries', '3',
     '--seed', '1', '--out', 'data/multiquery.pl.csv'],
    # 24 wffs, 100-20000 atoms: too big for Brute-SAT, Proplog timing only
    ['generate_wffs.py', '--sizes', '100,200,500,1000,2000,5000,10000,20000',
     '--per-size', '3', '--brute-max-atoms', '20', '--seed', '0', '--no-cnf',
     '--out', 'data/large.pl.csv'],
]
BRUTE_SETS = ['examples/puzzles.pl.csv', 'data/generated.pl.csv', 'data/multiquery.pl.csv']
PROPLOG_SETS = BRUTE_SETS + ['data/large.pl.csv']


def run(args):
    print('\n$ python3 ' + ' '.join(args), flush=True)
    subprocess.run([PY] + args, check=True)


if __name__ == '__main__':
    quick = '--quick' in sys.argv[1:]
    run(['make_examples.py'])
    if not quick:
        for cmd in GENERATE:
            run(cmd)
    for path in BRUTE_SETS:
        run(['run_brute.py', path])
    for path in PROPLOG_SETS:
        run(['proplog_solver.py', '--problem', path])
    run(['plot_results.py'])
    print('\nDone. Charts are in charts/, results in results/.')