# Step 508 — Production is GREEN. And the dead id had a second, live victim.

**Date:** 2026-08-31 · **Instruction:** `build_log/508_chat_instruction.md`
**Tests 369 passed. Pushed `92b8d1a..b983b6e`, branch only, 0 tags on remote. Alerting NOT wired.**

---

# 1. THE FAIL-OPEN IS CONSIDERED — the code says so in its own words

`lease_gate.py`, the except block, verbatim:

```python
    except Exception as e:
        # Gate failure is non-fatal — log and proceed
        # Better to run and maybe produce imperfect results than to block valid leases
        elapsed = round(time.time() - start, 2)
        print(f"[lease_gate] Gate check failed (non-fatal): {e}", flush=True)
        return {
            "is_lease": True,  # Assume valid and proceed
```

**Deliberate, not an accident.** The comment states the trade explicitly and `# Assume valid and
proceed` names the choice.

**But the trade was priced for RARE failures, and the failure has been PERMANENT.** With the id
retired, the classifier has been a **no-op** for as long as that id has been dead — every document
passed. A non-lease upload would clear the gate and burn a full ~97-call pipeline producing a lease
analysis of something that is not a lease.

**The design is sound; the precondition was false.** That is a different finding from "the default is
wrong," and I am not recommending the default be changed.

# 2. A THIRD REFERENCE — live, user-facing, not previously recorded

Five steps recorded `lease_gate.py:49`. Nobody had grepped for the id itself. It appears in **three**
places:

| site | status | consequence |
|---|---|---|
| `lease_gate.py:49` | known since Step 491 | gate silently no-op |
| `model_config.py:68` | known since Step 491 | retired id labelled `"Claude Sonnet 4.6"` |
| **`lease_template_reader.py:35`** | **NOT previously recorded** | **`/api/template/summary` silently returns an empty dict** |

`read_template_summary` is live — `main.py:738` — and on failure returns
`{"landlord": "", "property": "", "base_rent": "", "lease_term": "", "governing_law": ""}`. **A second
silent failure on the same id, in a user-facing endpoint.** Fixed here rather than left as a
known-broken twin.

## Replacements, and why each

```
lease_gate.py            -> claude-haiku-4-5-20251001
lease_template_reader.py -> claude-sonnet-4-6
model_config.py:68       -> entry REMOVED
```

- **The gate takes haiku**, not role A's primary. It is role A's own-chain fallback, already in the
  pipeline, and the cheapest and fastest available — **exactly what the line's own comment asks for**
  (*"Use fastest/cheapest available model for gate check"*). A 10-token `LEASE`/`NOT_LEASE`
  classification does not need sonnet.
- **The template reader takes `claude-sonnet-4-6`**, role A's primary: it extracts five fields from
  12,000 characters with a 200-token budget, not a one-word classification.
- **The `DISPLAY_NAMES` entry is removed** rather than relabelled. It mapped a retired id to a current
  model's name — the same class as Step 497's `actual_model` naming a model that served nothing. A
  retired id should have no display name, because nothing should be displaying it.

**No live reference to the retired id remains** outside `cam/adapters/contractnli`, a different
adapter and out of scope.

# 3. VERIFIED BY CALL — both directions

```
POSITIVE (real fixtures)
   atlas             is_lease=True   abort=False   3.68s
   divall            is_lease=True   abort=False   0.68s

NEGATIVE (ad-hoc probe strings -- NOT fixtures)
   software licence  is_lease=False  abort=True    0.54s
   recipe            is_lease=False  abort=True    0.62s
```

**NO NON-LEASE FIXTURE EXISTS.** `test_data/tenants/` is all leases, `standard_template.txt` is a
lease template, the Beitel document is a lease. The two negatives are **probe strings written for this
step**, not fixtures, and are reported as such. **The negative case is tested; it is not tested against
a fixture, and no fixture was created.**

**The gate discriminates: leases pass, non-leases abort with the user-facing message.**

# 4. STARTUP ASSERTION, LOCAL — HEALTHY on all seven

`tools/check_models.py` TARGETS updated to follow the gate, then:

```
ALL 7 MODELS LISTED AND CALLABLE.

[startup_health] HEALTHY: 7 models OK | anthropic=0.125.0 google-genai=2.20.0 openai=2.8.1
status = 'healthy'   failures = []
```

# 5. DEPLOYED

```
92b8d1a..b983b6e  main -> main     unpushed: 0     tags on remote: 0
tracked files differing from HEAD: 0     tests: 369 passed
```

Six flags confirmed from HEAD, unchanged.

# 6. PRODUCTION IS GREEN

```
GET /api/provider-health (authenticated) -> HTTP 200

status='healthy'   failures=[]   elapsed=13.44s   checked=2026-08-31T03:11:27Z

anthropic  claude-sonnet-4-6           listed=True  callable=True  served=claude-sonnet-4-6
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True  served=claude-haiku-4-5-20251001
openai     gpt-5.5                     listed=True  callable=True  served=gpt-5.5
xai        grok-4.3                    listed=True  callable=True  served=grok-4.3
google     gemini-3.1-pro-preview      listed=True  callable=True  served=gemini-3.1-pro-preview
google     gemini-2.5-pro              listed=True  callable=True  served=gemini-2.5-pro
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True  served=claude-haiku-4-5-20251001

prod SDKs: anthropic=0.125.0  openai=2.54.0  google-genai=2.20.0
```

**Every target listed and callable in production.** The steady-state `unhealthy` flagged at Step 507
§C is cleared — `healthy` is now the baseline, so a future `unhealthy` is a real signal rather than
noise on top of a standing fault.

---

## ON ALERTING — the per-model set, and the last two hours are the argument

Keying on the summary would have said only *"red"* for the whole of Steps 507–508, while **six of
seven targets were fine**. The set says *which*. It also survives the case that actually matters: a
new failure arriving while an old one is unfixed, which a summary cannot distinguish at all.

## WHAT IS NOT ESTABLISHED

- **No non-lease FIXTURE exists.** The negative case rests on probe strings written for this step. A
  future change to the gate prompt or model has no regression test to fail.
- **`claude-haiku-4-5` has never classified a real non-lease upload in production.** Verified locally
  on four documents; production has processed none since the change.
- **`lease_template_reader` is fixed but UNEXERCISED.** `/api/template/summary` was not called on the
  new model, locally or deployed. It is a config change verified only by the id now resolving.
- **The production boot delay is still unmeasured** — Step 507 §C.3 carried the same gap.
- **Alerting is not wired.** Nothing reads `status` and tells anyone; the endpoint must be polled.
- **The gate's fail-open is unchanged.** If haiku is ever retired the same silence returns. The
  startup assertion would catch it at the next deploy — but not mid-life.
