# BTL Measure

BTL Measure independently checks model-evaluation records and compares a baseline with a candidate. Its job is to make a capability or regression claim auditable. It recomputes metrics from per-item records and requires matching taskset identity and revision.

It does not run models, create tasks, assign rewards, choose training algorithms or publish checkpoints. It consumes evaluation output from BTL Fieldwork/Verifiers, BTL Advance, BTL Adapt or another declared evaluator. A valid file proves record structure and arithmetic; it does not prove that the evaluator or task verifier is trustworthy.

## Input contract

```json
{
  "model_id": "Tinfield-1-8B",
  "model_revision": "<full checkpoint SHA or immutable revision>",
  "taskset_id": "coding-v1",
  "taskset_revision": "<taskset commit or manifest SHA>",
  "records": [
    {"id": "case-001", "source_id": "repo-001", "passed": true},
    {"id": "case-002", "source_id": "repo-002", "score": 0.5}
  ]
}
```

Each record needs a unique ID and either a score/reward in `[0, 1]` or a boolean `passed`. The checker recomputes mean score and pass rate. It rejects duplicate IDs, missing identity, nonfinite/out-of-range scores and empty records.

## Commands

```sh
python -m pip install 'btl-measure @ git+https://github.com/Badtheorylabs/btl-measure.git@main'
btl-measure validate evaluation.json
btl-measure compare baseline.json candidate.json
```

The comparison is paired. It rejects taskset or revision mismatches, missing cases, and identical model revisions. It reports per-item deltas, mean change, relative change, regressions and improvements. A threshold is a declared gate, not a statistical significance test. The CLI returns nonzero when the evaluation is malformed or incomparable.

The root `./btl measure` command adds these checks to the Lab ledger and stores hashes of the source files and report. Its integration is intentionally separate from model execution. It cannot turn training reward or a self-reported aggregate into a release claim.

Version 0.2 rejects contradictory score/reward/pass fields and changed source identities under the same item ID. Regression IDs include partial-credit score decreases. Equal mean scores do not meet an improvement threshold. A full pass remains score 1.0.

Through BTL Lab, `btl measure from-run RUN_ID` consumes a completed Advance record, verifies its artifacts and recomputes its synthetic action rewards before comparing them. This checks recorded verifier arithmetic; it does not execute a second independent model evaluation. Managed Advance runs perform this handoff automatically.

BTL-owned code in this repository is released under the MIT License. Evaluators, tasksets and model artifacts retain their own licenses.
