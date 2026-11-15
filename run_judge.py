"""Run DeepSeek as an LLM judge over MT-Bench turn-1 items.

pair   : the 910 (question, model pair) items that have expert votes; answers shown in order AB or BA
single : the 480 (model, question) answers, each graded 1-10
Prompts are MT-Bench's own (pair-v2 / single-v1; *-math-v1 with GPT-4's reference answer
for math, reasoning and coding), unchanged.

Needs DEEPSEEK_API_KEY. Resumable: ids already in --out with a parsed verdict are skipped,
so running the same command again only retries the calls that returned no verdict.
"""
import argparse, json, os, re, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
API = 'https://api.deepseek.com'
NEED_REF = {'math', 'reasoning', 'coding'}

KEY = os.environ.get('DEEPSEEK_API_KEY') or sys.exit('set DEEPSEEK_API_KEY')
# connect directly: on macOS urllib otherwise picks up the system proxy on its own
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def balance():
    req = urllib.request.Request(f'{API}/user/balance', headers={'Authorization': 'Bearer ' + KEY})
    d = json.loads(OPENER.open(req, timeout=20).read())
    return float(d['balance_infos'][0]['total_balance'])


def load_items(task):
    prompts = {json.loads(l)['name']: json.loads(l) for l in open(f'{D}/judge_prompts.jsonl')}
    cat = {q['question_id']: q['category'] for q in map(json.loads, open(f'{D}/question.jsonl'))}
    ref = {r['question_id']: r['choices'][0]['turns'][0] for r in map(json.loads, open(f'{D}/gpt-4.jsonl'))}
    human = [json.loads(l) for l in open(f'{D}/human.jsonl')]
    answers, question = {}, {}
    for r in human:
        for s in 'ab':
            answers[(r['model_' + s], r['question_id'])] = r['conversation_' + s][1]['content']
        question[r['question_id']] = r['conversation_a'][0]['content']
    items = []
    if task == 'pair':
        pairs = sorted({(r['question_id'],) + tuple(sorted((r['model_a'], r['model_b']))) for r in human if r['turn'] == 1})
        for qid, m1, m2 in pairs:
            math = cat[qid] in NEED_REF
            items.append(dict(key=f'{qid}|{m1}|{m2}', qid=qid, cat=cat[qid], m1=m1, m2=m2,
                              prompt=prompts['pair-math-v1' if math else 'pair-v2'],
                              fmt=dict(question=question[qid], ref_answer_1=ref.get(qid, ''),
                                       a1=answers[(m1, qid)], a2=answers[(m2, qid)])))
    else:
        for (m, qid), a in sorted(answers.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            math = cat[qid] in NEED_REF
            items.append(dict(key=f'{qid}|{m}', qid=qid, cat=cat[qid], model=m,
                              prompt=prompts['single-math-v1' if math else 'single-v1'],
                              fmt=dict(question=question[qid], ref_answer_1=ref.get(qid, ''), answer=a)))
    return items


def parse(task, text):
    if task == 'pair':
        hits = re.findall(r'\[\[([ABC])\]\]', text)
        return hits[-1] if hits else None
    hits = re.findall(r'\[\[(\d+\.?\d*)\]\]', text) or re.findall(r'\[(\d+\.?\d*)\]', text)
    return float(hits[-1]) if hits else None


class Abort(Exception):
    pass


def call(body):
    req = urllib.request.Request(f'{API}/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    for attempt in range(6):
        try:
            return json.loads(OPENER.open(req, timeout=300).read())
        except urllib.error.HTTPError as e:
            if e.code == 402:
                raise Abort('402 insufficient balance')
            if e.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 5:
                raise
        time.sleep(2 ** attempt + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', choices=['pair', 'single'], required=True)
    ap.add_argument('--model', default='deepseek-flash')
    ap.add_argument('--thinking', choices=['on', 'off'], default='on')
    ap.add_argument('--temperature', type=float)  # omitted = API default
    ap.add_argument('--order', choices=['AB', 'BA'], default='AB')
    ap.add_argument('--run', default='r1')
    ap.add_argument('--keys', help='file with item keys to restrict to')
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-balance', type=float, default=0.0,
                    help='refuse to start below this account balance (CNY), e.g. when the key is shared')
    ap.add_argument('-j', type=int, default=6)
    a = ap.parse_args()

    items = load_items(a.task)
    if a.keys:
        keep = set(open(a.keys).read().split())
        items = [i for i in items if i['key'] in keep]
    tag = f'{a.model}|think-{a.thinking}|T{a.temperature}|{a.order if a.task == "pair" else "-"}|{a.run}'
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            r = json.loads(l)
            if r['verdict'] is not None:
                done.add(r['id'])
    todo = [i for i in items if f"{i['key']}|{tag}" not in done]
    start = balance()
    print(f'{tag}: {len(items)} items, {len(todo)} to run, balance {start:.2f}', flush=True)
    if start < a.min_balance:
        sys.exit(f'balance {start:.2f} below --min-balance {a.min_balance}')

    lock, stop, n = threading.Lock(), threading.Event(), [0]
    fh = open(a.out, 'a')

    def work(it):
        if stop.is_set():
            return
        f = dict(it['fmt'])
        if a.task == 'pair':
            first, second = ('a1', 'a2') if a.order == 'AB' else ('a2', 'a1')
            f['answer_a'], f['answer_b'] = f.pop(first), f.pop(second)
        p = it['prompt']
        body = {'model': a.model, 'max_tokens': 8192,
                'messages': [{'role': 'system', 'content': p['system_prompt']},
                             {'role': 'user', 'content': p['prompt_template'].format(**f)}]}
        if a.thinking == 'off':
            body['thinking'] = {'type': 'disabled'}
        if a.temperature is not None:
            body['temperature'] = a.temperature
        t = time.time()
        try:
            d = call(body)
        except Abort as e:
            stop.set()
            print('ABORT', e, flush=True)
            return
        except Exception as e:
            print('FAIL', it['key'], repr(e)[:200], flush=True)
            return
        msg = d['choices'][0]['message']
        rec = dict(id=f"{it['key']}|{tag}", key=it['key'], task=a.task, model=a.model, thinking=a.thinking,
                   temperature=a.temperature, order=a.order if a.task == 'pair' else None, run=a.run,
                   qid=it['qid'], cat=it['cat'], m1=it.get('m1'), m2=it.get('m2'), graded_model=it.get('model'),
                   verdict=parse(a.task, msg['content']), content=msg['content'],
                   reasoning_chars=len(msg.get('reasoning_content') or ''), usage=d['usage'],
                   latency=round(time.time() - t, 2))
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            fh.flush()
            n[0] += 1
            if n[0] % 100 == 0:
                print(f'{n[0]}/{len(todo)}', flush=True)

    with ThreadPoolExecutor(a.j) as ex:
        list(ex.map(work, todo))
    end = balance()
    print(f'done {n[0]}/{len(todo)}; balance {start:.2f} -> {end:.2f} (spent {start - end:.2f})', flush=True)


if __name__ == '__main__':
    main()
