# Converts a .pl Proplog file to a .pl.csv file in the format specified by FORMAT.md
#
#   python proplog_to_CSV.py examples/picnic.pl                 -> examples/picnic.pl.csv
#   python proplog_to_CSV.py examples/picnic.pl out.pl.csv --id 7
#   python proplog_to_CSV.py                                    (asks for the paths)
#
# Syntax (FORMAT.md section 3): statements end with '.', and may span lines;
# '%' starts a comment that runs to the end of the line.
#   car_has_gas.                            fact
#   have_food :- get_to_store, have_money.  rule
#   ?- picnic.        or   -?picnic.        query
# Atoms are numbered 1..n in order of first appearance (0 is the row terminator).
import os
import re
import sys

from pl_csv import write_pl_csv

IDENT = re.compile(r'[a-z_][A-Za-z0-9_]*$')


class ProplogSyntaxError(Exception):
    pass


# A Proplog Program class
class PL:
    def __init__(self, atoms, facts, rules, queries):
        # List of atoms in order of first appearance ['car_has_gas', 'have_money', ...]
        # (a list, not a set, so atom numbers are the same on every run)
        self.atoms = atoms
        self.facts = facts      # List of facts ['car_has_gas']

        # List of rules, with each rule being a tuple
        # For example, ('picnic', ['have_food', 'sun_shining']) is equiv. to:
        # picnic :- have_food, sun_shining.
        self.rules = rules

        # List of queries, with each query being a list of the atoms being queried
        # For example ['picnic', 'sun_shining'] is equiv. to:
        # ?- picnic, sun_shining.
        self.queries = queries

        # Every statement in file order: ('f', atom, []), ('r', head, body), ('q', None, body)
        self.statements = []

    def add_atom(self, atom):
        if atom not in self.atoms:
            self.atoms.append(atom)

    # Atom name -> number, 1..n in order of first appearance
    def atom_numbers(self):
        return {atom: i for i, atom in enumerate(self.atoms, 1)}

    # Pretty-printing of PL class for debugging
    def __str__(self):
        return f"""
Atoms: {self.atoms}
Facts: {self.facts}
Rules: {self.rules}
Queries: {self.queries}
        """


def _check_ident(name, line, path):
    if not IDENT.match(name):
        raise ProplogSyntaxError(
            f"{path}, line {line}: '{name}' is not a valid atom name "
            "(it must start with a lowercase letter or '_' and use only letters, digits, '_')")
    return name


def _split_atoms(text, line, path):
    atoms = [a.strip() for a in text.split(',')]
    if not atoms or any(a == '' for a in atoms):
        raise ProplogSyntaxError(f"{path}, line {line}: empty atom in '{text.strip()}'")
    return [_check_ident(a, line, path) for a in atoms]


# Parses Proplog text and returns a PL object
def pl_text_to_pl_object(text, path='<text>'):
    pl = PL([], [], [], [])

    # remove comments, keeping newlines so line numbers stay right
    text = re.sub(r'%[^\n]*', '', text)

    pos = 0
    for match in re.finditer(r'\.', text):
        stmt = text[pos:match.start()]
        line = text.count('\n', 0, pos + len(stmt) - len(stmt.lstrip())) + 1
        pos = match.end()
        stmt = ' '.join(stmt.split())          # join lines, collapse whitespace
        if not stmt:
            raise ProplogSyntaxError(f"{path}, line {line}: stray '.'")

        if stmt.startswith('?-') or stmt.startswith('-?'):      # Query
            query = _split_atoms(stmt[2:], line, path)
            for atom in query:
                pl.add_atom(atom)
            pl.queries.append(query)
            pl.statements.append(('q', None, query))
        elif ':-' in stmt:                                       # Rule
            lhs, rhs = stmt.split(':-', 1)
            head = _check_ident(lhs.strip(), line, path)
            body = _split_atoms(rhs, line, path)
            pl.add_atom(head)
            for atom in body:
                pl.add_atom(atom)
            pl.rules.append((head, body))
            pl.statements.append(('r', head, body))
        else:                                                    # Fact
            fact = _check_ident(stmt, line, path)
            pl.add_atom(fact)
            pl.facts.append(fact)
            pl.statements.append(('f', fact, []))

    leftover = text[pos:].strip()
    if leftover:
        line = text.count('\n', 0, pos + len(text[pos:]) - len(text[pos:].lstrip())) + 1
        raise ProplogSyntaxError(f"{path}, line {line}: statement '{leftover}' is missing its '.'")
    return pl


# Takes the .pl file from path, converts it into a PL object, and returns the PL object
def pl_file_to_pl_object(path):
    try:
        with open(path) as file:
            return pl_text_to_pl_object(file.read(), path)
    except FileNotFoundError:
        print("Input file not found")
        exit(1)


# Turns a PL object into the wff dict used by pl_csv.py
def pl_object_to_wff(pl, problem_id=1, title=None):
    num = pl.atom_numbers()
    statements = [(kind, num[head] if head else None, [num[a] for a in body])
                  for kind, head, body in pl.statements]
    return {'problem_id': problem_id, 'label': '?', 'n_atoms': len(pl.atoms),
            'title': title, 'names': {i: a for a, i in num.items()},
            'assignment': None, 'statements': statements}


# Takes a PL object and writes it to path in the format specified by FORMAT.md
# (overwrites the file, so running twice does not duplicate the wff)
def pl_object_to_pl_csv_file(pl, path, problem_id=1, title=None):
    write_pl_csv([pl_object_to_wff(pl, problem_id, title)], path)


def default_output_path(input_path):
    return input_path + '.csv'          # picnic.pl -> picnic.pl.csv


def title_for(path):
    return os.path.splitext(os.path.basename(path))[0]


if __name__ == '__main__':
    args = sys.argv[1:]
    problem_id = 1
    if '--id' in args:
        i = args.index('--id')
        problem_id = int(args[i + 1])
        del args[i:i + 2]

    if args:
        input_path = args[0]
        output_path = args[1] if len(args) > 1 else default_output_path(input_path)
    else:
        input_path = input("Enter the .pl file's path: ")
        output_path = input("Enter the desired output path/filename: ") \
            or default_output_path(input_path)

    try:
        pl = pl_file_to_pl_object(input_path)
    except ProplogSyntaxError as e:
        print(f"Syntax error: {e}")
        exit(1)
    pl_object_to_pl_csv_file(pl, output_path, problem_id, title_for(input_path))
    print(f"Wrote {output_path}: {len(pl.atoms)} atoms, {len(pl.statements)} statements")