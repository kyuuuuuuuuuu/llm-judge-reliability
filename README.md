# 模型当评委，靠得住吗？

**Is an LLM judge reliable?** Using MT-Bench's public expert votes (turn 1: 910 answer pairs, 1,689 votes), I measured DeepSeek V4.1 Flash and V4 Pro as LLM judges. Excluding ties, Flash agrees with the experts 85.4% of the time, on par with GPT-4 (85.9%) and above expert-to-expert agreement (82.0%); the disagreements sit where the experts disagree among themselves (96.5% on unanimous pairs, 65.3% on split ones). Swapping the two answers flips 7.4% of verdicts, mostly toward whichever answer is shown first, and temperature 0 does not make verdicts deterministic. On an 80-question suite, re-running the judge moves a model's mean score by at most 0.2 points, while the paired 95% CI between two models is about ±0.6: more questions narrow it, repeated judging barely does. About 8,600 API calls, under ¥40. Details below are in Chinese; all raw verdicts are in `results/`.

用 MT-Bench 公开的专家标注，量 DeepSeek 当评委的四件事：

1. 和专家评得一样吗；
2. 两个回答换个位置，判决会变吗；
3. 同一个输入跑两次，结果一样吗；
4. 分数差多少，才算真变化。

## 结论

| 谁和专家比 | 含平局 | 不含平局 |
|---|---|---|
| 专家和专家 | 64.1% | 82.0% |
| GPT-4（MT-Bench 官方判决） | 66.6% | 85.9% |
| DeepSeek V4.1 Flash，开思考，正反各一次 | 68.0% | 85.4% |
| DeepSeek V4.1 Flash，关思考，正反各一次 | 67.8% | 86.0% |
| DeepSeek V4 Pro，开思考，正反各一次（448 组） | 68.8% | 83.6% |

95% 区间都在 ±3 到 ±5 个点，这几个评委之间分不出高下。

- **分歧集中在专家自己也有分歧的题上。** 专家意见一致的 290 组，评委 96.5% 对得上；专家有分歧的 195 组，只有 65.3%。GPT-4 也是 95.9% 和 65.3%。
- **顺序会影响判决。** 两个回答换个位置，Flash 开思考有 92.6% 的判决不变，关思考 88.4%；变的时候多半偏向先出现的那个。正反各跑一次、不一致记平局，能去掉这个偏差。
- **温度 0 不等于结果固定。** 两两比较跑两次，94.4% 的判决一样；关思考、温度设 0，也只有 93.0%。单独打分（1–10 分），两次分数完全一样的占 69.0%，温度 0 时 72.9%；差 3 分以上的不到 1%。
- **"没给判决"要单独计数。** 开思考时，有些调用把 8,192 个 token 的上限全用在思考上，没给判决：Flash 0.7%，Pro 2.1%。重试一次也救不回全部。关思考的 3,380 次调用一次都没有。
- **分数差多少才算真变化。** 80 道题、同样的回答，重打一遍，平均分最多差 0.2 分；换一批题，平均分的 95% 区间是 ±0.5 到 ±0.7。两个模型在同一批题上做配对比较，区间约 ±0.6；三次打分取平均，区间只窄 3%。所以想看得更细，加题比重复打分有用。6 个模型两两比较共 15 组，14 组分得开、方向和专家全部一致；分不开的那组（Claude v1 对 GPT-3.5），专家投票也是 35 比 40。
- **贵的评委没有更准。** 同一批 448 组上，Pro 83.6%，Flash 84.3%，GPT-4 83.8%（不含平局）。按官网价格，Pro 每次判决的花费约是 Flash 的 4.6 倍。
- **开放式的题最难判。** 有参考答案的数学类 95.5%，写作类 74.4%（GPT-4 也只有 74.7%）。

完整表格见 [results/summary.md](results/summary.md)。

## 怎么做的

- **数据。** MT-Bench 的第一轮对话：80 道题（8 类，每类 10 道）× 6 个模型（GPT-4、GPT-3.5、Claude v1、Vicuna-13B、Alpaca-13B、LLaMA-13B）的回答；专家两两比较 1,689 票，覆盖 910 组配对，其中 485 组有两票以上。
- **评委提示词。** MT-Bench 原版，一字没改：两两比较用 `pair-v2`，单独打分用 `single-v1`；数学、推理、编程三类用带 GPT-4 参考答案的 `*-math-v1`。
- **一致率。** 照 MT-Bench 论文的口径按票算：含平局是三种结果都算，不含平局只看双方都没判平局的票。95% 区间按题目重抽样（bootstrap）。用这个口径重算 GPT-4 对专家、专家对专家，得到 66.6% / 85.9% 和 64.1% / 82.0%；论文 Table 5(a) 是 66% / 85% 和 63% / 81%。
- **正反各一次。** 也是 MT-Bench 的规则：两次判决不一致，记平局。

## 复现

```bash
# 1. 下载数据到 data/（能直连 huggingface.co 就去掉 HF_ENDPOINT）
HF_ENDPOINT=https://hf-mirror.com uv run --with pyarrow python fetch_data.py

# 2. 用 results/ 里的原始判决重算 summary.md，不需要 key
python3 analyze.py

# 3. 从头重跑：约 8,600 次调用、70 分钟、不到 40 元（2026-11 的价格）
export DEEPSEEK_API_KEY=sk-...
bash run_all.sh
```

`run_judge.py` 可以断点续跑：同一条命令再跑一次，只会重试没给判决的调用。key 如果和别的服务共用同一个账户，可以加 `--min-balance`（或者给 `run_all.sh` 设 `MIN_BALANCE`），余额低于这个数就不开跑。

**promptfoo 版。** 同样的检查，在 promptfoo 里跑一小批：15 组专家意见一致的配对 × 两种顺序 × 重复两次。

```bash
cd promptfoo && python3 make_tests.py
DEEPSEEK_API_KEY=sk-... npx promptfoo@0.125.1 eval -c promptfooconfig.yaml --repeat 2 --no-cache -j 2
```

我那次的结果：60 次里 49 次和专家一致；30 组正反对里，27 组换顺序后判决不变；`--repeat 2` 报告 30 条测试里有 5 条两次结果不一样。

## 文件

- `fetch_data.py`：下载数据。
- `run_judge.py`：调 DeepSeek 当评委。
- `run_all.sh`：生成 `results/` 的完整运行顺序。
- `analyze.py`：统计，只用 Python 标准库。
- `results/`：全部原始判决（含评委输出全文）、汇总表 `summary.md`、数字 `summary.json`。
- `promptfoo/`：promptfoo 版的配置和测试生成脚本。

## 局限

- 只用了第一轮对话。题目是英文通用问答；被评的是 2023 年的 6 个模型，强弱差距大，本来就容易分。
- 评委只试了 DeepSeek 的两个型号和 MT-Bench 原版提示词。Pro 只跑了一半配对；温度 0 的两两比较只跑了 300 组。
- 专家彼此之间的一致率也只有 64% 和 82%。专家标注是参照，不是标准答案。
- 用的是 2026 年 11 月的模型版本，版本一换，数字就会变。

## 许可与出处

- 代码：MIT。
- MT-Bench 专家评判数据：CC BY 4.0，来自 [lmsys/mt_bench_human_judgments](https://huggingface.co/datasets/lmsys/mt_bench_human_judgments)。题目、参考答案和评委提示词来自 [FastChat](https://github.com/lm-sys/FastChat)（Apache-2.0）。`results/` 里的评委输出引用了这些内容。
- 论文：Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, arXiv:2306.05685, 2023.
