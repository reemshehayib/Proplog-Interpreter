# Converts a .pl Proplog file to a .pl.csv file in the format specified by FORMAT.md

# A Proplog Program class
class PL:
    def __init__(self, atoms, facts, rules, queries):
        self.atoms = atoms      # Set of atoms {'picnic', 'have_food', ...}
        self.facts = facts      # List of facts ['car_has_gas']

        # List of rules, with each rule being a tuple
        # For example, ('picnic', ['have_food', 'sun_shining']) is equiv. to:
        # picnic :- have_food, sun_shining.
        self.rules = rules

        # List of queries, with each query being a list of the atoms being queried
        # For example ['picnic', 'sun_shining'] is equiv. to:
        # ?- picnic, sun_shining.
        self.queries = queries

    # Pretty-printing of PL class for debugging
    def __str__(self):
        return f"""
Atoms: {self.atoms}
Facts: {self.facts}
Rules: {self.rules}
Queries: {self.queries}
        """

# Takes the .pl file from path, converts it into a PL object, and returns the PL object
def pl_file_to_pl_object(path):
    pl = PL(set(), [], [], [])

    try:
        with open(path) as file:
            for line in file:
                line = line.strip()

                if len(line.split()) == 1 and line.endswith('.'):  # Fact
                    pl.facts.append(line[:-1])

                    pl.atoms.add(line[:-1])
                elif ':-' in line:  # Rule
                    lhs, rhs = line.split(':-', 1)
                    lhs = lhs.strip()
                    rhs = rhs[:rhs.find('.')]
                    rhs = rhs.strip().split(', ')

                    pl.rules.append((lhs, rhs))

                    pl.atoms.add(lhs)
                    for atom in rhs:
                        pl.atoms.add(atom)
                elif line.startswith('?-'):  # Query
                    query = line.removeprefix('?-')
                    query = query.strip()
                    query = query[:query.find('.')]
                    query = query.strip().split(',')

                    pl.queries.append(query)
    except FileNotFoundError:
        print("Input file not found")
        exit(1)

    return pl

# Takes a PL object and writes it to path in the format specified by FORMAT.md
def pl_object_to_pl_csv_file(pl, path):
    max_body_length = 0
    num_statements = len(pl.facts) + len(pl.rules) + len(pl.queries)
    atom_number_map = {atom: i for i, atom in enumerate(pl.atoms)}

    for rule in pl.rules:
        if len(rule[1]) > max_body_length:
            max_body_length = len(rule[1])

    for query in pl.queries:
        if len(query) > max_body_length:
            max_body_length = len(query)

    with open(path, 'a') as file:
        file.write(f'c,0,{max_body_length},?\n')
        file.write(f'p,horn,{len(pl.atoms)},{num_statements}\n')

        for atom, i, in atom_number_map.items():
            file.write(f'n,{i},{atom}\n')

        for fact in pl.facts:
            file.write(f'f,{atom_number_map[fact]},0\n')

        for rule in pl.rules:
            file.write(f'r,{atom_number_map[rule[0]]},{','.join([str(atom_number_map[atom]) for atom in rule[1]])},0\n')

        for query in pl.queries:
            file.write(f'q,{','.join([str(atom_number_map[atom]) for atom in query])},0\n')

if __name__ == '__main__':
    input_path = input("Enter the .pl file's path: ")
    output_path = input("Enter the desired output path/filename: ")

    pl = pl_file_to_pl_object(input_path)
    pl_object_to_pl_csv_file(pl, output_path)