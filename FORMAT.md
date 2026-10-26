# Proplog file formats

## 1. Proplog CSV (native format)

An extension of the CNF CSV format from the Brute-SAT project. A file holds any
number of wffs back to back; each starts with a `c` row. Cells may be separated by
commas or tabs, and trailing empty cells are ignored (so files saved from Excel work).

| Row | Meaning |
|---|---|
| `c,<problem#>,<max body length>,<S\|U\|?>` | header: problem number, longest rule/query body, label |
| `p,horn,<n atoms>,<m statements>` | atoms are numbered 1..n; m = number of `f` + `r` + `q` rows |
| `n,<atom#>,<name>` | optional: readable name for an atom (`n,0,<name>` names the puzzle) |
| `a,<±1>,<±2>,...,<±n>,0` | optional annotation: a satisfying assignment (+v true, -v false) |
| `f,<id>,0` | **fact** `id.` |
| `r,<id0>,<id1>,...,<idk>,0` | **rule** `id0 :- id1, ..., idk.` (head first) |
| `q,<id1>,...,<idk>,0` | **query** `?- id1, ..., idk.` |

Every statement row ends in `0`, as clause rows do in the CNF format. Example (the
picnic puzzle, `examples/picnic.pl`):

```
c,7,3,U
p,horn,8,9
n,0,picnic
n,1,car_has_gas
n,2,have_money
n,3,raining
n,4,have_umbrella
n,5,get_to_store
n,6,have_food
n,7,picnic
n,8,sun_shining
f,1,0
f,2,0
f,3,0
f,4,0
r,5,1,0
r,6,5,2,0
r,7,6,8,0
r,7,6,3,4,0
q,7,0
```

`r,7,6,3,4,0` reads "picnic :- have_food, raining, have_umbrella." and `q,7,0` is
"?- picnic.". The label is `U` because the query is provable.

### Label convention

The label describes the **wff** (all statements, queries included, read as clauses),
the same way the CNF files did:

* `S` the wff is satisfiable. The `a` row gives a model. In Prolog terms the
  query is **not** provable: "no".
* `U` the wff is unsatisfiable. The query is **provable** from the facts and
  rules: Prolog would answer "yes" (slide "Prolog Inferencing": if the wff is
  unsatisfiable then G must be true).
* `?` unknown (Brute-SAT could not finish).

### Statement to clause

| Statement | Clause | Literals |
|---|---|---|
| `a.` | `(a)` | one positive |
| `a :- b1, ..., bk.` | `(~b1 v ... v ~bk v a)` | one positive, k negative |
| `?- b1, ..., bk.` | `(~b1 v ... v ~bk)` | all negative |

## 2. Plain CNF CSV (accepted as input)

The solver also reads the earlier `p,cnf,...` files directly. Each clause is
classified by its number of positive literals (1 and alone = fact, 1 plus negatives =
rule, 0 = query). A clause with two or more positive literals is not Horn and is
rejected with an error, because Proplog cannot express it.

Every Proplog CSV written by the tools has a companion `*.pl.cnf.csv` in plain CNF form,
which is what Brute-SAT reads.

## 3. Proplog text (`.pl`)

Human-friendly syntax, one statement per `.`, `%` starts a comment:

```prolog
car_has_gas.                            % fact
have_food :- get_to_store, have_money.  % rule
?- picnic.                              % query  (the slides' "-?picnic." also works)
```

Identifiers start with a lowercase letter or `_`. Atoms are numbered in order of
first appearance. `make_examples.py` compiles every `examples/*.pl` into
`examples/puzzles.pl.csv` (problem numbers 1, 2, ... in file-name order).
