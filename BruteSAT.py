"""Brute-SAT, from https://github.com/reemshehayib/Brute-Force-SAT-Solver
(parser.py + brute_sat_solver.py, unchanged). 

Used to label Proplog wffs.

Note: the timeout uses SIGALRM, so it works on Linux/macOS but not Windows.
"""
import csv
import signal
import time


# ---------------------------------------------------------------- parser.py

def parse_cnf_csv(filename):
    with open(filename, newline='') as f:
        sample = f.read(2048)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=',\t')
        rows = list(csv.reader(f, dialect))

    # strip trailing empty-string cells from each row
    rows = [[cell for cell in row if cell != ''] for row in rows]
    # drop fully-empty rows if any slipped through
    rows = [row for row in rows if row]

    wffs = []
    i = 0
    while i < len(rows):
        row = rows[i]
        assert row[0] == 'c', f"Expected 'c' row at line {i}, got {row}"
        problem_id = int(row[1])
        max_lits = int(row[2])
        label = row[3] if len(row) > 3 else None
        i += 1

        prow = rows[i]
        assert prow[0] == 'p' and prow[1] == 'cnf'
        n_vars = int(prow[2])
        n_clauses = int(prow[3])
        i += 1

        clauses = []
        for _ in range(n_clauses):
            crow = rows[i]
            lits = [int(x) for x in crow]
            assert lits[-1] == 0, f"Clause did not end in 0: {crow}"
            clauses.append(lits[:-1])   # drop the trailing 0
            i += 1

        wffs.append({
            'problem_id': problem_id,
            'max_lits': max_lits,
            'label': label,
            'n_vars': n_vars,
            'n_clauses': n_clauses,
            'clauses': clauses,
        })

    return wffs


# ---------------------------------------------------------------- brute_sat_solver.py

def clause_satisfied(clause, assignment):
    for lit in clause:
        var = abs(lit)
        val = assignment[var]
        if (lit > 0 and val) or (lit < 0 and not val):
            return True
    return False


def count_satisfied(clauses, assignment):
    return sum(1 for c in clauses if clause_satisfied(c, assignment))


def brute_sat(n_vars, clauses):
    total = len(clauses)
    best_count = -1
    best_assignment = None
    start = time.perf_counter()
    for i in range(2 ** n_vars):
        assignment = {v: bool((i >> (v - 1)) & 1) for v in range(1, n_vars + 1)}
        count = count_satisfied(clauses, assignment)
        if count == total:
            return ('SAT', assignment, count, time.perf_counter() - start)
        if count > best_count:
            best_count = count
            best_assignment = assignment
    return ('UNSAT', best_assignment, best_count, time.perf_counter() - start)


class TimeoutError(Exception):
    pass


def _handler(signum, frame):
    raise TimeoutError()


def brute_sat_with_timeout(n_vars, clauses, timeout_sec=60):
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_sec)
    try:
        result = brute_sat(n_vars, clauses)
        signal.alarm(0)
        return result
    except TimeoutError:
        return ('TIMEOUT', None, None, timeout_sec)