# Claim lock contract

Use a lock only for terms whose exact form must survive the rewrite. Save it as UTF-8 JSON:

```json
{
  "protected_exact": ["Treatment A", "95% CI"],
  "forbidden_in_revision": ["proves", "causes"]
}
```

`protected_exact` values must already occur in the source and must occur unchanged in the revision. `forbidden_in_revision` values must not occur in the revision. Matching is case-sensitive and literal.

The checker always compares these surface invariants, with or without a lock:

- source and revision must both contain non-whitespace text;
- numeric expressions, including signs, decimals, exponents, and percentages;
- numeric bracket citations, DOI strings, URLs, and author-year parentheses;
- explicit negation markers;
- maximum evidence-strength language;
- newly introduced causal language.

These checks are conservative. A failure can be a harmless rephrasing, while a pass can still hide semantic drift. Never use the result as proof of scientific equivalence.

## Trigger examples

- Tighten a results paragraph without changing claims or citations.
- Remove repetitive phrasing while keeping uncertainty and null findings.
- Make a technical passage read naturally after its scientific content is frozen.

## Non-trigger examples

- Decide whether the conclusion is supported by the data.
- Summarize or translate a paper.
- Strengthen an abstract, add citations, or infer practical implications.
- Reconcile contradictory studies or calculate a statistic.
