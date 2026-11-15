"""Download the inputs into ./data.

- MT-Bench human judgments (CC BY 4.0): lmsys/mt_bench_human_judgments on Hugging Face, parquet -> jsonl
- questions, GPT-4 reference answers and judge prompts: FastChat's llm_judge data (Apache-2.0)

Needs pyarrow:  uv run --with pyarrow python fetch_data.py
If huggingface.co is slow or blocked:  HF_ENDPOINT=https://hf-mirror.com uv run --with pyarrow python fetch_data.py
"""
import json, os, urllib.request

import pyarrow.parquet as pq

HF = os.environ.get('HF_ENDPOINT', 'https://huggingface.co').rstrip('/')
DS = 'lmsys/mt_bench_human_judgments'
FC = 'https://raw.githubusercontent.com/lm-sys/FastChat/main/fastchat/llm_judge/data'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def get(url, path):
    with urllib.request.urlopen(url, timeout=120) as r, open(path, 'wb') as f:
        f.write(r.read())
    print('ok', os.path.basename(path))


os.makedirs(D, exist_ok=True)
files = [s['rfilename'] for s in json.load(urllib.request.urlopen(f'{HF}/api/datasets/{DS}', timeout=60))['siblings']]
for split in ('human', 'gpt4_pair'):
    name = next(f for f in files if f.startswith(f'data/{split}-') and f.endswith('.parquet'))
    pq_path = f'{D}/{split}.parquet'
    get(f'{HF}/datasets/{DS}/resolve/main/{name}', pq_path)
    with open(f'{D}/{split}.jsonl', 'w') as fh:
        for row in pq.read_table(pq_path).to_pylist():
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')
for src, dst in [('mt_bench/question.jsonl', 'question.jsonl'), ('judge_prompts.jsonl', 'judge_prompts.jsonl'),
                 ('mt_bench/reference_answer/gpt-4.jsonl', 'gpt-4.jsonl')]:
    get(f'{FC}/{src}', f'{D}/{dst}')
