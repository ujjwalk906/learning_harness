---
name: learning-research
description: Research and inspect reliable material for an evolving learning goal, preserving source provenance and mapping justified capabilities. Use alongside a learning journey when sources or prerequisites need investigation.
---

# Research for the next useful learning step

Read the current goal and relevant evidence with the shared `learn.py resume COURSE`.
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

Map fine enough concepts to identify prerequisites and evidence. Explain every
required edge with the mechanism it enables. Keep helpful connections distinct
from prerequisites; retain uncertainty for proposed dependencies. Cite recorded
resource IDs in graph nodes. Use meaningful observable target capabilities and
limit required scope to the learner's goal. Preserve original materials rather
than replacing them with an agent-generated book.

When a claim is disputed, inspect the source again and resolve or document the
uncertainty. Save decision-grade notes with exact pointers, then record the next
purpose. Research and source checks never establish learner understanding.
