---
name: refactor-expert
version: 0.1.0
domain: clean-code
activate-when:
  - code is long, nested, duplicated, or hard to read
  - asked to "make it cleaner", "shorter", "more organized" without changing behavior
  - before adding a feature to a file that already smells
verify-by:
  - run `forge refactor <file|dir>` (MCP `refactor.inspect`) and read the issues
  - behavior unchanged: tests still green after every step (run them, don't assume)
  - one smell fixed per step; small diff, not a rewrite
limits:
  - structure only — never remove or weaken a feature to shorten code
  - never rename/delete public API or change signatures without asking
  - never touch generated/vendored files; never reformat unrelated code
  - no behavior change without a green test proving it
---
# Refactor Expert

Make code shorter and clearer **without changing what it does**. The goal is
fewer lines with the same meaning — not fewer features.

## Measure first
- `forge refactor <file|dir>` → list of issues: `long-function`,
  `deep-nesting`, `duplicate-block`, `magic-number`, `too-many-args`, `god-class`.
- Work by severity: high → medium → low. One issue, one small commit.

## The safe recipe (behavior-preserving)
1. **Tests first.** If none cover the target, write one green test that captures
   current behavior. No test → no refactor.
2. **Long function (>50 lines):** name the inner chunk by what it *means*
   (`_parse_header`, `_retry_once`) and extract it. The top function should read
   like a summary: steps with names, not a wall of lines.
3. **Deep nesting (>3):** invert and exit early (guard clauses). `if not valid:
   return` at the top flattens the happy path.
4. **Duplicate block (3+ lines):** extract into one function/helper; both callers
   use it. Deletion here is repair, not feature loss.
5. **Magic number:** name it (`MAX_RETRIES = 5`) with a one-line "why".
6. **Too many args (>4):** group related args into a dataclass/config object.
7. **God-class (>200 lines):** split by responsibility (SRP); keep the public
   interface as thin delegations so callers don't change.

## Compact, not cryptic (the taste rule)
- Prefer a well-named function over a clever one-liner.
- Reuse over repetition: the second copy is the smell.
- Data over code: tables/maps replace long `if/elif` ladders.
- Delete dead code and commented-out blocks — git remembers them.
- Comments explain **why**, not **what**; if code needs a "what" comment, rename.

## When NOT to refactor
- Working code with no test and no clear win: leave it, note it, move on.
- A change that would alter public API, output format, or error messages:
  propose it, don't sneak it in.
- Hot paths where the "cleaner" version actually runs slower: measure, then decide.

## Quality bar
- Same inputs → same outputs. Tests green before and after.
- Diff is small and reviewable; each step is independently revertable.
- Net lines down or equal, readability up. Functions and features intact.
