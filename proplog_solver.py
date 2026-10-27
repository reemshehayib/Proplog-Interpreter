""" Proplog solver

Solves Proplog programs in the CSV format

Usage:

    python3 proplog_solver.py --program proplog_file.pl.csv
    
"""

import argparse #for parsing arguments to solve a particular example
import dataclasses
from time import perf_counter

@dataclasses.dataclass
class ProplogProblem:
    facts: set[int]
    rules: list[tuple[int, list[int]]]
    satisfiable: bool
    names: dict[int,str]
    query: list[int]

def convert_problem_to_class(problem_file):
    with open(problem_file, "r") as file:
        lines = file.readlines()
        
        problem = ProplogProblem(set(), [], False, dict(), [])
        print(problem)
        
        for line in lines:
            line = line.strip()
            information_type = line[0]
            
            if information_type == 'c':#comment line
                if line[-1] == 'S':
                    problem.satisfiable = True
                #remember already set to false by default
            elif information_type == 'p': #not totally sure what the point of this line was in the FORMAT.md
                pass
            elif information_type == 'n': #name line
                line = line.split(',')
                problem.names[int(line[1])] = line[2]
            elif information_type == 'f':#fact line
                line = line.split(',')
                problem.facts.add(int(line[1]))
            elif information_type == 'r': #rule line
                line = line.split(',')
                conclusion = int(line[1])
                body = [int(m) for m in line[2:-1]]
                problem.rules.append((conclusion, body))
            elif information_type == 'q': #query line
                line = line.split(',')
                query = [int(m) for m in line[1:-1]]
                problem.query = query
        
    return problem

def solve_problem(problem: ProplogProblem):
    '''Solve the problem with forward propogation

        General algorithm:
            Go through each rule and check the list
            
        Returns: True or False for Satisfiable and Unsatisfiable
    '''
    pass

def main(problem_file: str):
    print(f"Converting {problem_file} to data class...")
    
    start = perf_counter()
    problem = convert_problem_to_class(problem_file=problem_file)
    end = perf_counter()
    conversion_time = end - start
    
    print(problem)
    
    print(f"Converted in {conversion_time}")
    
    print(f"Solving {problem_file}...")
    
    start = perf_counter()
    
    result = solve_problem(problem=problem)
    
    end = perf_counter()
    performance_time = end - start
    
    print(f"Solved in {performance_time}")
    
    
if __name__=='__main__':
    
    parser = argparse.ArgumentParser(description='Solve proplog program')
    parser.add_argument('--problem', metavar='path', required=True,
                        help='proplog file name')
    
    args = parser.parse_args()
    main(problem_file=args.problem)