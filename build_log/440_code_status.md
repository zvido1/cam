# Step 440 — DEFINITIVE READ: does XAIAdapter run `_check_generation_integrity`? → **YES** (explicit call at line 764)

**VERDICT (one sentence):** `XAIAdapter.call` runs `_check_generation_integrity` on its call path via
an **explicit call to the module-level function at line 764** — confirmed by the executed source
(`inspect.getsource(XAIAdapter.call)` contains the call) and by `self.last_integrity = integrity` at
line 765 — even though `hasattr(XAIAdapter, '_check_generation_integrity')` is **False** because the
function is module-level, NOT an inherited base-class method.

READ-ONLY. Zero edits, zero model calls. `git status --porcelain cam/` empty (no cam file touched).

---

## 1. CLASS HIERARCHY (verbatim, with line numbers)
```
299    class BaseAdapter:
300        # Step 372c: most recent call's token usage (None until a call populates it).
301        last_usage: Optional[dict] = None
302
303        def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
304            raise NotImplementedError
```
```
306    class OpenAIAdapter(BaseAdapter):
422    class AnthropicAdapter(BaseAdapter):
728    class XAIAdapter(BaseAdapter):
```
All three inherit `BaseAdapter`. `BaseAdapter` defines only `call` (abstract) and `last_usage` — it
does NOT define `_check_generation_integrity` and does NOT define `last_integrity`.

## 2. `_check_generation_integrity` — grep of the WHOLE file (every occurrence, with line numbers)
```
53:  def _check_generation_integrity(                                             ← THE definition (module-level)
329:         Runs _check_generation_integrity before every call — undocumented ... ← docstring text only
375:         integrity = _check_generation_integrity(target, params, temperature_omit_reason)  ← CALL (OpenAI._call_once)
461:             integrity = _check_generation_integrity(target, params, temperature_omit_reason)  ← CALL (Anthropic.call)
764:             integrity = _check_generation_integrity(target, params)          ← CALL (XAIAdapter.call)
```
**Definitively: there is ONE definition** — a **module-level function** at line 53 (column 0, not
indented under any class):
```
53    def _check_generation_integrity(
54        target: "ModelTarget",
55        params: dict,
56        temperature_omit_reason: Optional[str] = None,
57    ) -> dict:
```
It is **NOT defined on the base class, NOT defined on any adapter, NOT overridden anywhere.** It is a
free function that three adapters CALL: OpenAI (`:375`), Anthropic (`:461`), and **xAI (`:764`)**.
XAIAdapter neither defines nor inherits it as a method — it invokes the module function directly.

## 3. `XAIAdapter.call` — FULL BODY, verbatim, with line numbers
```
745        def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
746            timeout_sec = target.timeout_sec if target.timeout_sec else 60.0
747            client = self._openai_class(
748                api_key=self.api_key,
749                base_url=self.base_url,
750                timeout=timeout_sec,
751            )
752            try:
753                params: Dict[str, Any] = {
754                    "model": target.model,
755                    "messages": [
756                        {"role": "system", "content": system_prompt},
757                        {"role": "user", "content": user_prompt},
758                    ],
759                    "temperature": target.temperature,
760                    "max_tokens": target.max_output_tokens,
761                }
762
763                # Step 416: integrity assertion — temperature unconditionally transmitted.
764                integrity = _check_generation_integrity(target, params)
765                self.last_integrity = integrity
766
767                resp = client.chat.completions.create(**params)
768                self.last_usage = _extract_usage(resp)
769                return (resp.choices[0].message.content or "").strip()
770            except FatalProviderError:
771                raise
772            except Exception as e:
773                msg = f"xai_error: {type(e).__name__}: {e}"
774                s = str(e).lower()
775                if "429" in s or "rate" in s or "timeout" in s or "temporarily" in s:
776                    raise RetryableProviderError(msg)
777                if "401" in s or "unauthorized" in s or "invalid api key" in s:
778                    raise FatalProviderError(msg)
779                raise ProviderError(msg)
```
**Does it call `_check_generation_integrity`? YES — line 764**, before the client call at `:767`.

## 4. `last_integrity` — grep, every assignment (with line numbers)
```
315:     last_integrity: Optional[dict] = None    ← OpenAIAdapter class attr
376:         self.last_integrity = integrity      ← set in OpenAIAdapter._call_once
427:     last_integrity: Optional[dict] = None    ← AnthropicAdapter class attr
462:             self.last_integrity = integrity  ← set in AnthropicAdapter.call
734:     last_integrity: Optional[dict] = None    ← XAIAdapter class attr
765:             self.last_integrity = integrity  ← set in XAIAdapter.call
```
On the xAI path, `last_integrity` is **set at line 765** (to the record returned by `:764`). It is
**not None** after a call. (The class default `None` at `:734` is overwritten by `:765` every call.)

## 5. RUNTIME INTROSPECTION (executed, no model call) — the settling evidence
```
1) hasattr(XAIAdapter, "_check_generation_integrity") = False
   (False expected: it is a MODULE function, not a class method)
2) hasattr(module, "_check_generation_integrity") = True
3) XAIAdapter.__mro__ = ['XAIAdapter', 'BaseAdapter', 'object']
4) which MRO class defines _check_generation_integrity: NONE (not a method on any class in the MRO)
5) module-level def _check_generation_integrity at line 53 -> def _check_generation_integrity(
6) inspect.getsource(XAIAdapter.call) contains a call to _check_generation_integrity: True
   XAIAdapter.call -> integrity = _check_generation_integrity(target, params)
   XAIAdapter.call -> self.last_integrity = integrity
7) BaseAdapter defines last_integrity? False | XAIAdapter defines last_integrity? True
```
This settles it by execution: the function is module-level (2,5), not on any class in xAI's MRO
(1,3,4), yet `XAIAdapter.call`'s executed source invokes it and assigns `last_integrity` (6). So the
check RUNS on xAI despite `hasattr` on the class being False.

## VERDICT + reconciliation of the three prior reads
**Does XAIAdapter run `_check_generation_integrity` on its call path? YES** — explicit call at
`provider_router.py:764`, quoted above, executed-source-confirmed (§5 item 6), with `last_integrity`
set at `:765`.

- **"xAI has NO check, last_integrity is None"** → **WRONG.** Refuted by `:764` (call) and `:765`
  (`self.last_integrity = integrity`). Likely origin of the error: `hasattr(XAIAdapter,
  '_check_generation_integrity')` is False (§5 item 1) — a class-method/attribute check returns
  False because the function is module-level, which was mis-read as "no check." The call site
  disproves it.
- **"there IS a shared check, it RUNS on xAI" (435/Condition-1)** → **CORRECT on the outcome** (it
  runs on xAI, `:764`). Minor imprecision: it is a shared **module-level function**, not a
  base-class **method** (BaseAdapter does not define it; MRO defines none, §5 items 4,7). "Runs on
  xAI" = right.
- **"xAI does NOT inherit it, silent/no-op"** → **HALF right, HALF WRONG.** "Does not inherit it" is
  TRUE (`hasattr`=False; no MRO class defines it, §5 items 1,4). "silent/no-op" is FALSE — `:764`
  explicitly calls it and `:765` records the result. The correct-observation-wrong-conclusion: not
  inherited ⇏ not run; here it is not inherited but IS explicitly called.

**Net:** all three canonical adapters explicitly CALL the one module-level `_check_generation_integrity`
(OpenAI `:375`, Anthropic `:461`, xAI `:764`); none inherits it. xAI is neither missing it nor
no-op. This confirms the reads in Steps 435–439 (which located it at `:764`) and refutes the
"xAI silent/no-op" ruling.

*(Consistency note: the Step 439 report language calls Role C a "structural absence of the
OMISSION-GUARD" — that remains accurate under this finding. xAI DOES run `_check_generation_integrity`,
but because it transmits temperature unconditionally (`:759`), the check's temperature-OMISSION
branch (`:82-91`) is never exercised on grok; the check runs and confirms presence, it just cannot
catch an omission that structurally cannot occur. "Runs the check" and "the omission-guard branch is
structurally unreachable for grok" are both true and not in tension.)*

## Discipline
`git status --porcelain cam/` empty. Zero edits, zero model calls. Read-only introspection only.
