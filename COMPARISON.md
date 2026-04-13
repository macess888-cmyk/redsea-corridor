# Cross-Zone PASS / FAIL Matrix

| Zone / Case | Declared Scope Holds | Present-State Execution | Refusal Available at Bind | Proof Present at Bind | Primary Violation | Co-Violations | Outcome |
|---|---|---|---|---|---|---|---|
| Base Pass | YES | YES | YES | YES | None | none | PASS |
| Base Drift / Fail Fixture | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION, ROUTE_WINDOW_INVALID, CLASSIFICATION_INVALID, CIVILIAN_CLASS_NOT_PROTECTED | FAIL |
| Red Sea Drift | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| Greenland Drift | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| Taiwan Strait Probe | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| Universal Drift | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| AI Monitoring Claim | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| Autonomy Constraint Claim | NO | NO | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION | FAIL |
| Near-Pass Regrounded Expansion | NO | YES | YES | YES | MISSION_SCOPE_EXPANSION | none | FAIL |
| Near-Pass Delayed Refusal | YES | YES | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | none | FAIL |
| Proof-Fail Boundary | YES | YES | YES | NO | MISSING_PROOF_SOURCES | none | FAIL |
| Refusal-Fail Boundary | YES | YES | NO | YES | REFUSAL_UNAVAILABLE_AT_BIND | none | FAIL |
| Scope-Fail Boundary | NO | YES | YES | YES | MISSION_SCOPE_EXPANSION | none | FAIL |
| Adversarial Full-Fail | NO | NO | NO | NO | MISSING_PROOF_SOURCES | REFUSAL_UNAVAILABLE_AT_BIND, CARRIED_STATE_EXECUTION, MISSION_SCOPE_EXPANSION, ROUTE_WINDOW_INVALID, CLASSIFICATION_INVALID, CIVILIAN_CLASS_NOT_PROTECTED | FAIL |
| Pressure-Stable Pass | YES | YES | YES | YES | None | none | PASS |

---

## Readout

### Universal failure signature
Across geopolitical, AI, autonomy, and abstract cases, the recurring drift signature is:

- Primary: `REFUSAL_UNAVAILABLE_AT_BIND`
- Co-violations:
  - `CARRIED_STATE_EXECUTION`
  - `MISSION_SCOPE_EXPANSION`

### Distinct boundary classes
These remain isolated and do not collapse into drift:

- `MISSING_PROOF_SOURCES`
- `MISSION_SCOPE_EXPANSION`
- `REFUSAL_UNAVAILABLE_AT_BIND`

### Strongest current hypothesis
The deepest cross-domain invariant is:

**If refusal is unavailable at bind, a system cannot reliably prevent escalation drift.**

---

## Notes

- `None` means no violation fired.
- `none` in co-violations means no additional violations beyond the primary.
- `YES` / `NO` entries reflect the case design, not interpretation after the fact.