"""Proplog CSV <-> CNF CSV, plus the shared code every script uses to read and
write the Proplog CSV format (FORMAT.md).

Run it to convert a Proplog CSV file to a plain CNF CSV file for Brute-SAT:

    python proplog_to_CSV_CNF.py examples/picnic.pl.csv
        -> examples/picnic.pl.cnf.csv

    python proplog_to_CSV_CNF.py in.pl.csv out.cnf.csv

Each statement becomes one clause:
    fact  a.                  ->  a,0
    rule  a :- b1, ..., bk.   ->  -b1,...,-bk,a,0
    query ?- b1, ..., bk.     ->  -b1,...,-bk,0
Problem numbers, atom numbers and labels are kept as they are.

The other scripts import its functions (read_pl_csv, write_pl_csv, to_clauses,
write_cnf_csv, cnf_path_for) so there is only one copy of the format code.

A wff is a dict:
    problem_id  int
    max_body    int             longest rule body or query
    label       'S' | 'U' | '?'
    n_atoms     int             atoms are numbered 1..n_atoms
    title       str | None      from the optional  n,0,<name>  row
    names       {atom: name}    from optional  n,<atom>,<name>  rows
    assignment  {atom: bool} | None   from the optional  a  row
    statements  list of (kind, head, body) in file order
                  ('f', id, [])          fact   id.
                  ('r', id0, [id1..k])   rule   id0 :- id1, ..., idk.
                  ('q', None, [id1..k])  query  ?- id1, ..., idk.
"""
import csv
import os


# ---------------------------------------------------------------- reading

def _read_rows(path):
    """Rows of the file with empty cells and empty rows removed.
    Commas or tabs are accepted, as in the Brute-SAT parser."""
    with open(path, newline='') as f:
        text = f.read()
    delim = '\t' if text.count('\t') > text.count(',') else ','
    rows = []
    for row in csv.reader(text.splitlines(), delimiter=delim):
        row = [cell.strip() for cell in row if cell.strip() != '']
        if row:
            rows.append(row)
    return rows


def _ints(cells, where):
    try:
        return [int(x) for x in cells]
    except ValueError:
        raise ValueError(f"{where}: expected integers, got {cells}")


def read_pl_csv(path):
    """Return the list of wffs in a Proplog CSV file."""
    rows = _read_rows(path)
    wffs = []
    i = 0
    while i < len(rows):
        row = rows[i]
        where = f"{path}, data row {i + 1}"
        if row[0] != 'c':
            raise ValueError(f"{where}: expected a 'c' row, got {row}")
        wff = {
            'problem_id': int(row[1]),
            'max_body': int(row[2]) if len(row) > 2 else 0,
            'label': row[3] if len(row) > 3 else '?',
            'title': None, 'names': {}, 'assignment': None, 'statements': [],
        }
        i += 1
        prow = rows[i] if i < len(rows) else []
        if len(prow) < 4 or prow[0] != 'p' or prow[1] != 'horn':
            raise ValueError(f"{path}, data row {i + 1}: expected 'p,horn,<n>,<m>', got {prow}")
        n, m = int(prow[2]), int(prow[3])
        wff['n_atoms'] = n
        i += 1

        while i < len(rows) and rows[i][0] != 'c':
            row = rows[i]
            where = f"{path}, data row {i + 1}"
            kind = row[0]
            if kind == 'n':
                atom = int(row[1])
                name = ','.join(row[2:])
                if atom == 0:
                    wff['title'] = name
                else:
                    wff['names'][atom] = name
            elif kind == 'a':
                lits = _ints(row[1:], where)
                if lits and lits[-1] == 0:
                    lits = lits[:-1]
                wff['assignment'] = {abs(l): l > 0 for l in lits}
            elif kind in ('f', 'r', 'q'):
                ids = _ints(row[1:], where)
                if not ids or ids[-1] != 0:
                    raise ValueError(f"{where}: statement must end in 0: {row}")
                ids = ids[:-1]
                if 0 in ids or any(a < 1 or a > n for a in ids):
                    raise ValueError(f"{where}: atom numbers must be 1..{n}: {row}")
                if kind == 'f':
                    if len(ids) != 1:
                        raise ValueError(f"{where}: a fact has exactly one atom: {row}")
                    wff['statements'].append(('f', ids[0], []))
                elif kind == 'r':
                    if len(ids) < 2:
                        raise ValueError(f"{where}: a rule needs a head and a body: {row}")
                    wff['statements'].append(('r', ids[0], ids[1:]))
                else:
                    if len(ids) < 1:
                        raise ValueError(f"{where}: empty query: {row}")
                    wff['statements'].append(('q', None, ids))
            else:
                raise ValueError(f"{where}: unknown row type '{kind}'")
            i += 1

        if len(wff['statements']) != m:
            raise ValueError(f"{path}: problem {wff['problem_id']} says {m} statements "
                             f"but has {len(wff['statements'])}")
        wffs.append(wff)
    return wffs


# ---------------------------------------------------------------- clauses

def statement_to_clause(kind, head, body):
    """fact (a); rule (~b1 v ... v ~bk v a); query (~b1 v ... v ~bk)."""
    if kind == 'f':
        return [head]
    if kind == 'r':
        return [-b for b in body] + [head]
    return [-b for b in body]


def to_clauses(wff):
    return [statement_to_clause(*s) for s in wff['statements']]


def max_body(statements):
    return max((len(body) for _, _, body in statements), default=0)


# ---------------------------------------------------------------- writing

def _wff_pl_rows(wff):
    st = wff['statements']
    rows = [['c', wff['problem_id'], max_body(st), wff.get('label') or '?'],
            ['p', 'horn', wff['n_atoms'], len(st)]]
    if wff.get('title'):
        rows.append(['n', 0, wff['title']])
    for atom in sorted(wff.get('names') or {}):
        rows.append(['n', atom, wff['names'][atom]])
    if wff.get('assignment') and wff.get('label') == 'S':
        a = wff['assignment']
        rows.append(['a'] + [v if a.get(v, False) else -v
                             for v in range(1, wff['n_atoms'] + 1)] + [0])
    for kind, head, body in st:
        if kind == 'f':
            rows.append(['f', head, 0])
        elif kind == 'r':
            rows.append(['r', head] + list(body) + [0])
        else:
            rows.append(['q'] + list(body) + [0])
    return rows


def _wff_cnf_rows(wff):
    clauses = to_clauses(wff)
    rows = [['c', wff['problem_id'], max((len(c) for c in clauses), default=0),
             wff.get('label') or '?'],
            ['p', 'cnf', wff['n_atoms'], len(clauses)]]
    rows += [c + [0] for c in clauses]
    return rows


def _write(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', newline='') as f:     # 'w': re-running never duplicates
        csv.writer(f, lineterminator='\n').writerows(rows)


def write_pl_csv(wffs, path):
    _write(path, [r for w in wffs for r in _wff_pl_rows(w)])


def write_cnf_csv(wffs, path):
    """Plain CNF CSV, readable by the Brute-SAT parser.
    Rows are padded with empty cells to one width, like the Excel-exported CNF
    files, because the Brute-SAT parser's csv.Sniffer cannot detect the
    delimiter when rows have different lengths. Empty cells are ignored."""
    rows = [r for w in wffs for r in _wff_cnf_rows(w)]
    width = max((len(r) for r in rows), default=0)
    _write(path, [r + [''] * (width - len(r)) for r in rows])


def cnf_path_for(pl_csv_path):
    """example.pl.csv -> example.pl.cnf.csv"""
    if pl_csv_path.endswith('.csv'):
        return pl_csv_path[:-4] + '.cnf.csv'
    return pl_csv_path + '.cnf.csv'


# ---------------------------------------------------------------- command line

def convert(pl_csv_path, cnf_csv_path=None):
    cnf_csv_path = cnf_csv_path or cnf_path_for(pl_csv_path)
    wffs = read_pl_csv(pl_csv_path)
    write_cnf_csv(wffs, cnf_csv_path)
    return cnf_csv_path, len(wffs)


if __name__ == '__main__':
    import sys
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    out, count = convert(*sys.argv[1:])
    print(f"Wrote {count} wff(s) to {out}")