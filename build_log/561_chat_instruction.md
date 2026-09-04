Step 561. Add "applicable" to DEGRADABLE_APPLICABILITY. One constant.

Step 560's measurement: applicable => must_abort has never fired on a
`required` LP, and every recorded firing on a conditional LP was a false
classification. Three real leases -- albireo, everbridge, ncino -- are
blocked by it today. Its protective value is unmeasured.

`required` LPs still abort. Only `applicable` degrades.

RECORD THE TRADE IN THE CODE, not only the status. A comment at the
constant stating: this trades a measured false-abort rate of 3 of 4
documents against an unmeasured true-abort rate of zero-so-far. It is
defensible on the evidence and indefensible in principle. If a conditional
LP is ever genuinely present and extraction misses it, this change turns a
loud abort into a degraded report -- and the degraded path (Steps 476-478,
497) is what carries that fact to the reader. Revisit if that case is ever
observed.

RUN, in order, stopping after any abort:
  albireo, everbridge, ncino.

REPORT per document, per Step 559's shape. Additionally:
  - which LPs now degrade that previously aborted, and what each produces
  - does the degraded banner name them, and does a reader see it
  - any headline asserting something the document contradicts -- that is
    the only thing worth interrupting for
  - everbridge and albireo each keep an LP-21 blocker per Step 560. If
    they still abort on LP-21, report it and stop; that is a required LP
    and this change should not touch it.

Do NOT implement Step 535's rule. Do NOT touch any clue list.
