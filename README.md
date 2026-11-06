# XERJ and BM25 + Seb: small comparison experiments

This repository records exploratory comparisons of [XERJ Query-1](https://xerj.org/blog/xerj-query-ai-model), XERJ full-text search, SQLite BM25 and [Seb](https://seblabs.dev/). The experiments answer different questions and use different interfaces. **Do not treat the rows below as a single matched benchmark or a general product ranking.**

## What was tested

| Experiment | XERJ | BM25 + Seb | Important limitations |
| --- | --- | --- | --- |
| [Raw-text passage retrieval](bible-raw-retrieval/README.md) | XERJ full-text ranked the dataset’s designated verse first for 25/160 questions; Query-1 returned UNKNOWN on 160/160 when given documents but no extracted facts. | SQLite BM25 top-5 plus five Seb relevance judgments ranked the designated verse first for 42/160; BM25 alone: 25/160. | Passage retrieval, not answer accuracy. One designated passage per question; other passages can answer. Query-1 with extracted facts was **not** evaluated. |
| [Knowledge graph lookups](bible-content-qa/README.md) | Query-1 matched 157/160 graph answers, with two differing answers and one decline. | BM25 + Seb matched 160/160 graph answers. | Inputs were 839 graph-derived facts, not raw Bible text. XERJ answered openly; Seb received four candidates and retrieved facts. Results are agreement with the graph, not independently verified truth. |
| [Chapter-length comparisons](bible-xerj-seb/README.md) | Query-1 returned 141 correct and declined 19 of 160. | BM25 + Seb returned 154 correct and six wrong. | 80 chapter pairs asked both ways, using precomputed verse counts. The adapter and phrasing were adjusted during development; this is not a sealed evaluation. |
| [Initial synthetic smoke test](xerj-seb-spike/README.md) | 13/14 correct, one unsupported. | 14/14 correct. | A tiny repetitive synthetic test; not suitable for general claims. |

The raw-text test is the most relevant run for **passage search**. Its metric cannot establish which system writes better answers. Seb reranking is a separate stage after BM25, not BM25 top-1 alone. XERJ’s full-text search and Query-1 are distinct features. XERJ’s released autoindex indexed the Bible but did not create a Query-1 facts namespace; the cost and quality of extracting facts from narrative text were not measured.

## Costs and timing

In the raw-text run, Seb made 800 metered judgments (five per question), costing $0.002485392 for 160 questions, or **$0.0155337 per 1,000 questions** at the observed usage. That excludes search infrastructure. Local single-run median retrieval times were 0.643 ms for SQLite and 0.382 ms for XERJ full-text over different client paths; Seb’s median **per-passage API call** was 60.6 ms, not end-to-end latency for five passages. See the individual reports for indexing measurements, pricing assumptions, and earlier runs.

CPU-equivalent projections in the historical reports apply a cloud CPU price to work measured on an Apple Mac. They are not measured cloud bills, do not include idle hosting or storage, and should not be compared as total cost of ownership. The graphics are snapshots of individual experiments and must not be combined.

## Files and reproduction

Each experiment directory contains its script, methodology, summary, and where rights allow, recorded result rows. Python 3 and SQLite FTS5 are required; a live rerun additionally requires the relevant XERJ release and Seb access. The source-specific READMEs contain commands and describe the paid inference steps. Set `BENCH_DATA_DIR` to the folder containing the pinned input files, or use the root `data/` folder. Derived SQLite databases and local input data are ignored by Git.

**BibleQA source text and question-bearing raw responses are intentionally not redistributed here:** the upstream repository does not declare a license. Download the pinned files from the source link and verify the hashes given in [the raw-text report](bible-raw-retrieval/README.md). Its recorded aggregate summary and scripts are included, but `verify.py` requires regenerating the omitted question and response files. The other experiments include their recorded result rows for inspection.

## Sources and attribution

- KJV text: [midvash/bible-data](https://github.com/midvash/bible-data), pinned commit and SHA-256 in the reports; the source identifies the KJV text as public domain.
- Questions and labeled passages: [BibleQA](https://github.com/helen-jiahe-zhao/BibleQA), pinned commit and SHA-256 in the raw-text report; no explicit upstream repository license was found.
- Graph-derived experiment: [Gnosis v0.9.3](https://github.com/spearssoftware/gnosis/releases/tag/v0.9.3), CC BY-SA 4.0. Its `SOURCES.md` lists upstream attribution. Graph-derived question/fact text in `bible-content-qa/` is distributed under that source license; no broader license for third-party sources is implied.
- XERJ release, model and documentation: [xerj-org/xerj](https://github.com/xerj-org/xerj); see the vendor for its software and model terms.

The comparisons are independent experiments, not an official evaluation by XERJ or Seb Labs.
