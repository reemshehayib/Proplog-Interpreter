""" Proplog solver

Solves Proplog programs in the CSV format

Usage:

    python3 proplog_solver.py --problem proplog_file.pl.csv --results results.csv
    
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
    number_of_atoms: int
    problem_number: int

def convert_problem_to_class(problem_file):
    with open(problem_file, "r") as file:
        lines = file.readlines()
        problems = []
        for line in lines:
            line = line.strip()
            information_type = line[0]
            
            if line == "":
                continue
            
            if information_type == 'c':#comment line
                line = line.split(',')
                problem = ProplogProblem(set(), [], line[3] == 'S', dict(), [], -1, int(line[1]))
                problems.append(problem)
                continue
                
            problem = problems[-1] #latest problem
            if information_type == 'p': #number of atoms
                line = line.split(',')
                problem.number_of_atoms = int(line[2])
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
        
    return problems

def solve_problem(problem: ProplogProblem):
    '''Solve the problem with forward propogation

        General algorithm:
            Go through each rule and check the list
            
        Returns: "Satisfiable" or "Unsatisfiable"
    '''
    pass_number = 1
    while True:
        print(f"Pass: {pass_number}")
        truth_count = len(problem.facts)
        for rule in problem.rules:
            conclusion, body = rule
            add_conclusion = True
            for potential_fact in body:
                if potential_fact not in problem.facts:
                    add_conclusion = False
                    break
            if add_conclusion:
                problem.facts.add(conclusion)
        if truth_count == len(problem.facts):
            break
        pass_number+=1
    
    for potential_conclusion in problem.query:
        if potential_conclusion not in problem.facts:
            return "Satisfiable"
        
    return "Unsatisfiable"

def find_assignment(problem, result):
    if result == "Satisfiable":
        return [variable if variable in problem.facts else -variable for variable in range(1, problem.number_of_atoms + 1)]
    else:
        return None
    
def main(problem_file: str, results_file: str):
    
    with open(results_file, "+w") as file:
        file.write("problem_number,performance_time,result,assignment\n")
        
        print(f"Converting {problem_file} to data classes...")
        
        start = perf_counter()
        problems = convert_problem_to_class(problem_file=problem_file)
        end = perf_counter()
        conversion_time = end - start
        
        for problem in problems:
            print(problem)
            
            print(f"Converted in {conversion_time}")
            
            print(f"Solving {problem_file}...")
            
            start = perf_counter()
            
            result = solve_problem(problem=problem)
            assignment = find_assignment(problem, result)
            
            end = perf_counter()
            performance_time = end - start
            
            print(f"Solved in {performance_time}")
            print(f"Result: {result}")
            if assignment is not None:
                print(f"Assignment: {assignment}")
                file.write(f"{problem.problem_number},{performance_time},{result},{" ".join(map(str, assignment))}\n")
            else:
                file.write(f"{problem.problem_number},{performance_time},{result},{None}\n")
    
    
if __name__=='__main__':
    
    parser = argparse.ArgumentParser(description='Solve proplog program')
    parser.add_argument('--problem', metavar='path', required=True,
                        help='proplog file name')
    
    parser.add_argument('--results', metavar='path', required=True,
                            help='results file name')
    
    args = parser.parse_args()
    main(problem_file=args.problem, results_file=args.results)