"""Build the small promptfoo demo: 15 pairs on which every expert who voted agreed,
each written as two tests (answer order AB and BA), MT-Bench pair-v2 judge prompt unchanged.
Writes tests.yaml and prompt.json next to this file; reads ../data (run ../fetch_data.py first).
"""
import collections as C, json, os, random

H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, '..', 'data')
P = {json.loads(l)['name']: json.loads(l) for l in open(f'{D}/judge_prompts.jsonl')}
cat = {q['question_id']: q['category'] for q in map(json.loads, open(f'{D}/question.jsonl'))}
votes, conv = C.defaultdict(list), {}
for r in map(json.loads, open(f'{D}/human.jsonl')):
    if r['turn'] != 1:
        continue
    m1, m2 = sorted((r['model_a'], r['model_b']))
    w = r['model_a'] if r['winner'] == 'model_a' else r['model_b'] if r['winner'] == 'model_b' else 'tie'
    votes[(r['question_id'], m1, m2)].append(w)
    conv[(r['model_a'], r['question_id'])] = r['conversation_a']
    conv[(r['model_b'], r['question_id'])] = r['conversation_b']

# unanimous pairs with 2+ votes, outside the categories that need a reference answer
cand = sorted(k for k, v in votes.items() if len(v) >= 2 and len(set(v)) == 1
              and cat[k[0]] not in ('math', 'reasoning', 'coding'))
p = P['pair-v2']
tests = []
for q, m1, m2 in sorted(random.Random(5).sample(cand, 15)):
    h = votes[(q, m1, m2)][0]
    for order, (fa, fb) in (('AB', (m1, m2)), ('BA', (m2, m1))):
        tests.append({'description': f'q{q} {fa} vs {fb} ({order})',
                      'vars': {'user_msg': p['prompt_template'].format(question=conv[(m1, q)][0]['content'],
                                                                       answer_a=conv[(fa, q)][1]['content'],
                                                                       answer_b=conv[(fb, q)][1]['content']),
                               'pair': f'{q}|{m1}|{m2}', 'order': order, 'first': fa,
                               'expected': 'A' if h == fa else 'B' if h == fb else 'C'},
                      'metadata': {'category': cat[q], 'experts': h}})
json.dump(tests, open(f'{H}/tests.yaml', 'w'), ensure_ascii=False, indent=1)  # JSON is valid YAML
prompt = json.dumps([{'role': 'system', 'content': p['system_prompt']}, {'role': 'user', 'content': '__USER__'}],
                    ensure_ascii=False, indent=1)
open(f'{H}/prompt.json', 'w').write(prompt.replace('"__USER__"', '{{ user_msg | dump }}'))
print(len(tests), 'tests written')
