# Model Evaluation Report

Sol artifact `art_01j9x7k9k5m2c8v6h3p4q2r1s0` · sol_version 0.1 · **source commit: `commit_042`**

## Cells

### cell_001 (sol:cell/prose)

*Task*

Introduces the checkpoint comparison task.

```
Compare checkpoints.
```

### cell_010 (sol:cell/config)

*Config*

Defines evaluation thresholds.

```
delta_tie = 0.02
```

### cell_011 (sol:cell/data)

*Dataset*

Binds the evaluation dataset.

```
eval_dataset = frozen_dataset_v1
```

### cell_014 (sol:cell/code)

*Compute Evaluation Metrics*

Computes loss, accuracy, and EOS rate for each checkpoint.

```
metrics = compute_metrics(results)
```

Output contract: metrics_table (application/x-parquet)

### cell_015 (sol:cell/display)

*Metrics Table*

Displays the current metrics table.

Output contract: eos_plot (image/png)

### cell_claim_anchor_007 (sol:cell/anchor)

Places claim_007 into the narrative.

> Anchor: places `record:claim_007` into the narrative.

## Semantic records

### claim_007 (sol:record/claim)

- **record_id**: claim_007
- **type**: sol:record/claim
- **summary**: M200 has lower EOS hazard than M0 on open-ended prompts.
- **status**: active / current / verified
- **statement**: Checkpoint M200 has lower EOS hazard than M0 on open-ended prompts.
- **claim_type**: empirical_result
- **supporting_evidence**: record:evidence_011
- **confidence**: 0.82

### decision_002 (sol:record/decision)

- **record_id**: decision_002
- **type**: sol:record/decision
- **summary**: Promote M200 for next-stage testing.
- **status**: active / current / unverified
- **decision_type**: branch_selection
- **candidates**: branch:main, branch:branch_007
- **selected**: branch:main
- **decision_rule**: lowest_invalidated_outputs_then_human_review
- **made_by**: human:alice
- **based_on**: record:claim_007, record:evidence_011

### evidence_011 (sol:record/evidence)

- **record_id**: evidence_011
- **type**: sol:record/evidence
- **summary**: Metrics table showing M200 has lower EOS rate.
- **status**: active / current / unverified
- **evidence_type**: metric_table
- **source_ref**: cell:cell_014#metrics_table
- **source_object**: object:sha256:d36e8fc345567dee67411d3c26a48bf2c03255ba84814d8219a051240866aa31
- **supports**: record:claim_007

### task_001 (sol:record/task)

- **record_id**: task_001
- **type**: sol:record/task
- **summary**: Compare checkpoints M0, M200, and M2000.
- **status**: active / current / unverified
- **task_type**: human_instruction
- **instruction_ref**: object:sha256:3e14be743a8190e87586cca696b176955d21074988888643a4f22b01c50a6810

### verification_005 (sol:record/verification)

- **record_id**: verification_005
- **type**: sol:record/verification
- **summary**: Reexecution verification of claim_007.
- **status**: active / current / unverified
- **target**: record:claim_007
- **method**: sol:verify/reexecution
- **result**: passed
- **performed_by**: tool:sol_executor

## Runs

### run_008 — success

- source_commit: `commit:commit_041` → result_commit: `commit:commit_042`
- actor: `tool:sol_executor` · environment: `env_001`
- cells_executed: cell:cell_001, cell:cell_010, cell:cell_011, cell:cell_014, cell:cell_015
- binding: `cell:cell_014#metrics_table` → `object:sha256:d36e8fc345567dee67411d3c26a48bf2c03255ba84814d8219a051240866aa31` (valid)
- binding: `cell:cell_015#eos_plot` → `object:sha256:c2e93ae90fa365e59bace5a370714589ef35a16f7a419c30037bff6cffc40bd2` (valid)

### run_012 — success

- source_commit: `commit:commit_042` → result_commit: `(none)`
- actor: `tool:sol_executor` · environment: `env_001`
- cells_executed: cell:cell_001, cell:cell_010, cell:cell_011, cell:cell_014
- binding: `cell:cell_014#metrics_table` → `object:sha256:d36e8fc345567dee67411d3c26a48bf2c03255ba84814d8219a051240866aa31` (valid)

---
Rendered view derived from commit `commit_042`. This view is a derived product (RFC section 47); the artifact is the source of truth (INV-01). Rendered without code execution (INV-07).