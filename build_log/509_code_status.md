# Step 509 — Parts A and B clean. Part C BLOCKED on its own prerequisite.

**Date:** 2026-08-31 · **Instruction:** `build_log/509_chat_instruction.md`
**Default suite 369 passed, 3 skipped, call-free, 4.5s. Marked test 3/3 on real calls.**
**Part C NOT built — the SendGrid prerequisite is unestablished and I cannot establish it.**

---

# PART A — THE NON-LEASE FIXTURE

## The choice: a Mutual NDA, and every detail is deliberate

`05 Lease Analyzer/test_data/non_lease/mutual_nda.txt` — a **Mutual Non-Disclosure Agreement between
a commercial property owner and a capital partner**.

**Why an NDA rather than the software licence or the recipe:**

- **It genuinely gets mis-uploaded.** NDAs circulate in every real-estate transaction and sit in the
  same deal folder as the lease. This is the realistic negative the brief asked for.
- **It shares the lease register almost completely** — Delaware LLC parties with principal places of
  business, recitals, defined terms in quotes, term and termination, governing law, assignment,
  counterparts, a signature block. **A classifier keying on "looks like a commercial contract" gets
  this wrong.**
- **It even mentions real property, rent rolls and operating statements**, so keyword overlap alone
  does not save the gate.
- **What it lacks is what makes a lease:** no premises demised, no rent, no landlord/tenant
  relationship, no term of tenancy.

**A recipe would pass with any classifier at all** — the same failure as the Step-504 gemini false
positive one level up: *a check that cannot fail proves nothing.* The Step-508 recipe probe was
adequate to confirm the model resolved; it is not adequate as a regression test.

## Placement: NOT in the default suite, and why

**The suite must stay call-free.** It runs on every step, its output is quoted in every status file,
and CLAUDE.md forbids COMPLETE without pasted test output. **A test that spends money and needs
network on every step gets disabled the first time it flakes** — and then the regression protection
is gone precisely when it is believed to exist.

So `test_509_gate_discrimination.py` is skipped unless `CAM_RUN_PROVIDER_TESTS=1`:

```
default:     369 passed, 3 skipped, 12 subtests, 4.47s   (call-free, unchanged)
deliberate:  CAM_RUN_PROVIDER_TESTS=1 -> 3 passed, 3 subtests, 3.26s
```

**Cost to run: 3 provider calls** — 2 leases + 1 non-lease, `claude-haiku-4-5`,
`max_output_tokens=10` each. Fractions of a cent.

**The gap Step 508 recorded is closed:** a future change to the gate prompt or model now has a test
that can fail. The negative assertion carries its own reasoning in the failure message — *"a gate that
passes everything is indistinguishable from no gate."*

---

# PART B — `lease_template_reader` EXERCISED, AND IT WORKS

## Local, calling the reader directly

```json
{
  "landlord": "ATLAS INDUSTRIAL PROPERTIES LLC",
  "property": "4400 Industry Avenue, Brooklyn, New York 11232",
  "base_rent": "$28,520.83/month (Year 1), escalating to $32,112.92/month (Year 5)",
  "lease_term": "5 years",
  "governing_law": ""
}
```

## Deployed, through `POST /api/template/summary`

```json
{
  "landlord": "ATLAS INDUSTRIAL PROPERTIES LLC",
  "property": "4400 Industry Avenue, Brooklyn, New York 11232",
  "base_rent": "$28,520.83/month (Year 1), escalating annually",
  "lease_term": "5 years",
  "governing_law": "",
  "gate_passed": true,
  "gate_message": ""
}
```

**HTTP 200 with real content in both environments.** The Step-508 concern — *"the id resolving is not
the same as the call working"* — is settled: it works. Four of five fields populated, and
`gate_passed: true` confirms the new gate model in the same request.

## The empty `governing_law` is CORRECT, and it exposes a pre-existing limitation

I checked rather than assuming. **Atlas's governing-law clause is §24.3 at offset 27,178**, and
`read_template_summary` samples `text[:12000]`:

```
@27178  BEYOND 12000  ...Section 24.3. Governing Law. This Lease shall be governed by and
                         construed in accordance with the laws of the State of New York...
```

The only `applicable law` hits inside the sample are compliance-with-law obligations (§7, §8) —
**and the model correctly did not mistake them for a governing-law clause.** It returned empty rather
than fabricating, which is the behaviour you want.

**But the field is structurally unfillable for most leases.** Governing law is conventionally near the
end of a lease; divall's is at offset ~55,792 of 59,496. **The 12,000-character sample will miss it
almost every time.** That is a pre-existing limitation of the reader, not something Step 508
introduced, and it is unrelated to the model change. **Recorded, not fixed** — it is outside this
step's brief.

---

# PART C — BLOCKED ON ITS OWN PREREQUISITE

The brief is explicit: *"first establish whether SendGrid has ever sent from production. If it hasn't,
that is a prerequisite, not a detail."*

**I cannot establish it.** The determination needs the Railway log (`grep "Email not configured"`),
and my Railway CLI token is expired — `invalid_grant`, requiring interactive `railway login` in a
browser I cannot drive. Recorded at Step 505 §1 and unchanged.

**Why guessing is not acceptable here.** `notifications.py:325-330` returns `True` when nothing is
configured, and `job_manager.py:1683` discards the return value. **So the system cannot distinguish
"sent" from "silently did nothing" from the inside** — which means wiring alerting on top of it could
produce an alerting system that reports success while never sending an alert. **That is the exact
defect class this entire arc has been closing, and building it blind would be reproducing it
deliberately.**

## The cheapest way to settle it — proposed, NOT built

**Add email-configuration status to the authenticated `/api/provider-health` body.** It would report
which branch `send_email` would take in production — `sendgrid`, `gmail_api`, `smtp`, or
`not_configured` — by reading the same `sendgrid_configured(config)` / `email_configured(config)`
predicates the dispatcher uses at `notifications.py:332-338`.

- **Sends nothing.** No outward-facing action, no email to a real person.
- **No new mechanism.** Same config predicates, same authenticated endpoint, same always-200 contract.
- **Answers the prerequisite directly:** if production reports `not_configured`, then nothing has ever
  been sent and SendGrid must be configured before alerting means anything.

**The alternative — calling `/api/send-results-link` — would email a real person**, which is an
outward-facing action I am not taking unasked.

---

## WHAT IS NOT ESTABLISHED

- **Whether SendGrid has ever sent from production.** Part C's prerequisite. Unresolved.
- **Alerting is not built**, per the brief's ordering.
- **The non-lease fixture is a single document.** One NDA is a regression test, not a corpus. A
  services agreement or employment contract would broaden it; neither was added.
- **The gate has still never classified a real non-lease upload in production.** Verified on fixtures
  and probes only.
- **`governing_law` will be empty for most leases** because of the 12,000-character sample. Recorded
  above, not fixed, outside this brief.
