"""Compile every examples/*.pl into one Proplog CSV file.

    python make_examples.py                       -> examples/puzzles.pl.csv
    python make_examples.py examples out.pl.csv

Each puzzle becomes one wff: problem numbers 1, 2, ... in alphabetical file
order, puzzle name (file name) in the n,0 row, label '?'. Then run
    python run_brute.py examples/puzzles.pl.csv
to label them and get examples/puzzles.pl.cnf.csv.
"""
import glob
import os
import sys

from proplog_to_CSV_CNF import write_pl_csv
from proplog_to_CSV import pl_file_to_pl_object, pl_object_to_wff, title_for


def make_examples(folder='examples', out=None):
    out = out or os.path.join(folder, 'puzzles.pl.csv')
    paths = sorted(glob.glob(os.path.join(folder, '*.pl')))
    wffs = [pl_object_to_wff(pl_file_to_pl_object(p), pid, title_for(p))
            for pid, p in enumerate(paths, 1)]
    write_pl_csv(wffs, out)
    return out, paths


if __name__ == '__main__':
    out, paths = make_examples(*sys.argv[1:3])
    for pid, p in enumerate(paths, 1):
        print(f"  {pid}: {p}")
    print(f"Wrote {len(paths)} puzzle(s) to {out}")