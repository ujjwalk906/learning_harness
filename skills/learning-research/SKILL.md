---
name: learning-research
description: Research and inspect reliable material for an evolving learning goal, preserving source provenance and mapping justified capabilities. Use alongside a learning journey when sources or prerequisites need investigation.
---

# Research for the next useful learning step

The guide decides the teaching sequence; this workflow finds, inspects and
preserves suitable sources. Read the goal and relevant evidence with `resume COURSE`.
Research a coherent starting route and deepen it as needed. A complete library or
finished syllabus is not a prerequisite for learning. Match the requested subject,
depth, language, accessibility and real-world use. Reported prior knowledge stays
unassessed.

Find high-quality teaching and appropriate primary references. Read the actual
chapter, example or exercise before claiming it supports the target capability.
Record exact sections, why they are useful, inspected scope, version assumptions
and limitations using `record COURSE resource FILE`. A bibliography alone is not
research or teaching. Record inaccessible sources as unresolved rather than read.

When preserving originals is useful and rights permit, use `learn.py acquire`:

```sh
python3 learn.py acquire COURSE --id SOURCE --title TITLE --url URL \
  --method git --revision COMMIT --license LICENSE --license-file LICENSE_PATH \
  --reason 'Why this source fits the goal'
python3 learn.py verify-sources COURSE
```

Methods are file, archive, git and local. Archives require explicit include paths;
Git requires a revision. Inspect `acquire --help`. Code preserves bytes and receipts;
it cannot determine whether license metadata is true. Do not download without a
reuse basis, execute downloaded code during acquisition, or edit originals/receipts
to accept an alteration. Corrections belong in adjacent research notes.

Within the guide's coarse objective map, investigate prerequisite detail for the
current unit. Explain each required edge by the mechanism it enables, retaining
uncertainty for proposed dependencies. Cite recorded resources and propose
observable capabilities; the guide integrates these into the teaching plan.
Preserve originals rather than replacing them with an agent-generated book.

When a claim is disputed, inspect the source again and resolve or document the
uncertainty. Save findings with exact pointers for the guide's next decision.
Research and source checks never establish learner understanding.
