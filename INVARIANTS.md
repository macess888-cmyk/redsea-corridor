# Execution Invariants

## Universal drift signature
A case fails universally when all three appear together:

- REFUSAL_UNAVAILABLE_AT_BIND
- CARRIED_STATE_EXECUTION
- MISSION_SCOPE_EXPANSION

## Distinct boundary classes
These are separate and should not be conflated:

- MISSING_PROOF_SOURCES
- REFUSAL_UNAVAILABLE_AT_BIND
- MISSION_SCOPE_EXPANSION

## Pressure-stable pass conditions
A case passes under pressure only if all of these hold:

- proof present at bind
- refusal available at bind
- execution originates from present state
- declared scope holds
- classification valid
- route window valid

## Current conclusion
The deepest cross-domain invariant is:

If refusal is unavailable at bind, the system cannot reliably prevent escalation drift.