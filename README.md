# ai201-project3-takemeter

Classifying **r/soccer** comments by take quality: `analysis` (a claim backed by a
concrete, checkable reason) vs. `hot_take` (a bare strong opinion). See
[planning.md](planning.md) for the full label design, data collection, and
evaluation plan.

- **Dataset:** [takemeter_labeled.csv](takemeter_labeled.csv) — 217 human-reviewed
  comments from 9 World Cup match threads (145 `hot_take` / 72 `analysis`, 66.8% / 33.2%).
- **Model:** `distilbert-base-uncased`, fine-tuned on the 70% train split.
- **Artifacts:** [evaluation_results.json](evaluation_results.json),
  [confusion_matrix.png](confusion_matrix.png).

## Hyperparameters

Used the notebook defaults — **3 epochs, learning rate 2e-5, batch size 16**.
No hyperparameters were changed.

---

# Evaluation Report

## Overall results

| Model | Accuracy | Macro-F1 |
|---|---|---|
| Zero-shot baseline (LLM prompt) | **0.758** | 0.75 |
| Fine-tuned DistilBERT | **0.667** | **0.40** |

**The fine-tuned model performed *worse* than the baseline (−0.091 accuracy, and
macro-F1 nearly halved).**

## Per-class metrics

**Baseline (zero-shot LLM):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| analysis | 0.59 | 0.91 | 0.71 | 11 |
| hot_take | 0.94 | 0.68 | 0.79 | 22 |
| **macro avg** | 0.76 | 0.80 | 0.75 | 33 |

**Fine-tuned DistilBERT:**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| analysis | 0.00 | 0.00 | 0.00 | 11 |
| hot_take | 0.67 | 1.00 | 0.80 | 22 |
| **macro avg** | 0.33 | 0.50 | 0.40 | 33 |

The fine-tuned model scores **0.00 on every analysis metric** — it never once
predicted the minority class.

## Confusion matrix — fine-tuned model (test set, n=33)

| | Predicted: analysis | Predicted: hot_take |
|---|---|---|
| **Actual: analysis** | 0 | 11 |
| **Actual: hot_take** | 0 | 22 |

(`confusion_matrix.png` is the committed image copy of this table.)

Every error is in **one direction: `analysis → hot_take`** (11/11 analysis
comments misclassified, 0 hot_takes misclassified). The model predicted `hot_take`
33/33 times. Its 0.667 accuracy is *exactly* the "always guess the majority class"
rate.

## AI-assisted pattern surfacing (and verification)

I pasted the misclassified examples into an LLM (Claude) and asked it to find
common themes across the errors. What it proposed, and what I did with it:

- **Proposed:** "All errors are directional (`analysis → hot_take`)." → **Verified**
  against the confusion matrix — true, 11/11.
- **Proposed:** "The misclassified analysis comments tend to *open* with generic
  evaluative/celebratory phrasing (‘Great game’, ‘Good win’, ‘Good defence but…’)
  and only reveal their concrete reasoning later." → **Verified** by re-reading all
  three (below) — confirmed; each leads with hot-take-style language.
- **Proposed and discarded:** "Length is the signal — short posts get called
  hot_take." → **Discarded after checking:** example #2 is one of the *shortest*
  comments in the set and example #1 is one of the *longest*, yet both were
  misclassified identically (confidence 0.53–0.54). Length is not the
  discriminator. I removed this from the analysis.

The decisive correction came from the **confidence scores** (0.53–0.54 on a binary
task ≈ a coin flip). The model isn't *confidently* wrong; its logits are nearly
flat and tip to the majority class by a hair. That reframes the failure: not
"learned the wrong rule" but "learned almost nothing and defaulted to the prior."

## Three wrong predictions (with analysis)

All three are **true `analysis`, predicted `hot_take`** — and notably all are
*borderline* analysis comments that lead with generic praise before the substance.

**#1 — germany_vs_ivory_coast (conf. 0.54)**
> "Great game from both teams. The intensity, the duels, the counters, the nerves... it really felt like a knockout game. Congratulations to Germany... Adingra's miss was diabolical. When I saw Undav starting to enter the pitch, I knew he would be the X Factor and the turning point... They won against us (France) convincingly weeks ago in a friendly."

The analytical content (Adingra's miss, Undav as the turning point, the France
friendly as evidence) is real, but it's **buried under three sentences of vibes**
("intensity, duels, nerves," "felt like a knockout game," congratulations). The
surface reads hot_take; the substance is analysis.

**#2 — spain_vs_saudi_arabia (conf. 0.53)**
> "Good win, still a lot of practice and getting into form needed. They especially need a threat on the left, something Fermin might have contributed. Starting Olmo was immense, especially against that low block."

A concrete tactical point (needs a left-side threat; Olmo's value *against a low
block*) wrapped in generic openers ("Good win," "getting into form needed"). It's
also short — so the model has little signal beyond the hot-take-flavored phrasing.

**#3 — ecuador_vs_curacao (conf. 0.53)**
> "Good defence but they are lacking up top... hope for this team in Ecuador because of Caicedo, Hincapié and Pacho but there's big gaps. I feel like the team has been pretty overrated because of their qualifying performance..."

A genuine squad diagnosis (strong defense / weak attack, named players, an
overrated-by-qualifying argument) — but it opens with "Good defence but…" and
reads like a verdict.

### Which labels, why hard, labeling vs. data, and the fix

- **Which labels are confused:** 100% directional, `analysis → hot_take`. The
  model never learned to *emit* `analysis`.
- **Why the boundary is hard:** the hardest analysis comments **lead with
  hot-take-style language** (celebration, "good win," broad verdicts) and only
  surface their concrete reasoning mid-paragraph. Structure signals analysis;
  opening tone signals hot_take.
- **Labeling problem or data problem?** I checked: I labeled these *consistently* —
  comparable "praise-then-reasoning" comments are all `analysis` in my data, so
  this is **not annotation inconsistency**. It's a **data-distribution problem**:
  with only ~50 analysis examples in training and a 67/33 prior, the model never
  got enough signal to override the majority bias, *especially* for the borderline
  cases where the concrete reason is brief or buried.
- **What would fix it:** (1) class weights or oversampling `analysis`; (2) more
  `analysis` examples, pushing the split toward 50/50; (3) **more of the hard case
  specifically** — analysis comments that open with generic praise — so the model
  learns to look past the opening tone; (4) lower LR / fewer epochs to reduce the
  pull toward the majority prior.

## Sample Classifications (fine-tuned model)

| Comment (truncated) | True | Predicted | Confidence |
|---|---|---|---|
| "Great game from both teams… Adingra's miss was diabolical… Undav… the turning point" | analysis | hot_take | 0.54 |
| "Good win… they especially need a threat on the left… Starting Olmo was immense vs that low block" | analysis | hot_take | 0.53 |
| "Good defence but they are lacking up top… Caicedo, Hincapié and Pacho but there's big gaps" | analysis | hot_take | 0.53 |
| "Ref aside, the Egyptians are a class above NZ… Egypt just too good." | hot_take | **hot_take ✓** | 0.528 |

**Why the correct prediction is reasonable:** the last row ("Egypt are a class
above NZ, just too good") is predicted `hot_take` correctly — and rightly so: the
text is a pure verdict with no concrete play, stat, or mechanism, which is exactly
the `hot_take` definition. But note the confidence is **0.528** — barely above the
0.5 coin-flip line. Every prediction, right or wrong, sits at ~0.53, which confirms
the model isn't discriminating; it's outputting a near-constant majority guess and
is "correct" only when the true label happens to be the majority class.

## Reflection: what the model captured vs. what I intended

I intended the model to capture a **semantic** distinction: *is there a concrete,
checkable reason behind the claim?* What it actually captured was almost nothing
discriminative — it **overfit to the class prior** (predict the 67% majority) and
to shallow surface tone, not to the presence-of-evidence criterion my labels
encode.

- **What it overfit to:** the base rate. With a small, imbalanced set, "always
  `hot_take`" is a low-loss shortcut, and 3 epochs wasn't enough signal to leave it.
- **What it missed:** the entire `analysis` concept. It never learned that
  tactical mechanisms, named sequences, or stats should pull a comment toward
  `analysis` — which is the whole point of the project. The gap between my label
  definition (a content/evidence test) and the model's decision boundary (a
  near-constant majority guess) is total for the minority class.

The honest takeaway: the label *definition* is sound and human-consistent, but the
*dataset* is too small and too skewed for fine-tuning to recover it. The baseline
LLM, which brought a strong prior about "what counts as reasoning," actually
captured the intended distinction better — the opposite of what I expected.

## Spec reflection

- **How the spec helped:** the milestone spec's **mandatory class-imbalance check
  (>70% rule)** caught that my dataset was 71% `hot_take` and forced me to collect
  more `analysis` before training. Without that gate I'd have trained on an even
  worse split and likely not understood *why* the model collapsed — the spec turned
  a silent failure into a diagnosable one.
- **How I diverged:** the spec frames fine-tuning as the step that *improves* on the
  baseline. My implementation produced a model that did the opposite, and I chose to
  **report the negative result honestly rather than tune hyperparameters until the
  number went up.** I diverged from the implied "beat the baseline" goal because
  forcing an improvement on 217 examples would have been overfitting to the test
  set, not real learning — the honest finding (small/imbalanced data → majority
  collapse) is more useful than a massaged metric.

## AI usage

- **Annotation (disclosed):** all 217 comments were **pre-labeled by an LLM (Claude
  Opus, via Claude Code)** using the planning.md §2 definitions, then **human-
  reviewed in full** — I read every comment and kept the AI labels after agreeing
  with them. Tracked during review via a `reviewed` flag.
- **Failure-pattern analysis:** I directed the LLM to cluster the misclassified
  examples and name common themes. It produced the "directional `analysis →
  hot_take`" observation and the "leads-with-generic-praise" pattern (both kept
  after I verified them), and a "length is the signal" hypothesis that **I tested
  and discarded** (counterexamples #1 long / #2 short, both wrong).
- **Pipeline & drafting:** the data-cleaning/filtering scripts (`data/`) and the
  first draft of this README were AI-generated; I directed the structure, supplied
  the real metrics/predictions, verified every number against the notebook output,
  and corrected the analysis (e.g. removing the length hypothesis, replacing
  invented example posts with the actual misclassified test rows).
