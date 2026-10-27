"""Draw the timing charts from the results CSVs.

    python plot_results.py

Reads every  results/proplog_<set>_results.csv  and, where it exists, the
matching  results/brute_<set>_results.csv  (joined on problem_id), and writes
three charts to  charts/ :

  scatter_brute_vs_proplog.png  one point per wff solved by both solvers:
                                x = Brute-SAT time, y = Proplog time,
                                colour/shape = satisfiable (S) or not (U)
  time_vs_n.png                 time vs number of atoms for both solvers
  proplog_time_vs_literals.png  Proplog time vs number of literals, with a
                                straight-line fit (linear time)

and prints a short summary (agreement, speedups, time per literal).
"""
import csv
import glob
import os
import statistics

import matplotlib
matplotlib.use('Agg')                       # write files, no window
import matplotlib.pyplot as plt

RESULTS_DIR = 'results'
CHARTS_DIR = 'charts'

# colours: validated categorical palette slots 1 and 2 (blue, orange);
# every series also has its own marker shape so colour is never the only cue
SURFACE, INK, INK_2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
BLUE, ORANGE = '#2a78d6', '#eb6834'
STYLE = {
    'S':       dict(color=BLUE,   marker='o', label='Satisfiable (S): query not provable'),
    'U':       dict(color=ORANGE, marker='^', label='Unsatisfiable (U): query provable'),
    'brute':   dict(color=ORANGE, marker='^', label='Brute-SAT'),
    'proplog': dict(color=BLUE,   marker='o', label='Proplog'),
}


# ---------------------------------------------------------------- loading

def read_rows(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['n_vars'] = int(r['n_vars'])
        r['n_literals'] = int(r['n_literals'])
        r['elapsed_sec'] = float(r['elapsed_sec']) if r['elapsed_sec'] else None
    return rows


def load():
    """{set name: {'proplog': rows, 'brute': rows or []}}"""
    sets = {}
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, 'proplog_*_results.csv'))):
        name = os.path.basename(path)[len('proplog_'):-len('_results.csv')]
        brute_path = os.path.join(RESULTS_DIR, f'brute_{name}_results.csv')
        sets[name] = {'proplog': read_rows(path),
                      'brute': read_rows(brute_path) if os.path.exists(brute_path) else []}
    return sets


def paired(sets):
    """Wffs solved by both solvers (Brute-SAT finished): one dict per wff."""
    pairs = []
    for name, d in sets.items():
        brute = {r['problem_id']: r for r in d['brute']}
        for p in d['proplog']:
            b = brute.get(p['problem_id'])
            if b and b['status'] in ('S', 'U') and b['elapsed_sec'] is not None:
                pairs.append({'set': name, 'id': p['problem_id'], 'n': p['n_vars'],
                              'brute': b['elapsed_sec'], 'proplog': p['elapsed_sec'],
                              'brute_status': b['status'], 'proplog_status': p['status']})
    return pairs


# ---------------------------------------------------------------- drawing

def new_axes(title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=13, loc='left', pad=12)
    ax.set_xlabel(xlabel, color=INK_2)
    ax.set_ylabel(ylabel, color=INK_2)
    ax.grid(True, which='major', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2)
    return fig, ax


def save(fig, name):
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = os.path.join(CHARTS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path}")


def scatter_chart(pairs):
    fig, ax = new_axes('Time per wff: Brute-SAT vs Proplog',
                       'Brute-SAT time (seconds, log scale)',
                       'Proplog time (seconds, log scale)')
    ax.set_xscale('log')
    ax.set_yscale('log')
    for label in ('S', 'U'):
        pts = [p for p in pairs if p['brute_status'] == label]
        st = STYLE[label]
        ax.scatter([p['brute'] for p in pts], [p['proplog'] for p in pts],
                   s=36, color=st['color'], marker=st['marker'], alpha=0.85,
                   edgecolors=SURFACE, linewidths=0.8,
                   label=f"{st['label']}  ({len(pts)})")
    lo = min(min(p['brute'] for p in pairs), min(p['proplog'] for p in pairs)) / 2
    hi = max(max(p['brute'] for p in pairs), max(p['proplog'] for p in pairs)) * 2
    ax.plot([lo, hi], [lo, hi], color=INK_2, linewidth=1, linestyle='--')
    ax.text(hi / 4, hi / 4 * 2.2, 'equal time', color=INK_2, fontsize=9,
            ha='right', va='bottom', rotation=45, rotation_mode='anchor')
    ax.text(hi / 1.2, lo * 1.5, 'below the line:\nProplog is faster', color=INK_2,
            fontsize=9, ha='right', va='bottom')
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.legend(loc='upper left', frameon=False, labelcolor=INK)
    save(fig, 'scatter_brute_vs_proplog.png')


def median_by_n(rows):
    by_n = {}
    for r in rows:
        if r['elapsed_sec'] is not None:
            by_n.setdefault(r['n_vars'], []).append(r['elapsed_sec'])
    ns = sorted(by_n)
    return ns, [statistics.median(by_n[n]) for n in ns]


def time_vs_n_chart(sets):
    fig, ax = new_axes('Solve time vs number of atoms',
                       'Number of atoms n (log scale)', 'Time (seconds, log scale)')
    ax.set_xscale('log')
    ax.set_yscale('log')
    for solver in ('brute', 'proplog'):
        rows = [r for d in sets.values() for r in d[solver]
                if r['elapsed_sec'] is not None and r['status'] in ('S', 'U')]
        st = STYLE[solver]
        ax.scatter([r['n_vars'] for r in rows], [r['elapsed_sec'] for r in rows],
                   s=12, color=st['color'], marker=st['marker'], alpha=0.25,
                   linewidths=0)
        ns, med = median_by_n(rows)
        ax.plot(ns, med, color=st['color'], linewidth=2, label=st['label'] + ' (median per n)')
        ax.annotate(st['label'], (ns[-1], med[-1]), xytext=(6, 0),
                    textcoords='offset points', color=INK, fontsize=10, va='center')
    ax.legend(loc='lower right', frameon=False, labelcolor=INK)
    save(fig, 'time_vs_n.png')


def literals_chart(sets):
    rows = [r for d in sets.values() for r in d['proplog'] if r['elapsed_sec'] is not None]
    xs = [r['n_literals'] for r in rows]
    ys = [r['elapsed_sec'] for r in rows]
    # least-squares fit through the origin: time = c * literals
    c = sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs)
    fig, ax = new_axes('Proplog solve time vs program size',
                       'Number of literals in the program', 'Time (seconds)')
    st = STYLE['proplog']
    ax.scatter(xs, ys, s=20, color=st['color'], marker=st['marker'], alpha=0.6,
               linewidths=0, label='one wff')
    top = max(xs)
    ax.plot([0, top], [0, c * top], color=INK_2, linewidth=1.5, linestyle='--',
            label=f'linear fit: {c * 1e6:.3f} µs per literal')
    ax.set_xlim(0, top * 1.03)
    ax.set_ylim(0, max(ys) * 1.1)
    ax.legend(loc='upper left', frameon=False, labelcolor=INK)
    save(fig, 'proplog_time_vs_literals.png')
    return c


# ---------------------------------------------------------------- main

def main():
    sets = load()
    if not sets:
        raise SystemExit(f"no results/proplog_*_results.csv files: run proplog_solver.py first")
    pairs = paired(sets)
    counts = ', '.join('%s (%d)' % (k, len(v['proplog'])) for k, v in sets.items())
    print(f"Sets: {counts}")

    agree = sum(p['brute_status'] == p['proplog_status'] for p in pairs)
    print(f"Wffs solved by both: {len(pairs)}; answers agree on {agree}")
    speedups = [p['brute'] / p['proplog'] for p in pairs if p['proplog'] > 0]
    big = [p for p in pairs if p['n'] >= 15]
    print(f"Median speedup of Proplog over Brute-SAT: {statistics.median(speedups):,.0f}x"
          + (f"  (n >= 15: {statistics.median(p['brute'] / p['proplog'] for p in big):,.0f}x)"
             if big else ''))

    print("Charts:")
    if pairs:
        scatter_chart(pairs)
    time_vs_n_chart(sets)
    c = literals_chart(sets)
    print(f"Proplog time per literal (fit): {c * 1e6:.3f} microseconds")


if __name__ == '__main__':
    main()