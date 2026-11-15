# LLM judge vs MT-Bench expert votes (turn 1)

- human votes: 1689 on 910 pairs; human-human S1 64.1% [59.2, 68.8] (n=1198), S2 82.0% [77.2, 86.8] (n=772)
- GPT-4 (MT-Bench, swap, inconsistent->tie) vs human: S1 66.6% [62.8, 70.1] (n=1689), S2 85.9% [82.6, 88.9] (n=1060); GPT-4 inconsistent rate 15.7%

## Pairwise judges (r1)

| judge | order | S1 (with ties) | S2 (no ties) | position-consistent | first-pos wins | second-pos wins | one side tie |
|---|---|---|---|---|---|---|---|
| deepseek-flash think-on | AB only | 67.6% [64.4, 70.8] (n=1687) | 84.1% [81.1, 86.9] (n=1253) | | | | |
| deepseek-flash think-on | BA only | 67.5% [64.1, 70.7] (n=1687) | 83.1% [79.5, 86.3] (n=1259) | | | | |
| deepseek-flash think-on | swap (MT-Bench rule) | 68.0% [64.5, 71.5] (n=1685) | 85.4% [82.4, 88.2] (n=1190) | 92.6% (n=907) | 4.1% | 0.7% | 2.6% |
| deepseek-flash think-off | AB only | 68.0% [65.1, 71.0] (n=1689) | 83.2% [79.9, 86.3] (n=1248) | | | | |
| deepseek-flash think-off | BA only | 67.3% [63.9, 70.4] (n=1689) | 83.4% [79.7, 86.9] (n=1237) | | | | |
| deepseek-flash think-off | swap (MT-Bench rule) | 67.8% [64.0, 71.3] (n=1689) | 86.0% [83.0, 88.7] (n=1143) | 88.4% (n=910) | 5.6% | 1.8% | 4.3% |
| deepseek-v4-pro think-on | AB only | 68.4% [64.1, 72.6] (n=934) | 81.2% [76.9, 85.4] (n=691) | | | | |
| deepseek-v4-pro think-on | BA only | 69.0% [64.7, 73.4] (n=852) | 81.5% [76.7, 85.9] (n=626) | | | | |
| deepseek-v4-pro think-on | swap (MT-Bench rule) | 68.8% [64.2, 73.5] (n=850) | 83.6% [79.4, 87.8] (n=586) | 91.7% (n=448) | 4.0% | 0.9% | 3.3% |

## Same 448 pairs, every judge (swap rule; position-consistent in brackets)

| judge | S1 | S2 | position-consistent |
|---|---|---|---|
| deepseek-flash think-on | 68.8% [63.9, 73.8] (n=850) | 84.3% [80.1, 88.2] (n=604) | 92.0% |
| deepseek-flash think-off | 67.6% [62.1, 72.8] (n=850) | 85.7% [81.8, 89.5] (n=575) | 88.6% |
| deepseek-v4-pro think-on | 68.8% [64.2, 73.5] (n=850) | 83.6% [79.4, 87.8] (n=586) | 91.7% |
| GPT-4 (MT-Bench) | 66.7% [61.8, 71.8] (n=850) | 83.8% [79.2, 88.0] (n=555) | |

## Judge-expert against expert-expert, same pairs (2+ experts; S2; paired bootstrap over questions)

| judge | pairs | judge-expert | expert-expert | difference [95% CI] |
|---|---|---|---|---|
| deepseek-flash think-on | 483 | 85.4% (n=890) | 82.0% (n=771) | +3.4 [+0.4, +6.5] |
| deepseek-flash think-off | 484 | 86.5% (n=865) | 82.0% (n=772) | +4.5 [+0.5, +8.1] |
| deepseek-v4-pro think-on | 245 | 84.2% (n=444) | 81.8% (n=423) | +2.4 [-2.4, +7.1] |
| GPT-4 (MT-Bench) | 484 | 86.0% (n=798) | 82.0% (n=772) | +4.0 [+0.6, +7.1] |

Positive = the judge sides with the expert majority more often than one expert sides with another; it does not mean the judge beats the experts.

## Flash (swap) vs humans, by how much the experts agreed among themselves (pairs with 2+ votes)

- experts unanimous (290 pairs): flash S1 86.7% [81.7, 91.2] (n=705), S2 96.5% [93.5, 98.9] (n=573); GPT-4 S1 83.7% [77.2, 89.4] (n=707), S2 95.9% [92.9, 98.4] (n=539)
- experts split (195 pairs): flash S1 43.6% [40.1, 47.1] (n=557), S2 65.3% [60.7, 70.3] (n=317); GPT-4 S1 45.1% [41.6, 48.4] (n=557), S2 65.3% [59.7, 71.0] (n=259)

## Same input, repeated (pairwise, AB order)

- flash think-on, default temperature: 2 runs x 909 pairs; identical in all runs 94.4%, any two runs agree 94.4%
- flash think-off, temperature 0: 2 runs x 300 pairs; identical in all runs 93.0%, any two runs agree 93.0%

## By category (flash think-on, swap) vs GPT-4 vs human-human, S2

| category | flash S2 | GPT-4 S2 | position-consistent (flash) |
|---|---|---|---|
| coding | 84.8% [78.3, 90.9] (n=138) | 87.4% [82.1, 93.1] (n=103) | 96% |
| extraction | 91.0% [81.3, 98.0] (n=144) | 90.9% [83.5, 96.9] (n=132) | 93% |
| humanities | 81.1% [73.6, 87.6] (n=175) | 87.0% [80.0, 92.6] (n=154) | 98% |
| math | 95.5% [91.9, 98.5] (n=133) | 96.9% [91.2, 100.0] (n=97) | 90% |
| reasoning | 88.2% [83.2, 93.1] (n=102) | 91.0% [85.5, 95.5] (n=89) | 88% |
| roleplay | 86.3% [80.3, 91.7] (n=197) | 82.2% [76.2, 87.1] (n=180) | 96% |
| stem | 83.1% [76.1, 91.4] (n=172) | 84.9% [77.8, 93.5] (n=159) | 94% |
| writing | 74.4% [62.1, 85.3] (n=129) | 74.7% [62.1, 86.5] (n=146) | 85% |

## Single-answer grading (1-10)

- think-off, T=0.0: 2 runs x 480 answers; identical 72.9%, range>=2 2.7%, range>=3 0.6%, mean per-answer SD 0.15, mean |run1-run2| 0.30
- think-on, T=None: 3 runs x 480 answers; identical 52.5%, range>=2 4.6%, range>=3 0.8%, mean per-answer SD 0.25, mean |run1-run2| 0.36

| model | mean score (avg of runs) [95% CI over questions] | per-run means | human win rate |
|---|---|---|---|
| gpt-4 | 7.64 [7.12, 8.16] | 7.71 / 7.60 / 7.61 | 74% |
| claude-v1 | 6.57 [5.99, 7.18] | 6.51 / 6.56 / 6.62 | 62% |
| gpt-3.5-turbo | 6.52 [5.95, 7.09] | 6.55 / 6.41 / 6.60 | 63% |
| vicuna-13b-v1.2 | 5.00 [4.32, 5.66] | 5.03 / 4.96 / 5.00 | 52% |
| alpaca-13b | 3.58 [3.04, 4.16] | 3.69 / 3.49 / 3.58 | 28% |
| llama-13b | 2.55 [2.08, 3.03] | 2.55 / 2.52 / 2.56 | 17% |

- same 80 questions, judge re-run only: suite-mean spread across runs max 0.20, mean 0.12 points

Paired differences (A - B, per-question avg over runs; bootstrap 95% CI over questions):

| A | B | diff | 95% CI | single run (r1 only) 95% CI | humans prefer |
|---|---|---|---|---|---|
| alpaca-13b | claude-v1 | -2.98 | [-3.67, -2.25] | [-3.58, -2.02] | alpaca-13b 5:61 |
| alpaca-13b | gpt-3.5-turbo | -2.94 | [-3.62, -2.26] | [-3.56, -2.14] | alpaca-13b 15:109 |
| alpaca-13b | gpt-4 | -4.06 | [-4.77, -3.38] | [-4.75, -3.29] | alpaca-13b 9:68 |
| alpaca-13b | llama-13b | +1.04 | [+0.44, +1.66] | [+0.51, +1.79] | alpaca-13b 36:17 |
| alpaca-13b | vicuna-13b-v1.2 | -1.41 | [-2.00, -0.81] | [-1.95, -0.72] | alpaca-13b 24:54 |
| claude-v1 | gpt-3.5-turbo | +0.05 | [-0.54, +0.65] | [-0.65, +0.60] | claude-v1 35:40 |
| claude-v1 | gpt-4 | -1.07 | [-1.67, -0.48] | [-1.82, -0.59] | claude-v1 24:46 |
| claude-v1 | llama-13b | +4.02 | [+3.34, +4.67] | [+3.26, +4.65] | claude-v1 90:9 |
| claude-v1 | vicuna-13b-v1.2 | +1.57 | [+0.99, +2.17] | [+0.86, +2.11] | claude-v1 36:21 |
| gpt-3.5-turbo | gpt-4 | -1.12 | [-1.70, -0.61] | [-1.74, -0.64] | gpt-3.5-turbo 31:67 |
| gpt-3.5-turbo | llama-13b | +3.98 | [+3.34, +4.64] | [+3.36, +4.66] | gpt-3.5-turbo 111:8 |
| gpt-3.5-turbo | vicuna-13b-v1.2 | +1.52 | [+0.87, +2.20] | [+0.85, +2.23] | gpt-3.5-turbo 68:44 |
| gpt-4 | llama-13b | +5.10 | [+4.45, +5.74] | [+4.53, +5.80] | gpt-4 90:6 |
| gpt-4 | vicuna-13b-v1.2 | +2.65 | [+2.01, +3.30] | [+2.05, +3.34] | gpt-4 55:11 |
| llama-13b | vicuna-13b-v1.2 | -2.45 | [-3.10, -1.84] | [-3.14, -1.86] | llama-13b 10:84 |

- single scores used as a pairwise verdict vs human: S1 66.7% [63.1, 70.3] (n=1689), S2 83.1% [79.7, 86.1] (n=1210)
- mean per-answer SD by category: coding 0.25, extraction 0.21, humanities 0.33, math 0.10, reasoning 0.21, roleplay 0.31, stem 0.29, writing 0.33

## Calls and tokens

- pair|deepseek-flash|think-off: 2420 calls, prompt 1.81M, completion 0.67M tokens
- pair|deepseek-flash|think-on: 2748 calls, prompt 2.14M, completion 2.52M tokens
- pair|deepseek-v4-pro|think-on: 980 calls, prompt 0.81M, completion 1.25M tokens
- single|deepseek-flash|think-off: 960 calls, prompt 0.46M, completion 0.19M tokens
- single|deepseek-flash|think-on: 1441 calls, prompt 0.72M, completion 1.05M tokens
- parse failures: 52
