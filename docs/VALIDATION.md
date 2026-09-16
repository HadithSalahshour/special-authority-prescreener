# Validation plan

The current repository demonstrates engineering controls; it does not establish
clinical validity.

Before any real-world pilot, build a versioned, clinician-reviewed benchmark containing:

1. Separate policy-indication and renewal pathways.
2. Clearly labelled AND/OR criterion groups.
3. Positive, negative, incomplete, contradictory, and boundary-value cases.
4. Expected citations, not only expected verdicts.
5. Policy version and source URL for every case.

Report at minimum:

- Criterion-level sensitivity and specificity.
- False-positive rate for `MET`.
- Citation exactness and relevance.
- Numeric-boundary accuracy.
- Patient-level abstention/manual-review rate.
- Results stratified by drug, indication, and criterion type.

The release gate should prioritize avoiding unsupported `MET` results. A model score
alone is not enough; error analysis and independent clinical review are required.
