"""Generate random Proplog (Horn) wffs, labeled by Brute-SAT.

    to run the file, commands can be written as such:
    python generate_wffs.py  # defaults below
    python generate_wffs.py --sizes 2-18 --per-size 10 --seed 1
    python generate_wffs.py --sizes 2-16,32,64,128,256 --brute-max-atoms 18

Writes  data/generated.pl.csv  (Proplog CSV, FORMAT.md) and its companion
data/generated.pl.cnf.csv  (plain CNF for Brute-SAT).

Each wff over n atoms has
  * 1 .. max(1, n/4) facts               (distinct atoms)
  * n/2+1 .. 2n rules, head random, body of 1 .. --max-body other atoms
  * 1 .. --max-queries queries of 1 .. --max-body atoms
and is labeled by running Brute-SAT on its clauses:
  S  satisfiable (query not provable); the model goes in the 'a' row
  U  unsatisfiable (query provable)
  ?  Brute-SAT timed out, or n > --brute-max-atoms so it was not run
For sizes Brute-SAT can label, candidates are drawn until each size has
--per-size wffs split evenly between S and U, so the scatter chart gets
both colours. Larger sizes (labeled ?) are only for timing the Proplog solver.
"""

import argparse
import random
import sys

from BruteSAT import brute_sat_with_timeout
from proplog_to_CSV_CNF import to_clauses, write_pl_csv, write_cnf_csv, cnf_path_for

STATUS_LABEL = {'SAT': 'S', 'UNSAT': 'U', 'TIMEOUT': '?'}


def parse_sizes(text):
    """'2-6,10,20' -> [2, 3, 4, 5, 6, 10, 20]"""
    sizes = []
    for part in text.split(','):
        part = part.strip()
        if '-' in part:
            lo, hi = part.split('-')
            sizes += range(int(lo), int(hi) + 1)
        elif part:
            sizes.append(int(part))
    if any(n < 2 for n in sizes):
        raise ValueError('sizes must be at least 2 atoms')
    return sizes


def random_wff(n, max_body, max_queries, rng):
    """One random Horn wff over atoms 1..n, as a list of statements."""
    atoms = list(range(1, n + 1))
    statements = [('f', a, []) for a in sorted(rng.sample(atoms, rng.randint(1, max(1, n // 4))))]
    seen = set()
    for _ in range(rng.randint(n // 2 + 1, 2 * n)):
        head = rng.choice(atoms)
        others = [a for a in atoms if a != head]
        body = rng.sample(others, rng.randint(1, min(max_body, len(others))))
        key = (head, frozenset(body))
        if key not in seen:                 # skip exact duplicate rules
            seen.add(key)
            statements.append(('r', head, body))
    for _ in range(rng.randint(1, max_queries)):
        statements.append(('q', None, rng.sample(atoms, rng.randint(1, min(max_body, n)))))
    return statements


def label_with_brute(n, statements, timeout):
    status, assignment, _, elapsed = brute_sat_with_timeout(
        n, to_clauses({'statements': statements}), timeout)
    label = STATUS_LABEL[status]
    return label, (assignment if label == 'S' else None), elapsed


def generate(sizes, per_size, max_body, max_queries, timeout, brute_max_atoms,
             seed, start_id=1, max_tries=200, verbose=True):
    rng = random.Random(seed)
    wffs = []
    pid = start_id
    for n in sizes:
        kept = []
        if n > brute_max_atoms:
            # too big for Brute-SAT: unlabeled, for Proplog timing only
            kept = [('?', None, random_wff(n, max_body, max_queries, rng))
                    for _ in range(per_size)]
        else:
            want = {'S': per_size // 2, 'U': per_size - per_size // 2}
            tries = timeouts = 0
            while (want['S'] > 0 or want['U'] > 0) and tries < max_tries * per_size:
                tries += 1
                st = random_wff(n, max_body, max_queries, rng)
                label, model, _ = label_with_brute(n, st, timeout)
                if label == '?':
                    kept.append(('?', None, st))   # timed out: keep it unlabeled
                    timeouts += 1
                    if timeouts >= 2:              # this size is too big for Brute-SAT
                        break
                elif want[label] > 0:
                    kept.append((label, model, st))
                    want[label] -= 1
            short = {k: v for k, v in want.items() if v > 0}
            if short and verbose:
                print(f"  n={n}: gave up after {tries} candidates, short {short}", file=sys.stderr)
        for k, (label, model, st) in enumerate(kept, 1):
            wffs.append({'problem_id': pid, 'label': label, 'n_atoms': n,
                         'title': f'gen_n{n}_{k}', 'names': {},
                         'assignment': model, 'statements': st})
            pid += 1
        if verbose:
            counts = {l: sum(1 for x in kept if x[0] == l) for l in 'SU?'}
            print(f"n={n:4d}: {len(kept)} wffs  S={counts['S']} U={counts['U']} ?={counts['?']}")
    return wffs


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sizes', default='2-16', help="atom counts, e.g. '2-16,32,64' (default 2-16)")
    ap.add_argument('--per-size', type=int, default=10, help='wffs per size (default 10)')
    ap.add_argument('--max-body', type=int, default=3, help='longest rule body / query (default 3)')
    ap.add_argument('--max-queries', type=int, default=1, help='queries per wff (default 1)')
    ap.add_argument('--timeout', type=int, default=60, help='Brute-SAT seconds per wff (default 60)')
    ap.add_argument('--brute-max-atoms', type=int, default=20,
                    help='do not run Brute-SAT above this many atoms (default 20)')
    ap.add_argument('--seed', type=int, default=0, help='random seed (default 0)')
    ap.add_argument('--start-id', type=int, default=1, help='first problem number (default 1)')
    ap.add_argument('--out', default='data/generated.pl.csv', help='output Proplog CSV')
    args = ap.parse_args()

    wffs = generate(parse_sizes(args.sizes), args.per_size, args.max_body, args.max_queries,
                    args.timeout, args.brute_max_atoms, args.seed, args.start_id)
    write_pl_csv(wffs, args.out)
    write_cnf_csv(wffs, cnf_path_for(args.out))
    print(f"Wrote {len(wffs)} wffs to {args.out} and {cnf_path_for(args.out)}")