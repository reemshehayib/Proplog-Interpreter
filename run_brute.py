"""Solve every wff in a Proplog CSV file with Brute-SAT, record the times, and
annotate the file with the answers.

    python run_brute.py examples/picnic.pl.csv
    python run_brute.py data/generated.pl.csv --timeout 30 --no-annotate

Steps for each input  X.pl.csv:
  1. write  X.pl.cnf.csv  (proplog_to_CSV_CNF.py)
  2. read it back with the Brute-SAT parser and solve each wff with Brute-SAT
  3. write  results/brute_X_results.csv  (one row per wff, columns below)
  4. unless --no-annotate, rewrite X.pl.csv and X.pl.cnf.csv with the label
     (S / U / ? on timeout) in the 'c' row and, for S, the model in an 'a' row

Results columns (the Proplog solver writes the same ones so the two can be
joined on problem_id):
  problem_id, n_vars, n_clauses, n_literals, label, status,
  satisfied_count, elapsed_sec, matched_label
'label' is the label the file had before this run; 'status' is Brute-SAT's
answer (S, U or ?). matched_label is blank when there was no prior label.
Only the solve is timed, not parsing. Wffs with more than --max-atoms atoms
are skipped (status ?, elapsed_sec blank) since 2^n would never finish.
"""
import argparse
import csv
import os

from BruteSAT import parse_cnf_csv, brute_sat_with_timeout
from proplog_to_CSV_CNF import read_pl_csv, write_pl_csv, write_cnf_csv, cnf_path_for

RESULT_COLUMNS = ['problem_id', 'n_vars', 'n_clauses', 'n_literals', 'label',
                  'status', 'satisfied_count', 'elapsed_sec', 'matched_label']

STATUS_LABEL = {'SAT': 'S', 'UNSAT': 'U', 'TIMEOUT': '?'}


def solve_clauses(n_vars, clauses, timeout):
    """Run Brute-SAT. Returns (label S/U/?, model or None, satisfied_count, seconds)."""
    status, assignment, count, elapsed = brute_sat_with_timeout(n_vars, clauses, timeout)
    label = STATUS_LABEL[status]
    return label, (assignment if label == 'S' else None), count, elapsed


def results_path_for(pl_csv_path, results_dir='results'):
    base = os.path.basename(pl_csv_path)
    for ext in ('.pl.csv', '.csv'):
        if base.endswith(ext):
            base = base[:-len(ext)]
            break
    return os.path.join(results_dir, f'brute_{base}_results.csv')


def run(pl_csv_path, timeout=60, results_path=None, annotate=True, verbose=True,
        max_atoms=25):
    wffs = read_pl_csv(pl_csv_path)
    cnf_path = cnf_path_for(pl_csv_path)
    write_cnf_csv(wffs, cnf_path)
    cnf_wffs = parse_cnf_csv(cnf_path)          # Brute-SAT reads the CNF file

    rows = []
    for wff, cnf in zip(wffs, cnf_wffs):
        assert wff['problem_id'] == cnf['problem_id']
        if cnf['n_vars'] > max_atoms:            # 2^n is hopeless: don't even start
            label, model, count, elapsed = '?', None, None, None
        else:
            label, model, count, elapsed = solve_clauses(cnf['n_vars'], cnf['clauses'], timeout)
        prior = wff['label']
        matched = '' if prior not in ('S', 'U') or label == '?' else (prior == label)
        rows.append({
            'problem_id': cnf['problem_id'], 'n_vars': cnf['n_vars'],
            'n_clauses': cnf['n_clauses'],
            'n_literals': sum(len(c) for c in cnf['clauses']),
            'label': prior, 'status': label, 'satisfied_count': count,
            'elapsed_sec': elapsed, 'matched_label': matched,
        })
        if verbose:
            name = f" ({wff['title']})" if wff['title'] else ''
            flag = '  <-- DISAGREES WITH FILE LABEL' if matched is False else ''
            print(f"problem {cnf['problem_id']}{name}: n={cnf['n_vars']} "
                  f"m={cnf['n_clauses']} -> {label}"
                  + (f" in {elapsed:.6f}s" if elapsed is not None else ' (skipped, too many atoms)')
                  + flag)
        if annotate and label != '?':
            wff['label'], wff['assignment'] = label, model
        elif annotate and wff['label'] not in ('S', 'U'):
            wff['label'], wff['assignment'] = '?', None   # keep a known label on timeout

    results_path = results_path or results_path_for(pl_csv_path)
    os.makedirs(os.path.dirname(os.path.abspath(results_path)), exist_ok=True)
    with open(results_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    if annotate:
        write_pl_csv(wffs, pl_csv_path)
        write_cnf_csv(wffs, cnf_path)
    return rows, results_path


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pl_csv', nargs='+', help='Proplog CSV file(s)')
    ap.add_argument('--timeout', type=int, default=60, help='seconds per wff (default 60)')
    ap.add_argument('--max-atoms', type=int, default=25,
                    help='skip Brute-SAT (status ?) above this many atoms (default 25)')
    ap.add_argument('--results', help='results CSV path (only with one input file)')
    ap.add_argument('--no-annotate', action='store_true',
                    help='do not write labels/models back into the input files')
    args = ap.parse_args()
    if args.results and len(args.pl_csv) > 1:
        ap.error('--results can only be used with one input file')
    for path in args.pl_csv:
        rows, out = run(path, args.timeout, args.results, not args.no_annotate,
                         max_atoms=args.max_atoms)
        print(f"Wrote {len(rows)} result row(s) to {out}")