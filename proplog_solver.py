""" Proplog solver

Solves Proplog programs in the CSV format (FORMAT.md) by forward chaining,
in time linear in the size of the program.

Usage:

    python3 proplog_solver.py --problem data/generated.pl.csv
    python3 proplog_solver.py --problem examples/puzzles.pl.csv --verbose
    python3 proplog_solver.py --problem proplog_file.pl.csv --results results.csv

Without --results, the results go to results/proplog_<name>_results.csv, with
the same columns as Brute-SAT's results (run_brute.py) plus the assignment, so
the two can be joined on problem_id for the scatter chart:
  problem_id, n_vars, n_clauses, n_literals, label, status,
  satisfied_count, elapsed_sec, matched_label, assignment
'label' is the label in the file (from Brute-SAT), 'status' is this solver's
answer (S or U), matched_label is True/False (blank when the label is '?').
Only solving is timed, not reading the file. Each problem is solved
--repeat times (default 5) and the fastest time is kept, because single runs
of a task this short are noisy.

Answer convention (FORMAT.md, "Prolog Inferencing" slide): the wff is
UNSATISFIABLE (U) when some query can be proven from the facts and rules
(Prolog answers "yes"), and SATISFIABLE (S) otherwise; the assignment is then
the minimal model: proven atoms true, all others false.
"""

import argparse #for parsing arguments to solve a particular example
import csv
import dataclasses
import os
from collections import deque
from time import perf_counter

from proplog_to_CSV_CNF import read_pl_csv, to_clauses
from run_brute import RESULT_COLUMNS, results_path_for

@dataclasses.dataclass
class ProplogProblem:
    facts: set[int]
    rules: list[tuple[int, list[int]]]
    label: str                  # label in the file: 'S', 'U' or '?'
    names: dict[int,str]
    queries: list[list[int]]    # a program can have several queries
    number_of_atoms: int
    problem_number: int
    title: str = None
    clauses: list = None        # the statements as clauses, for the results row

def convert_problem_to_class(problem_file):
    '''Read every problem in a Proplog CSV file (parsing is shared with the
    other scripts, so all tools agree on the format).'''
    problems = []
    for wff in read_pl_csv(problem_file):
        problem = ProplogProblem(set(), [], wff['label'], wff['names'], [],
                                 wff['n_atoms'], wff['problem_id'], wff['title'],
                                 to_clauses(wff))
        for kind, head, body in wff['statements']:
            if kind == 'f':       #fact line
                problem.facts.add(head)
            elif kind == 'r':     #rule line
                problem.rules.append((head, body))
            else:                 #query line
                problem.queries.append(body)
        problems.append(problem)
    return problems

def solve_problem(problem: ProplogProblem):
    '''Solve the problem with forward propagation.

        General algorithm (each rule and each body atom is handled once, so the
        time is linear in the size of the program):
            missing[r] = how many body atoms of rule r are not proven yet
            start with the facts in a queue; for each newly proven atom,
            lower missing[r] for every rule r that uses it; when missing[r]
            reaches 0, the head of r is proven and joins the queue.
            Then a query is proven if all of its atoms are proven.

        Returns: ("Satisfiable" or "Unsatisfiable", set of proven atoms)
    '''
    uses = {}                                 # atom -> rules whose body has it
    missing = []
    for r, (conclusion, body) in enumerate(problem.rules):
        body = set(body)                      # a body may repeat an atom
        missing.append(len(body))
        for atom in body:
            uses.setdefault(atom, []).append(r)

    proven = set(problem.facts)
    queue = deque(proven)
    while queue:
        atom = queue.popleft()
        for r in uses.get(atom, ()):
            missing[r] -= 1
            if missing[r] == 0:
                conclusion = problem.rules[r][0]
                if conclusion not in proven:
                    proven.add(conclusion)
                    queue.append(conclusion)

    for query in problem.queries:
        if all(atom in proven for atom in query):
            return "Unsatisfiable", proven     # this query is provable
    return "Satisfiable", proven               # no query is provable (or none given)

def find_assignment(problem, result, proven):
    if result == "Satisfiable":
        return [variable if variable in proven else -variable for variable in range(1, problem.number_of_atoms + 1)]
    else:
        return None

def assignment_satisfies(problem, assignment):
    '''Check: every clause has a true literal under the assignment.'''
    true = set(lit for lit in assignment if lit > 0)
    return all(any((lit > 0) == (abs(lit) in true) for lit in clause)
               for clause in problem.clauses)

def main(problem_file: str, results_file: str = None, verbose: bool = False, repeat: int = 5):
    results_file = results_file or results_path_for(problem_file).replace('brute_', 'proplog_')
    os.makedirs(os.path.dirname(os.path.abspath(results_file)), exist_ok=True)

    start = perf_counter()
    problems = convert_problem_to_class(problem_file=problem_file)
    conversion_time = perf_counter() - start
    print(f"Read {len(problems)} problem(s) from {problem_file} in {conversion_time:.4f}s")

    rows = []
    for problem in problems:
        performance_time = None
        for _ in range(max(1, repeat)):                     # keep the fastest run
            start = perf_counter()
            result, proven = solve_problem(problem=problem) # only this is timed
            elapsed = perf_counter() - start
            if performance_time is None or elapsed < performance_time:
                performance_time = elapsed

        assignment = find_assignment(problem, result, proven)
        if assignment is not None and not assignment_satisfies(problem, assignment):
            raise AssertionError(f"problem {problem.problem_number}: assignment does not satisfy every clause")

        status = 'S' if result == "Satisfiable" else 'U'
        matched = '' if problem.label not in ('S', 'U') else (problem.label == status)
        rows.append({
            'problem_id': problem.problem_number,
            'n_vars': problem.number_of_atoms,
            'n_clauses': len(problem.clauses),
            'n_literals': sum(len(c) for c in problem.clauses),
            'label': problem.label, 'status': status,
            'satisfied_count': len(problem.clauses) if status == 'S' else '',
            'elapsed_sec': performance_time, 'matched_label': matched,
            'assignment': ' '.join(map(str, assignment)) if assignment else '',
        })
        if verbose or matched is False:
            name = f" ({problem.title})" if problem.title else ''
            flag = '  <-- DISAGREES WITH FILE LABEL' if matched is False else ''
            print(f"problem {problem.problem_number}{name}: n={problem.number_of_atoms} "
                  f"-> {result} in {performance_time:.6f}s{flag}")
            if verbose and assignment is not None:
                print(f"  Assignment: {' '.join(map(str, assignment))}")

    with open(results_file, "w", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS + ['assignment'])
        writer.writeheader()
        writer.writerows(rows)

    wrong = sum(1 for r in rows if r['matched_label'] is False)
    checked = sum(1 for r in rows if r['matched_label'] != '')
    print(f"Wrote {len(rows)} result row(s) to {results_file}; "
          f"{checked - wrong}/{checked} labeled problems match Brute-SAT")
    return rows


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Solve proplog program')
    parser.add_argument('--problem', metavar='path', required=True,
                        help='proplog file name')

    parser.add_argument('--results', metavar='path',
                        help='results file name (default results/proplog_<name>_results.csv)')

    parser.add_argument('--verbose', action='store_true',
                        help='print every problem and its assignment')

    parser.add_argument('--repeat', type=int, default=5,
                        help='solve each problem this many times, keep the fastest (default 5)')

    args = parser.parse_args()
    main(problem_file=args.problem, results_file=args.results, verbose=args.verbose,
         repeat=args.repeat)