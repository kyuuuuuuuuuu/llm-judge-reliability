#!/usr/bin/env bash
# The run sequence behind results/ (2026-11-15): ~8,600 calls, about 70 minutes at -j 6-8.
# Every step is resumable; running this script a second time only retries calls that returned no verdict.
set -euo pipefail
cd "$(dirname "$0")"
R=results/pair.jsonl; P=results/pair_pro.jsonl; S=results/single.jsonl; MB=${MIN_BALANCE:-0}

# pairwise, Flash with thinking: both answer orders, plus a second AB run for run-to-run agreement
for o in AB BA; do python3 run_judge.py --task pair --order $o --run r1 --out $R -j 8 --min-balance $MB; done
python3 run_judge.py --task pair --order AB --run r2 --out $R -j 8 --min-balance $MB
# single-answer grading, Flash with thinking, three runs
for r in r1 r2 r3; do python3 run_judge.py --task single --run $r --out $S -j 8 --min-balance $MB; done
# Flash without thinking: both orders; then temperature 0, twice (300 pairs, all 480 answers)
for o in AB BA; do python3 run_judge.py --task pair --thinking off --order $o --run r1 --out $R -j 8 --min-balance $MB; done
for r in r1 r2; do
  python3 run_judge.py --task pair --thinking off --temperature 0 --order AB --run $r --keys results/keys_t0.txt --out $R -j 8 --min-balance $MB
  python3 run_judge.py --task single --thinking off --temperature 0 --run $r --out $S -j 8 --min-balance $MB
done
# Pro, both orders, on half of the pairs (keys_half.txt = every other pair, all 80 questions)
for o in AB BA; do python3 run_judge.py --task pair --model deepseek-v4-pro --order $o --run r1 --keys results/keys_half.txt --out $P -j 6 --min-balance $MB; done

python3 analyze.py
