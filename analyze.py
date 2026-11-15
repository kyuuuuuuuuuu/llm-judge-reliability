"""Summarise judge runs against MT-Bench expert votes (turn 1). Stdlib only.

Agreement follows MT-Bench (Zheng et al. 2023): vote-level, S1 counts ties as a third class,
S2 keeps only votes where neither side said tie. 95% CIs: bootstrap over the 80 questions.
"""
import collections as C, itertools as I, json, os, random, statistics as S, sys

B = os.path.dirname(os.path.abspath(__file__))
D, R = f'{B}/data', f'{B}/results'
rows = lambda p: [json.loads(l) for l in open(p)] if os.path.exists(p) else []
cat = {q['question_id']: q['category'] for q in rows(f'{D}/question.jsonl')}
QIDS = sorted(cat)
NB = 2000


def key(qid, a, b):
    m1, m2 = sorted((a, b))
    return f'{qid}|{m1}|{m2}'


def lab(r):  # human / gpt4 row -> model name or 'tie'
    w = r['winner']
    return r['model_a'] if w == 'model_a' else r['model_b'] if w == 'model_b' else 'tie'


human = [(key(r['question_id'], r['model_a'], r['model_b']), r['judge'], lab(r))
         for r in rows(f'{D}/human.jsonl') if r['turn'] == 1]
g4rows = [r for r in rows(f'{D}/gpt4_pair.jsonl') if r['turn'] == 1]
gpt4 = {key(r['question_id'], r['model_a'], r['model_b']): lab(r) for r in g4rows}
qof = lambda k: int(k.split('|')[0])


def boot(per_q, stat=lambda a, n: a / n if n else float('nan')):
    """per_q: {qid: (agree, n)} -> (point, lo, hi) with a question-level bootstrap."""
    a, n = sum(v[0] for v in per_q.values()), sum(v[1] for v in per_q.values())
    rnd, qs, out = random.Random(7), list(per_q), []
    for _ in range(NB):
        s = [per_q[rnd.choice(qs)] for _ in qs]
        out.append(stat(sum(x[0] for x in s), sum(x[1] for x in s)))
    out.sort()
    return stat(a, n), out[int(.025 * NB)], out[int(.975 * NB)], n


def fmt(t):
    p, lo, hi, n = t
    return f'{p * 100:.1f}% [{lo * 100:.1f}, {hi * 100:.1f}] (n={n})'


def agree_vs_human(judge, only=None):
    """judge: {key: label}. Returns S1, S2 tuples."""
    s1, s2 = C.defaultdict(lambda: [0, 0]), C.defaultdict(lambda: [0, 0])
    for k, _, h in human:
        j = judge.get(k)
        if j is None or (only and cat[qof(k)] not in only):
            continue
        s1[qof(k)][0] += j == h; s1[qof(k)][1] += 1
        if 'tie' not in (j, h):
            s2[qof(k)][0] += j == h; s2[qof(k)][1] += 1
    return boot({q: tuple(v) for q, v in s1.items()}), boot({q: tuple(v) for q, v in s2.items()})


def human_human():
    by = C.defaultdict(list)
    for k, j, h in human:
        by[k].append((j, h))
    s1, s2 = C.defaultdict(lambda: [0, 0]), C.defaultdict(lambda: [0, 0])
    for k, vs in by.items():
        for (j1, h1), (j2, h2) in I.combinations(vs, 2):
            if j1 == j2:
                continue
            s1[qof(k)][0] += h1 == h2; s1[qof(k)][1] += 1
            if 'tie' not in (h1, h2):
                s2[qof(k)][0] += h1 == h2; s2[qof(k)][1] += 1
    return boot({q: tuple(v) for q, v in s1.items()}), boot({q: tuple(v) for q, v in s2.items()})


def verdicts(recs, model, thinking, temp, order, run):
    out = {}
    for r in recs:
        if (r['model'], r['thinking'], r['temperature'], r['order'], r['run']) != (model, thinking, temp, order, run):
            continue
        v = r['verdict']
        first, second = (r['m1'], r['m2']) if order == 'AB' else (r['m2'], r['m1'])
        out[r['key']] = None if v is None else {'A': first, 'B': second, 'C': 'tie'}[v]
    return out


def letters(recs, model, thinking, temp, order, run):
    return {r['key']: r['verdict'] for r in recs
            if (r['model'], r['thinking'], r['temperature'], r['order'], r['run']) == (model, thinking, temp, order, run)}


def swap(ab, ba):
    return {k: (ab[k] if ab[k] == ba[k] else 'tie') for k in ab if k in ba and ab[k] and ba[k]}


def position(recs, model, thinking, temp):
    ab, ba = letters(recs, model, thinking, temp, 'AB', 'r1'), letters(recs, model, thinking, temp, 'BA', 'r1')
    mab, mba = verdicts(recs, model, thinking, temp, 'AB', 'r1'), verdicts(recs, model, thinking, temp, 'BA', 'r1')
    ks = [k for k in ab if k in ba and ab[k] and ba[k]]
    cons = sum(mab[k] == mba[k] for k in ks)
    inc = [k for k in ks if mab[k] != mba[k]]
    return dict(n=len(ks), consistent=cons / len(ks) if ks else None,
                first=sum(ab[k] == ba[k] == 'A' for k in inc) / len(ks) if ks else None,
                second=sum(ab[k] == ba[k] == 'B' for k in inc) / len(ks) if ks else None,
                tie_side=sum('C' in (ab[k], ba[k]) for k in inc) / len(ks) if ks else None)


def repeat_stats(vs):
    """vs: list of {key: verdict} for repeated runs of the same config."""
    ks = [k for k in vs[0] if all(v.get(k) for v in vs)]
    if not ks:
        return None
    same_all = sum(len({v[k] for v in vs}) == 1 for k in ks) / len(ks)
    pair = S.mean(sum(x[k] == y[k] for k in ks) / len(ks) for x, y in I.combinations(vs, 2))
    return dict(n=len(ks), runs=len(vs), all_same=same_all, pairwise_same=pair)


def main():
    P = rows(f'{R}/pair.jsonl') + rows(f'{R}/pair_pro.jsonl')
    SG = rows(f'{R}/single.jsonl')
    out, md = {}, []
    w = md.append
    w('# LLM judge vs MT-Bench expert votes (turn 1)\n')
    hh = human_human()
    w(f'- human votes: {len(human)} on {len({k for k, _, _ in human})} pairs; human-human S1 {fmt(hh[0])}, S2 {fmt(hh[1])}')
    g = agree_vs_human(gpt4)
    w(f'- GPT-4 (MT-Bench, swap, inconsistent->tie) vs human: S1 {fmt(g[0])}, S2 {fmt(g[1])}; '
      f'GPT-4 inconsistent rate {sum(r["winner"] == "tie (inconsistent)" for r in g4rows) / len(g4rows) * 100:.1f}%')
    out['human_human'], out['gpt4'] = hh, g

    configs = [('deepseek-flash', 'on', None), ('deepseek-flash', 'off', None), ('deepseek-v4-pro', 'on', None)]
    w('\n## Pairwise judges (r1)\n')
    w('| judge | order | S1 (with ties) | S2 (no ties) | position-consistent | first-pos wins | second-pos wins | one side tie |')
    w('|---|---|---|---|---|---|---|---|')
    for m, t, temp in configs:
        ab, ba = verdicts(P, m, t, temp, 'AB', 'r1'), verdicts(P, m, t, temp, 'BA', 'r1')
        if not ab:
            continue
        pos = position(P, m, t, temp) if ba else {}
        for name, j in [('AB only', ab), ('BA only', ba), ('swap (MT-Bench rule)', swap(ab, ba))]:
            if not j:
                continue
            a = agree_vs_human({k: v for k, v in j.items() if v})
            out[f'{m}|{t}|{name}'] = a
            extra = (f"| {pos['consistent'] * 100:.1f}% (n={pos['n']}) | {pos['first'] * 100:.1f}% | {pos['second'] * 100:.1f}% | {pos['tie_side'] * 100:.1f}% |"
                     if pos and name.startswith('swap') else '| | | | |')
            w(f'| {m} think-{t} | {name} | {fmt(a[0])} | {fmt(a[1])} {extra}')
        out[f'{m}|{t}|position'] = pos

    # same-subset comparison: every judge on the pairs the pro run covered in both orders
    pab, pba = verdicts(P, 'deepseek-v4-pro', 'on', None, 'AB', 'r1'), verdicts(P, 'deepseek-v4-pro', 'on', None, 'BA', 'r1')
    sub = {k for k in pab if k in pba and pab[k] and pba[k]}
    if sub:
        w(f'\n## Same {len(sub)} pairs, every judge (swap rule; position-consistent in brackets)\n')
        w('| judge | S1 | S2 | position-consistent |')
        w('|---|---|---|---|')
        for m, t in [('deepseek-flash', 'on'), ('deepseek-flash', 'off'), ('deepseek-v4-pro', 'on')]:
            ab, ba = verdicts(P, m, t, None, 'AB', 'r1'), verdicts(P, m, t, None, 'BA', 'r1')
            sw = {k: v for k, v in swap(ab, ba).items() if k in sub}
            if len(sw) < len(sub) * .95:
                continue
            a = agree_vs_human(sw)
            pc = sum(ab[k] == ba[k] for k in sw) / len(sw)
            out[f'subset|{m}|{t}'] = dict(s1=a[0], s2=a[1], position=pc)
            w(f'| {m} think-{t} | {fmt(a[0])} | {fmt(a[1])} | {pc * 100:.1f}% |')
        g = agree_vs_human({k: v for k, v in gpt4.items() if k in sub})
        w(f'| GPT-4 (MT-Bench) | {fmt(g[0])} | {fmt(g[1])} | |')

    # where do judge and humans disagree? split by whether the experts agreed among themselves
    ab, ba = verdicts(P, 'deepseek-flash', 'on', None, 'AB', 'r1'), verdicts(P, 'deepseek-flash', 'on', None, 'BA', 'r1')
    if ab and ba:
        by = C.defaultdict(set)
        for k, _, h in human:
            by[k].add(h)
        multi = C.Counter(k for k, _, _ in human)
        sw = swap(ab, ba)
        w('\n## Flash (swap) vs humans, by how much the experts agreed among themselves (pairs with 2+ votes)\n')
        for name, ks in [('experts unanimous', {k for k in by if multi[k] >= 2 and len(by[k]) == 1}),
                         ('experts split', {k for k in by if multi[k] >= 2 and len(by[k]) > 1})]:
            a, gg = agree_vs_human({k: v for k, v in sw.items() if k in ks}), agree_vs_human({k: v for k, v in gpt4.items() if k in ks})
            out[f'split|{name}'] = dict(flash=a, gpt4=gg, pairs=len(ks))
            w(f'- {name} ({len(ks)} pairs): flash S1 {fmt(a[0])}, S2 {fmt(a[1])}; GPT-4 S1 {fmt(gg[0])}, S2 {fmt(gg[1])}')

    w('\n## Same input, repeated (pairwise, AB order)\n')
    for label, m, t, temp, runs in [('flash think-on, default temperature', 'deepseek-flash', 'on', None, ['r1', 'r2']),
                                    ('flash think-off, temperature 0', 'deepseek-flash', 'off', 0.0, ['r1', 'r2'])]:
        st = repeat_stats([letters(P, m, t, temp, 'AB', r) for r in runs])
        out[f'repeat|{label}'] = st
        if st:
            w(f"- {label}: {st['runs']} runs x {st['n']} pairs; identical in all runs {st['all_same'] * 100:.1f}%, "
              f"any two runs agree {st['pairwise_same'] * 100:.1f}%")

    # per-category, flash think-on swap
    ab, ba = verdicts(P, 'deepseek-flash', 'on', None, 'AB', 'r1'), verdicts(P, 'deepseek-flash', 'on', None, 'BA', 'r1')
    if ab and ba:
        sw = swap(ab, ba)
        w('\n## By category (flash think-on, swap) vs GPT-4 vs human-human, S2\n')
        w('| category | flash S2 | GPT-4 S2 | position-consistent (flash) |')
        w('|---|---|---|---|')
        for c in sorted(set(cat.values())):
            a, gg = agree_vs_human(sw, {c}), agree_vs_human(gpt4, {c})
            ks = [k for k in ab if k in ba and ab[k] and ba[k] and cat[qof(k)] == c]
            pc = sum(ab[k] == ba[k] for k in ks) / len(ks)
            out[f'cat|{c}'] = dict(flash=a[1], gpt4=gg[1], position=pc)
            w(f'| {c} | {fmt(a[1])} | {fmt(gg[1])} | {pc * 100:.0f}% |')

    if SG:
        single(SG, out, w)
    tok = C.defaultdict(lambda: [0, 0, 0])
    for r in P + SG:
        t = tok[f"{r['task']}|{r['model']}|think-{r['thinking']}"]
        t[0] += 1; t[1] += r['usage']['prompt_tokens']; t[2] += r['usage']['completion_tokens']
    w('\n## Calls and tokens\n')
    for k, (n, pi, co) in sorted(tok.items()):
        w(f'- {k}: {n} calls, prompt {pi / 1e6:.2f}M, completion {co / 1e6:.2f}M tokens')
    w(f"- parse failures: {sum(r['verdict'] is None for r in P + SG)}")
    open(f'{R}/summary.md', 'w').write('\n'.join(md) + '\n')
    json.dump(out, open(f'{R}/summary.json', 'w'), indent=1, default=str)
    print('\n'.join(md))


def single(SG, out, w):
    sc = C.defaultdict(dict)  # (thinking,temp) -> {(qid,model): {run: score}}
    for r in SG:
        if r['verdict'] is not None:
            sc[(r['thinking'], r['temperature'])].setdefault((r['qid'], r['graded_model']), {})[r['run']] = r['verdict']
    w('\n## Single-answer grading (1-10)\n')
    for (t, temp), d in sorted(sc.items(), key=str):
        runs = sorted({r for v in d.values() for r in v})
        full = {k: v for k, v in d.items() if len(v) == len(runs)}
        if len(runs) < 2 or not full:
            continue
        rng = [max(v.values()) - min(v.values()) for v in full.values()]
        sds = [S.pstdev(v.values()) for v in full.values()]
        st = dict(n=len(full), runs=len(runs), identical=sum(x == 0 for x in rng) / len(rng),
                  range_ge2=sum(x >= 2 for x in rng) / len(rng), range_ge3=sum(x >= 3 for x in rng) / len(rng),
                  mean_sd=S.mean(sds),
                  mean_abs_r1r2=S.mean(abs(v[runs[0]] - v[runs[1]]) for v in full.values()))
        out[f'single|think-{t}|T{temp}'] = st
        w(f"- think-{t}, T={temp}: {st['runs']} runs x {st['n']} answers; identical {st['identical'] * 100:.1f}%, "
          f"range>=2 {st['range_ge2'] * 100:.1f}%, range>=3 {st['range_ge3'] * 100:.1f}%, mean per-answer SD {st['mean_sd']:.2f}, "
          f"mean |run1-run2| {st['mean_abs_r1r2']:.2f}")
        if t != 'on':
            continue
        models = sorted({m for _, m in full})
        avg = {k: S.mean(v.values()) for k, v in full.items()}
        w('\n| model | mean score (avg of runs) [95% CI over questions] | per-run means | human win rate |')
        w('|---|---|---|---|')
        hw = C.Counter(); hn = C.Counter()
        for k, _, h in human:
            _, m1, m2 = k.split('|')
            for m in (m1, m2):
                hn[m] += 1
                hw[m] += 1 if h == m else .5 if h == 'tie' else 0
        for m in sorted(models, key=lambda m: -S.mean(avg[(q, m)] for q in QIDS if (q, m) in avg)):
            per_q = {q: (avg[(q, m)], 1) for q in QIDS if (q, m) in avg}
            p = boot(per_q)
            pr = [S.mean(full[(q, m)][r] for q in QIDS if (q, m) in full) for r in runs]
            out[f'score|{m}'] = dict(mean=p, per_run=pr, human_win=hw[m] / hn[m])
            w(f"| {m} | {p[0]:.2f} [{p[1]:.2f}, {p[2]:.2f}] | {' / '.join(f'{x:.2f}' for x in pr)} | {hw[m] / hn[m] * 100:.0f}% |")
        drift = [max(v['per_run']) - min(v['per_run']) for k, v in out.items() if k.startswith('score|')]
        out['suite_drift'] = dict(max=max(drift), mean=S.mean(drift))
        w(f'\n- same 80 questions, judge re-run only: suite-mean spread across runs max {max(drift):.2f}, mean {S.mean(drift):.2f} points')
        w('\nPaired differences (A - B, per-question avg over runs; bootstrap 95% CI over questions):\n')
        w('| A | B | diff | 95% CI | single run (r1 only) 95% CI | humans prefer |')
        w('|---|---|---|---|---|---|')
        hp = C.defaultdict(lambda: [0, 0])
        for k, _, h in human:
            _, m1, m2 = k.split('|')
            if h != 'tie':
                hp[(m1, m2)][0 if h == m1 else 1] += 1
        for a_, b_ in I.combinations(sorted(models), 2):
            qs = [q for q in QIDS if (q, a_) in full and (q, b_) in full]
            d = {q: (avg[(q, a_)] - avg[(q, b_)], 1) for q in qs}
            d1 = {q: (full[(q, a_)][runs[0]] - full[(q, b_)][runs[0]], 1) for q in qs}
            p, p1 = boot(d), boot(d1)
            m1, m2 = sorted((a_, b_))
            h = hp[(m1, m2)]
            pref = f'{m1} {h[0]}:{h[1]}' if h[0] + h[1] else '-'
            out[f'diff|{a_}|{b_}'] = dict(all=p, r1=p1, human=h)
            w(f'| {a_} | {b_} | {p[0]:+.2f} | [{p[1]:+.2f}, {p[2]:+.2f}] | [{p1[1]:+.2f}, {p1[2]:+.2f}] | {pref} |')
        # pointwise scores used as a pairwise judge
        pj = {}
        for k, _, _ in human:
            q, m1, m2 = k.split('|'); q = int(q)
            if (q, m1) in avg and (q, m2) in avg:
                s1, s2 = avg[(q, m1)], avg[(q, m2)]
                pj[k] = m1 if s1 > s2 else m2 if s2 > s1 else 'tie'
        a = agree_vs_human(pj)
        out['single_as_pair'] = a
        w(f'\n- single scores used as a pairwise verdict vs human: S1 {fmt(a[0])}, S2 {fmt(a[1])}')
        bc = C.defaultdict(list)
        for (q, m), v in full.items():
            bc[cat[q]].append(S.pstdev(v.values()))
        w('- mean per-answer SD by category: ' + ', '.join(f'{c} {S.mean(x):.2f}' for c, x in sorted(bc.items())))


if __name__ == '__main__':
    main()
