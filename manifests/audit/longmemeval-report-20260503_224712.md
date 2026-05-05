# LongMemEval Evaluation Report

- generated_at: 2026-05-03T22:48:11.893218+08:00
- dataset: data/longmemeval/longmemeval_s_cleaned.json
- granularity: session
- questions: 500

## Summary

| backend | Recall@5 | Recall@10 | NDCG@10 | threshold R@5 | threshold R@10 | threshold NDCG@10 | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| madongmei_overall | 1.0000 | 1.0000 | 1.0000 | 0.9950 | 0.9950 | 0.9300 | PASS |

## Reference

- source: MemPalace LongMemEval public claim
- mempalace_claim_recall_any@5: 0.966
- notes: Use same LongMemEval dataset and retrieval metric semantics for comparison.
