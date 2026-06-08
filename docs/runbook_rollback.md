# Runbook: rollback

Phase 10 deliverable. Covers the two surfaces that can trigger an
emergency rollback in production, the exact action for each, and the
"last-known-good" tuple Boussole guarantees you can return to.

## What "last-known-good" means

Every assessment is stamped with a `RunManifest`:

```
run_id, corpus_version, model_id, embedding_model,
prompt_set_version, rules_version, timestamp
```

The triple that uniquely identifies a behavior is
`(model_id, prompt_set_version, corpus_version)`. We pin a baseline at
`eval/baselines/<corpus_version>.json` whenever a re-index changes a chunk
and the gold eval still passes. That baseline IS the last-known-good
snapshot: rolling back means redeploying the image whose env vars point at
the same triple.

## Triggers that should cause a rollback

1. `boussole_grounding_violations_total` increments. This is a hard fail:
   the contract says every legal claim must be backed by a retrieved
   passage. One violation in production is a bug, not a metric to budget.
2. `boussole_assess_latency_seconds` p95 crosses the SLO (current
   target: 5 s). Watch for 3 consecutive scrape intervals at the SLO
   buckets before paging.
3. Eval regression: a corpus re-index produces a non-empty diff and the
   subsequent `eval/run_eval.py --gold --baseline ...` exits non-zero.
   Block the deploy at CI; do not promote to prod.
4. Drift: `/drift` shows the input-domain distribution has shifted more
   than 20% from the gold-set mix on a 500-request rolling window. This
   does not auto-rollback. It means the rules layer needs review.

## Rollback steps (immediate, paged)

1. Confirm the trigger via `/metrics` and `/drift` against the current
   pod. A single violation event already justifies the steps below.
2. Identify the last good image tag:
   `kubectl rollout history deployment/boussole-api -n boussole`
   then `kubectl rollout undo deployment/boussole-api -n boussole`.
3. Verify the rollback landed:
   ```
   curl -s https://api.boussole.<domain>/health
   curl -s https://api.boussole.<domain>/ready
   curl -s https://api.boussole.<domain>/metrics | grep boussole_assess_total
   ```
   The pod should respond `200` on `/ready` and the assess counter should
   start ticking after the next request.
4. Confirm the manifest is back at the known-good triple by replaying a
   canary assessment and reading the `manifest` block in the response.

## Rollback steps (corpus-only)

Corpus changes ride a different rail because the index lives in Postgres,
not in the image.

1. The CI eval gate has already prevented the new `corpus_version` from
   reaching prod if it regressed. If a regression slipped through:
2. Re-stamp the VERSION file to the previous good `corpus_version` and
   re-run the indexer with `--source local` so the previous snapshot is
   re-applied. The `CachingRetriever` invalidates on the version change.
3. Confirm by reading `regulations/ai_act/corpus/VERSION` and replaying a
   canary; the response manifest should carry the rolled-back version.

## Rollback steps (prompt-only)

Prompt changes are gated through `prompts/registry.yaml`. Each entry has
a version + sha pin. To roll back:

1. Revert the `prompts/*.j2` edit and restore the sha in
   `prompts/registry.yaml` to its prior value.
2. Re-deploy: the image build re-renders the registry, the new
   `prompt_set_version` is published, and the manifest reflects the
   rollback on the next assessment.

## Canary procedure for the next promotion

Before re-promoting after a rollback:

1. Apply the fix.
2. Run `make eval` against the new triple; it must exit 0.
3. Deploy to the canary slot.
4. Replay 20 gold cases against the canary endpoint. All 20 should pass
   tier + grounding.
5. Watch the canary `/metrics` for 15 minutes. Zero grounding violations,
   p95 below SLO, no error_count growth. Then promote.

## What is intentionally NOT automated

We do not auto-rollback on a single grounding violation in this version.
The reason: false-positive rollbacks look like flapping in the GitOps
audit log, and an attacker can game them. A human operator pages, looks at
the offending `run_id`, and decides. That decision is the value the
service charges for.
