# Step 438 (labeled "Step 435-read") — READ-ONLY: does grok-4.3 have any temperature-drift path? → **CLEAN**

**Status:** READ-ONLY investigation complete. **VERDICT: CLEAN.** grok-4.3 (xAI, Role C) can ONLY
ever transmit `temperature = target.temperature = 0.0` by every path traced. No default
substitution, no override, no mutation, no alternate branch, no applicable SDK default. The Role-C
integrity requirement **DISSOLVES**: the guarded (conditional-omission) condition is structurally
absent AND no non-omission drift path exists. ZERO edits, ZERO calls, ZERO `cam/` changes.

---

## The full temperature path for a grok-4.3 call, quoted

### Harness → ModelTarget (`build_log/run_431_selection_measurement.py`, `_provider_call`)
```
753    target = ModelTarget(
...
758        temperature=evaluator_cfg.get("temperature", 0.0),
...
760    )
761    router = ProviderRouter([target], RouterConfig())
762    adapter = router._get_adapter(provider)
767    raw = adapter.call("", payload, target) or ""
```
`evaluator_cfg` for Role C is `EVALUATOR_LINEUP_305["C"]`, whose `"temperature": 0.0`
(`cam/adapters/lease_review/lease_coverage_305.py`). So `target.temperature = 0.0`; even the
`.get(...)` fallback is `0.0`; and `ModelTarget`'s own dataclass default is `temperature: float = 0.0`
(`provider_router.py:161`). The target is passed to `adapter.call` unchanged (`:767`).

### 1. XAIAdapter.call — how temperature enters the payload (`provider_router.py`)
```
753            params: Dict[str, Any] = {
754                "model": target.model,
...
759                "temperature": target.temperature,     ← read DIRECTLY from target; no intermediary
760                "max_tokens": target.max_output_tokens,
761            }
...
764            integrity = _check_generation_integrity(target, params)
765            self.last_integrity = integrity
767            resp = client.chat.completions.create(**params)   ← temperature passed EXPLICITLY
```
Temperature is read straight from `target.temperature` at `:759` — no `.get(...)` default, no
substitution, no intermediary. It is placed in `params` unconditionally and passed to the SDK at
`:767` via `**params`.

### 2. Any DEFAULT temperature on the path? — **NONE applies.**
- No `params.get("temperature", <default>)` anywhere on the xAI path — temperature is set
  unconditionally at `:759`.
- `ModelTarget` default is `0.0` (`:161`) — and it is explicitly overridden with `0.0` anyway.
- The SDK's own default would apply ONLY if `temperature` were absent from the request; it is never
  absent (`:759` always includes it), so the SDK default is unreachable.

### 3. Any OVERRIDE or MUTATION between construction and the wire? — **NONE.**
- Between `params` construction (`:753-761`) and `create(**params)` (`:767`) the only statements are
  `_check_generation_integrity(target, params)` (`:764`) and `self.last_integrity = integrity`
  (`:765`). The integrity function is READ-ONLY on `params`: it builds new dicts
  (`declared/transmitted/omitted`) and only ever reads `params` (`provider_router.py:79`
  `if "temperature" in params: transmitted["temperature"] = params["temperature"]`) — it never
  assigns to `params`. So `params["temperature"]` is not clamped, rounded, re-assigned, or
  transformed.
- `RouterConfig` (`:164-177`) has no temperature field. `ProviderRouter.__init__` (`:849-865`) and
  `_get_adapter` (`:867-882`) never touch temperature. `XAIAdapter.__init__` (`:736-743`) stores
  only api_key/base_url/SDK class.

### 4. Any CONDITIONAL branch (other than TEMPERATURE_ONLY_DEFAULT_MODELS) for grok-4.3? — **NONE.**
```
30    TEMPERATURE_ONLY_DEFAULT_MODELS: frozenset = frozenset({
31        "gpt-5.5",   # ...
32    })
```
grok-4.3 is NOT in the set. Moreover, the conditional-omission logic that consults this set lives in
`OpenAIAdapter._call_once` (`:352-361`), NOT in `XAIAdapter`. `XAIAdapter.call` contains **no
temperature conditional at all** — it always sets `:759`. The only branches in `XAIAdapter.call` are
the post-call `except` handlers (`:770-779`), which re-raise/classify errors AFTER `create()`; none
retries with a different temperature (xAI has no effort-escalation retry, unlike OpenAI).

### 5. The xAI SDK call — explicit temperature, no reachable default.
`XAIAdapter` uses the OpenAI SDK against `base_url="https://api.x.ai/v1"` (`:741`,`:747-751`), calling
`client.chat.completions.create(**params)` (`:767`) with `params["temperature"] = 0.0` always
present. The SDK forwards the explicit value; its "absent → provider default" behavior is never
triggered because the field is never absent.

## Conclusion
`transmitted_temperature ≡ target.temperature` identically, by construction (`:759` → `:767`, no
transform in between). Since `target.temperature = 0.0` for Role C, the transmitted temperature can
only ever be `0.0`. There is **no** default, override, mutation, or alternate branch by which it
could differ.

Corollary (already in the harness): `_provider_call` captures `adapter.last_integrity` per call
(`:769` → `call_meta["temperature_integrity"]` → the per-role object). xAI's own
`_check_generation_integrity` (`:764`) records `temperature` as **transmitted** (present in params),
so the run already carries per-call evidence that `temperature=0.0` was on the wire — xAI's integrity
check is not even vacuous for temperature *presence*; it simply cannot detect an *omission* because
xAI structurally never omits.

## Implication for the Role-C integrity question
**RESOLVED as CLEAN → the Role-C integrity requirement dissolves.** The omission failure mode that
`_check_generation_integrity` guards is structurally impossible for grok-4.3 (not in the set; xAI has
no omission path), and no non-omission drift path exists (transmitted ≡ declared). A harness-side
outbound temperature check for Role C would have nothing to catch. This also means the Step-434
config-integrity halt (which fires on OpenAI's wrapped `config_integrity_violation`) remains the
complete story: A and C propagate fatals (type-halt), B wraps (message-halt), and none of the three
can silently drift temperature.

## Discipline
`git status --porcelain cam/` empty (read-only). `git status --porcelain` shows only the new 438
finding docs under `build_log/`. Zero provider calls. No `cam/` file read-modified — read only.
