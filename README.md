# ai201-project3-takemeter

**Takemeter** classifies [r/soccer](https://www.reddit.com/r/soccer/) comments by
*take quality*: `analysis` (a claim backed by a concrete, checkable reason) vs.
`hot_take` (a bare strong opinion). Full design rationale is in
[planning.md](planning.md); this README is self-contained for grading.

- **Dataset:** [takemeter_labeled.csv](takemeter_labeled.csv) — 217 human-reviewed comments.
- **Model:** `distilbert-base-uncased`, fine-tuned on the 70% train split.
- **Artifacts:** [evaluation_results.json](evaluation_results.json), [confusion_matrix.png](confusion_matrix.png).

---

## 1. Community choice & reasoning

I chose **r/soccer** (~5M members), one of the most active text-discussion hubs in
sports. After every match, threads fill with hundreds of comments arguing tactics,
players, and results — and the quality of those comments varies enormously, from
one-word reactions to multi-paragraph tactical breakdowns.

That variation is exactly why it fits a classification task. In a single thread you
find bare verdicts ("Egypt just too good"), reasoned breakdowns ("they marked
man-to-man and shut down Germany's playstyle"), and a large mass of non-takes
(jokes, qualification math). The classes aren't trivially keyword-separable but
humans agree on clear cases — non-trivial yet learnable. It also scales easily: one
match thread yields 150–180 usable comments, so collecting 200+ is straightforward.

## 2. Label taxonomy

Two labels. Deciding question: **is the claim backed by a concrete, checkable reason
— a specific play, player, statistic, or tactical mechanism?**

### `analysis` — claim + a concrete, checkable reason.
- "They have a trainer who understands the German game and countered it perfectly… they stopped the Germans by marking man to man, it shut down a lot of Germany's playstyle."
- "Egypt's third goal was one of the worst defended corners I've ever seen. Trezeguet… was completely open and unmarked for like 5 seconds before the corner was taken."

### `hot_take` — a strong verdict/rating/prediction with little or no support.
- "Ref aside, the Egyptians are a class above NZ and the result is what you would expect. Egypt just too good."
- "They're just a mediocre team now. They are probably never winning another World Cup. 2010 was their last chance."

## 3. Data collection & labeling

**Source.** 9 public World Cup group-stage match threads from r/soccer, pulled as
raw JSON via Reddit's no-auth public JSON API (no private/authenticated content).
The unit is the **comment, not the post** — r/soccer posts are link/video shells
with empty bodies; all the discourse lives in the comment threads. ~1,564 comments
were flattened to `{score, body}`.

**Labeling process.**
1. Preprocess: keep comments with `score ≥ 5` and `body ≥ 100 chars`, then drop
   **non-takes** (jokes, reactions, qualification math, ticket/venue chatter,
   political/identity tangents) so only real *takes* remain.
2. An LLM (Claude Opus) **pre-labeled** each remaining take using the §2 definitions.
3. I **human-reviewed every label**, reading each comment and applying the decision
   rule; I kept the AI labels after confirming them.
4. To fix class imbalance (see below) I mined 13 additional `analysis` comments from
   the `score 3–4` pool and labeled those too.

**Label distribution.** 217 total — **145 `hot_take` (66.8%) / 72 `analysis`
(33.2%)**. The set initially came in at 71% `hot_take`, over the 70% imbalance
threshold; collecting the 13 extra `analysis` examples brought it under.

**3 difficult-to-label examples and my decisions:**

1. _"he won in 1994, and the 2006 lost in the quarters… Bielsa had Argentina
   eliminated by Sweden in 2002. And now Uruguay by Cape Verde… It's just not the
   same."_ → **`hot_take`.** It cites real scorelines, which *looks* like analysis,
   but they prop up a sweeping manager verdict rather than explain a match. Decision
   rule: cited results supporting a judgment ≠ analysis.
2. _"you sat back without a plan, not even a real defensive plan. Coach has to react
   quicker!"_ → **`analysis`.** It names a tactical mechanism (no defensive shape)
   even without a timestamped play. Decision rule: a named mechanism counts; a
   generic "they were bad" would not.
3. _"I have obvious biases but Salah was fantastic… it felt like every time Egypt was
   creating chances, Mo was involved."_ → **`hot_take`.** It offers a reason, but
   "felt like" + a general impression isn't a concrete, checkable play. Decision
   rule: impressions don't qualify as concrete support.

## 4. Fine-tuning approach

- **Base model:** `distilbert-base-uncased` (HuggingFace), a sequence-classification
  head over 2 labels.
- **Training setup:** 70/15/15 train/val/test split (notebook default), fine-tuned on
  the ~152 training comments.
- **Hyperparameters:** notebook defaults — **3 epochs, learning rate 2e-5, batch
  size 16**.
- **Hyperparameter decision:** I deliberately **kept epochs at 3 rather than
  increasing them.** With only ~152 training examples (≈10 steps/epoch at batch 16),
  more epochs would overfit and memorize rather than generalize. In hindsight the
  real lever I *should* have changed was **class weighting** — the default
  unweighted loss let the model collapse to the majority class (see Evaluation).

## 5. Baseline description

The baseline is a **zero-shot LLM classifier**: each test comment is sent to the
model with a system prompt defining the two labels and one example each, instructed
to output only a label string. Results were collected by parsing the model's
single-token response and comparing to the gold label; all 33 test responses parsed
cleanly (0% unparseable).

```
You are classifying comments from r/soccer, a football discussion community.
Each comment is a genuine "take" about a match, team, or player. Assign each
comment to exactly one of the following categories based on whether its claim
is backed by a concrete, checkable reason.

analysis: A comment that makes an evaluative or explanatory claim AND supports it
with a concrete, checkable reason — a specific play, player, statistic, or
tactical mechanism.
Example: "They stopped the Germans by marking man to man, it shut down a lot of
Germany's playstyle..."

hot_take: A strong evaluative claim — a rating, judgment, or prediction — stated
with little or no concrete support. Assertion over argument.
Example: "Ref aside, the Egyptians are a class above NZ... Egypt just too good."

Respond with ONLY the label name. Do not explain your reasoning.
Valid labels: analysis, hot_take
```

---

# Evaluation Report

## Overall results

| Model | Accuracy | Macro-F1 |
|---|---|---|
| Zero-shot baseline (LLM prompt) | **0.758** | 0.75 |
| Fine-tuned DistilBERT | **0.667** | **0.40** |

**The fine-tuned model performed *worse* than the baseline (−0.091 accuracy, macro-F1 nearly halved).**

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

The fine-tuned model scores **0.00 on every analysis metric** — it never once predicted the minority class.

## Confusion matrix — fine-tuned model (test set, n=33)

| Actual ↓ \ Predicted → | analysis | hot_take | Row total |
|---|---|---|---|
| **analysis** | 0 | 11 | 11 |
| **hot_take** | 0 | 22 | 22 |
| **Column total** | 0 | 33 | 33 |

(`confusion_matrix.png` is the committed image copy of this table.)

Read across the rows: of 11 true `analysis` comments, **0** were predicted `analysis`
and all **11** were predicted `hot_take`; of 22 true `hot_take` comments, all **22**
were predicted `hot_take`. Every error is in one direction (`analysis → hot_take`);
the model predicted `hot_take` 33/33 times, so its 0.667 accuracy is *exactly* the
majority-class rate.

## AI-assisted pattern surfacing (and verification)

I pasted the misclassified examples into an LLM (Claude) and asked it to find common
themes. What it proposed, and what I did with it:

- **Proposed:** "All errors are directional (`analysis → hot_take`)." → **Verified**
  against the confusion matrix — true, 11/11.
- **Proposed:** "Misclassified analysis comments *open* with generic
  evaluative/celebratory phrasing (‘Great game’, ‘Good win’, ‘Good defence but…’) and
  only reveal their reasoning later." → **Verified** by re-reading all three — confirmed.
- **Proposed and discarded:** "Length is the signal — short posts get called
  hot_take." → **Discarded:** example #2 is one of the *shortest* comments and #1 one
  of the *longest*, both misclassified identically. Length isn't the discriminator.

The decisive correction came from the **confidence scores** (0.53–0.54 on a binary
task ≈ a coin flip): the model isn't *confidently* wrong, its logits are nearly flat
and tip to the majority class by a hair. The failure is "learned almost nothing and
defaulted to the prior," not "learned the wrong rule."

## Three wrong predictions (with analysis)

All three are **true `analysis`, predicted `hot_take`** — and all are *borderline*
analysis comments that lead with generic praise before the substance.

**#1 — germany_vs_ivory_coast (conf. 0.54)**
> "Great game from both teams. The intensity, the duels, the counters, the nerves... it really felt like a knockout game. Congratulations to Germany… Adingra's miss was diabolical. When I saw Undav starting to enter the pitch, I knew he would be the X Factor and the turning point… They won against us (France) convincingly weeks ago in a friendly."

Real analytical content (Adingra's miss, Undav as the turning point, the France
friendly as evidence) **buried under three sentences of vibes**. Surface reads
hot_take; substance is analysis.

**#2 — spain_vs_saudi_arabia (conf. 0.53)**
> "Good win, still a lot of practice and getting into form needed. They especially need a threat on the left, something Fermin might have contributed. Starting Olmo was immense, especially against that low block."

A concrete tactical point (needs a left-side threat; Olmo's value *against a low
block*) wrapped in generic openers — and short, so little signal beyond the
hot-take-flavored phrasing.

**#3 — ecuador_vs_curacao (conf. 0.53)**
> "Good defence but they are lacking up top… hope for this team in Ecuador because of Caicedo, Hincapié and Pacho but there's big gaps. I feel like the team has been pretty overrated because of their qualifying performance…"

A genuine squad diagnosis (strong defense / weak attack, named players, an
overrated-by-qualifying argument) that opens "Good defence but…" and reads like a verdict.

**Which labels / why hard / labeling-vs-data / fix:**
- **Confused labels:** 100% directional, `analysis → hot_take`; the model never learned to *emit* `analysis`.
- **Why hard:** the hardest analysis comments **lead with hot-take-style language** and surface their reasoning mid-paragraph — structure says analysis, opening tone says hot_take.
- **Labeling or data problem?** I labeled these *consistently* (comparable "praise-then-reasoning" comments are all `analysis` in my data), so it's **not annotation inconsistency** — it's a **data-distribution problem**: ~50 analysis training examples against a 67/33 prior gave too little signal to override the majority bias, especially on borderline cases.
- **Fix:** class weights / oversampling `analysis`; more `analysis` data toward a 50/50 split; specifically more of the *hard case* (analysis that opens with generic praise); lower LR / fewer epochs.

## Sample Classifications (fine-tuned model)

| Comment (truncated) | True | Predicted | Confidence |
|---|---|---|---|
| "Great game from both teams… Adingra's miss was diabolical… Undav… the turning point" | analysis | hot_take | 0.54 |
| "Good win… they especially need a threat on the left… Starting Olmo was immense vs that low block" | analysis | hot_take | 0.53 |
| "Good defence but they are lacking up top… Caicedo, Hincapié and Pacho but there's big gaps" | analysis | hot_take | 0.53 |
| "Ref aside, the Egyptians are a class above NZ… Egypt just too good." | hot_take | **hot_take ✓** | 0.528 |

**Why the correct prediction is reasonable:** the last row is predicted `hot_take`
correctly — the text is a pure verdict with no concrete play, stat, or mechanism,
which is exactly the `hot_take` definition. But its confidence is **0.528**, barely
above the 0.5 coin-flip line. Every prediction, right or wrong, sits at ~0.53,
confirming the model isn't discriminating — it outputs a near-constant majority guess
and is "correct" only when the true label happens to be the majority class.

## Reflection: what the model learned vs. what I intended

I intended a **semantic** distinction: *is there a concrete, checkable reason behind
the claim?* What the model actually learned was almost nothing discriminative — it
**overfit to the class prior** (predict the 67% majority) and to shallow surface
tone, not to the presence-of-evidence criterion my labels encode.

- **Overfit to:** the base rate. On a small, imbalanced set, "always `hot_take`" is a
  low-loss shortcut, and 3 epochs wasn't enough to leave it.
- **Missed:** the entire `analysis` concept — it never learned that tactical
  mechanisms, named sequences, or stats should pull toward `analysis`, which is the
  whole point. The gap between my label definition (an evidence test) and the model's
  decision boundary (a near-constant majority guess) is total for the minority class.

Honest takeaway: the label *definition* is sound and human-consistent, but the
*dataset* is too small and skewed for fine-tuning to recover it. The baseline LLM —
which brought a strong prior about "what counts as reasoning" — captured the intended
distinction better, the opposite of what I expected.

## Spec reflection

- **How the spec helped:** its **mandatory class-imbalance check (>70% rule)** caught
  that my dataset was 71% `hot_take` and forced me to collect more `analysis` before
  training. Without that gate I'd have trained on a worse split and not understood
  *why* the model collapsed — the spec turned a silent failure into a diagnosable one.
- **How I diverged:** the spec frames fine-tuning as the step that *improves* on the
  baseline. My model did the opposite, and I chose to **report the negative result
  honestly rather than tune until the number went up.** Forcing an improvement on 217
  examples would be overfitting the test set, not real learning — the honest finding
  (small/imbalanced data → majority collapse) is more useful than a massaged metric.

## AI usage

- **Annotation (disclosed):** all 217 comments were **pre-labeled by an LLM (Claude
  Opus, via Claude Code)** using the §2 definitions, then **human-reviewed in full** —
  I read every comment and kept the AI labels after agreeing with them.
- **Failure-pattern analysis:** I directed the LLM to cluster the misclassified
  examples and name themes. It produced the "directional `analysis → hot_take`" and
  "leads-with-generic-praise" patterns (kept after I verified them) and a "length is
  the signal" hypothesis that **I tested and discarded** (counterexamples #1 long / #2
  short, both wrong).
- **Pipeline & drafting:** the data clean/filter scripts and the first draft of this
  README were AI-generated; I directed the structure, supplied the real
  metrics/predictions, verified every number against the notebook output, and
  corrected the analysis (removed the length hypothesis, replaced invented example
  posts with the actual misclassified test rows).
