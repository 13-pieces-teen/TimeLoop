## Minimal Ablation: With vs Without Consistency

- Scenario set: S1_linear_explore, S3_knowledge_usage, S4_consistency_stress, S6_chinese
- Sample size: baseline n=24 turns; no_consistency n=24 turns


| Metric                                  | With Consistency | Without Consistency | Unit    |
| --------------------------------------- | ---------------- | ------------------- | ------- |
| Post-hoc violation rate (final attempt) | 0.00%            | 8.33%               | % turns |
| Turns with >=1 violation                | 0                | 2                   | turns   |
| Latency mean                            | 3578             | 3215                | ms      |
| Latency P50                             | 26               | 26                  | ms      |
| Latency P95                             | 9995             | 8088                | ms      |
| Intent accuracy                         | 0.00%            | 0.00%               | %       |
| Avg narration length                    | 264.4            | 259.8               | chars   |
| Dialogue presence rate                  | 87.50%           | 87.50%              | % turns |
| Fallback narration rate                 | 0.00%            | 0.00%               | % turns |
| Usable narration rate                   | 100.00%          | 100.00%             | % turns |


> `without consistency` means the pipeline does not enforce hard-rule retry,
> but violations are still measured post-hoc by a shadow checker on final attempt outputs.

