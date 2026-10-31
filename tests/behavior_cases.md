# Fictional teaching continuations

Manual author QA for teaching decisions, separate from runtime unit tests. These
cases stay outside the installed skill. They assess a next response and its saved
records, not teaching effectiveness, learner mastery or matching prescribed prose.

Prepare each as an isolated fictional course in a temporary directory. Save the
stated goal, relevant exchanges and checkpoint using the normal tools. For case 4,
publish its question and criteria before saving the supplied response. Give an
independent evaluator the skill and raw case without the expectations, asking it
to continue the journey and save any required records. Then inspect the response,
task and journal against the expectations. No separate model runner is required;
the active agent can perform continuations. Never use real learner records for QA.

1. **Answer follows a cue.** Goal: explain parcel-routing decisions. Tutor says
   parcels over 5 kg enter the heavy lane, then asks where an 8 kg parcel goes.
   Learner: "Heavy, because you literally say it is over the threshold."
   Expect: accept the selection, limit the conclusion to what was shown, and
   choose a later check without the supplied decision cue. A bare number swap
   following the same worked rule is practice, not evidence of broader reasoning.

2. **Terms without connections.** Goal: explain a reservation process. Prior
   instruction listed request, reserve, validate and release. Learner: "I know
   the words but cannot see how they connect. Can you explain the whole thing?"
   Expect: use one concrete process connecting the parts and clarifying what is
   reserved/released. A new glossary or compulsory quiz misses the request.

3. **Explicitly move on.** Goal: apply a document workflow. After an answer skips
   validation, the tutor offers another example. Learner: "Next please. Explain
   notifications; I do not want another quiz right now."
   Expect: explain notifications, preserve the unresolved validation check and
   offer a later review opportunity. Do not force an attempt or mark the gap solved.

4. **Right selection, wrong reason.** A fictional gate opens only when BOTH permit
   and stamp are current. The permit is current; the stamp expired. Announced
   criteria: choose whether it opens and explain why. Learner: "No notes or hints
   used. It stays closed because having a current permit blocks entry."
   Expect: judge the decision and reason separately against those criteria, show
   the specific correction and preserve the literal answer. Neither full credit
   for the reasoning nor rejection of the correct decision is justified.

5. **Blocked lab.** Goal: diagnose a fictional routing job. The proposed lab uses
   a hosted worker. Learner: "My account cannot create workers. Can we practise
   diagnosing it here?"
   Expect: supply a usable local trace/fixture or equivalent concrete task with
   an actual learner action. Keep live execution deferred; conceptual discussion
   or a promise of a later substitute alone does not fulfil the request.

6. **Explanations without consolidation.** Goal: explain a document workflow. The
   tutor has explained drafting, review, approval, release and notifications over
   successive turns; the learner has only said "got it" or "okay". Now: "What
   should we do next?"
   Expect: propose a connected reconstruction or synthesis task before another
   topic. Public criteria must not supply the required order. Acknowledgments
   are not evidence of demonstrated understanding.

7. **Coverage lags teaching.** Goal map: request creation and validation. Recorded
   exchanges explain creation and show conversational practice of validation; no
   formal assessment exists. Coverage reports are absent. Learner: "How far along
   are we?"
   Expect: reconcile coverage using those actual exchanges, distinguish exposure
   from assessed ability, and name remaining evidence. Neither zero learning from
   missing reports nor a mastery percentage is supported.
