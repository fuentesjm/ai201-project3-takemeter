# Takemeter — Project Planning

Classifying r/soccer comments by **take quality**: distinguishing a *supported
argument* (`analysis`) from a *bare strong opinion* (`hot_take`).

---

## 1. Community

**Chosen community: [r/soccer](https://www.reddit.com/r/soccer/)** (~5M members).

**Why this community.** r/soccer is one of the most active text-discussion hubs
in sports. After every match, threads fill with hundreds of comments arguing
about tactics, players, refereeing, and results — and crucially, the quality of
those comments varies enormously, from one-word reactions to multi-paragraph
tactical breakdowns. That spread is what makes "hot take vs. analysis" a *real*
distinction regulars recognize, not an artificial one.

**Why it's a good fit for classification.** The discourse is varied along exactly
the axis we want to model. In any single thread you find:
- bare verdicts ("Egypt just too good"),
- reasoned breakdowns ("they marked man-to-man and shut down Germany's playstyle"),
- and a large mass of non-takes (jokes, reactions, qualification math).

This variety means the task is non-trivial (the classes aren't trivially
separable by keywords) but still learnable (humans agree on clear cases). It's
also easy to collect at scale: a single match thread yields 150–180 usable
comments, and we collected **9 threads / 1,564 comments**, far exceeding the
200 minimum.

---

## 2. Labels

Two labels. Both assume the comment is already a real *take* (non-takes — banter,
reactions, logistics — are removed in preprocessing, see §4). The deciding
question:

> **Is the claim backed by a concrete, checkable reason — a specific play,
> player, statistic, or tactical mechanism? Yes → `analysis`. No → `hot_take`.**

### `analysis`
A comment that advances an evaluative or explanatory claim **and** supports it
with a concrete, checkable reason (a specific play, player, statistic, or
tactical mechanism).

- _(germany_vs_ivory_coast, score 18):_ "They have a trainer who understands the German game and countered it perfectly. IvC played a strong defense against Germany's strong offense and combined that with strong pressing and fast counters... they stopped the Germans by marking man to man, it shut down a lot of Germany's playstyle."
- _(new_zealand_vs_egypt, score 65):_ "Egypt's third goal was one of the worst defended corners I've ever seen. Trezeguet didn't even need to jump, let alone move. He was completely open and unmarked for like 5 seconds before the corner was taken."

### `hot_take`
A strong evaluative claim — a rating, judgment, or prediction — stated with
little or no concrete support. Assertion over argument.

- _(new_zealand_vs_egypt, score 98):_ "Ref aside, the Egyptians are a class above NZ and the result is what you would expect... Egypt just too good."
- _(uruguay_vs_cape_verde, score 13):_ "They're just a mediocre team now. They are probably never winning another World Cup. 2010 was their last chance."

---

## 3. Hard edge cases

**The genuinely ambiguous case: a verdict propped up by a cited result or stat,
with no in-match mechanism.** These look like analysis (they contain "evidence")
but function as hot takes (the evidence is selected to justify an opinion, not to
explain how the game was played).

- _Real example (uruguay_vs_cape_verde, score 10):_ "he won in 1994, and the 2006 lost in the quarters against a Zidane led team. Bielsa had Argentina getting eliminated by Sweden in 2002. And now Uruguay by Cape Verde or Saudi. It's just not the same."

A second ambiguous type: **a named tactical failing without a specific play** —
e.g. "you sat back without a plan, not even a real defensive plan" (spain, score
14). It points at a mechanism but never grounds it in an observed sequence.

**How I'll handle them during annotation (decision rules, fixed in advance):**
1. **Cited results/stats supporting a sweeping judgment → `hot_take`.** Reserve
   `analysis` for reasoning about *how the match was played* (tactics, a specific
   sequence, a player's role).
2. **A named tactical mechanism counts as `analysis`** even without a timestamp
   (e.g. "marked man to man"); a generic quality verdict ("they were bad
   defensively") does not.
3. **When still 50/50, default to `hot_take`** (the larger, less demanding class)
   and log the comment ID in an `edge_cases` note so the boundary can be reviewed
   in aggregate rather than decided inconsistently case-by-case.

---

## 4. Data collection plan

**Source.** Raw JSON dumps of r/soccer match threads (`data/<match>.json`),
flattened to `{score, body}` including nested replies. Comments, not posts —
r/soccer posts are link/video shells with empty bodies.

**Preprocessing.** Filter to `score ≥ 5` and `body ≥ 100 chars` (concentrates on
substantive, visible comments), then drop **non-takes** (jokes, emotional
reactions, qualification-scenario math, ticket/venue chatter, broadcast gripes,
political/identity tangents). Only real takes proceed to labeling.

**Counts.** Current labeled set: **204 comments** (`data/labeling_batch.json`)
across 9 threads — **145 `hot_take` / 59 `analysis`** (~71% / 29%).

**If a label is underrepresented after 200 (it is — `analysis` is the minority):**
1. **Target analysis-dense sources.** Match threads skew reactive; r/soccer's
   *post-match tactical* discussion and daily threads have a higher analysis
   ratio. Collect from those specifically to add `analysis` examples.
2. **Loosen the length filter upward** (e.g. `body ≥ 200`) on existing clean
   files — longer comments are disproportionately analysis — to mine more without
   new collection.
3. **In modeling, don't rely on raw counts:** use class weights / stratified
   splits, and report per-class metrics (§5) so the minority class isn't masked.
4. **Floor:** aim for **≥ 80 `analysis` examples** before training, so the
   minority class has enough signal for a meaningful F1 estimate.

---

## 5. Evaluation metrics

This is a **binary, class-imbalanced** task (~71/29), and the *valuable* class is
the minority one (`analysis` — the whole point of a "take quality" tool is
surfacing substance). Metric choices follow from that.

- **Accuracy is insufficient.** A trivial "always predict `hot_take`" model scores
  **~71% accuracy** while never identifying a single analysis comment. Accuracy
  rewards the majority class and hides total failure on the class we care about.
- **Per-class precision / recall / F1**, reported separately. For `analysis`:
  - **Recall** = of all real analysis comments, how many we catch (missing
    substance is the core failure mode of the tool).
  - **Precision** = of comments we *call* analysis, how many really are (false
    positives erode trust when surfacing "good takes").
- **Macro-F1** as the single headline number — it averages the two classes
  equally, so the minority class can't be ignored.
- **Confusion matrix** to see error direction (are we collapsing analysis →
  hot_take, the expected failure given imbalance and the §3 edge cases?).
- **Baselines to beat:** (a) majority-class (~0.71 acc, ~0.42 macro-F1) and
  (b) a TF-IDF + logistic-regression baseline. A model that doesn't clearly beat
  both isn't learning the distinction.
- **Cohen's κ on a human-verified subset.** Because all current labels are
  AI-generated (§7), I'll hand-verify a stratified sample and report κ between my
  human labels and the AI labels — this bounds how much label noise is inflating
  or deflating the scores.

---

## 6. Definition of success

**Useful = the tool can surface substantive takes more reliably than chance and
than a naive baseline, without drowning users in false "analysis" flags.**

Concrete, measurable targets on a **held-out, stratified test set** (≥ 40
comments, ≥ 12 of them `analysis`):

| Criterion | Target |
|---|---|
| Macro-F1 | **≥ 0.75** |
| `analysis` recall | **≥ 0.70** |
| `analysis` precision | **≥ 0.65** |
| Beats majority baseline macro-F1 (0.42) | **yes, by ≥ 0.25** |
| Beats TF-IDF baseline macro-F1 | **yes** |

**"Good enough for deployment"** in a real community tool (e.g. auto-highlighting
substantive comments): I'd prioritize **precision on `analysis` ≥ 0.75**, even at
the cost of recall, because a highlight feature that mislabels hot takes as
analysis loses user trust fast — better to surface fewer, but reliably good,
takes. I'll report the precision/recall trade-off curve and pick the threshold
that hits ≥ 0.75 precision, then check the resulting recall is still useful
(≥ 0.50).

**Are these criteria specific enough to objectively judge?** Yes — each is a
number on a defined held-out set, computed with named metrics, against named
baselines. At the end I can state pass/fail per row, not a vibe. The one
dependency I'm naming explicitly: the test set must be **human-verified**, not
AI-labeled, or I'd be measuring agreement with myself rather than correctness.

---

## 7. AI Tool Plan

There's no code to generate here, so AI tools are used at three specific points:

### 7a. Label stress-testing (do this before annotating further)
Give an LLM (Claude) the §2 definitions and the §3 edge-case description, and ask
it to generate **5–10 comments that sit exactly on the `hot_take`/`analysis`
boundary** (e.g. verdicts with one borderline supporting clause). If I can't
classify the generated comments cleanly with my current rules, the definitions
are too loose — I'll tighten §2/§3 *before* labeling more data, and re-run until
the generated edge cases resolve unambiguously under the rules.

### 7b. Annotation assistance (disclosure-critical)
**This already happened and must be disclosed:** all **204** comments in
`labeling_batch.json` were **pre-labeled by an LLM (Claude Opus, via Claude
Code)**, not hand-labeled from scratch. Plan going forward:
- Treat these as a **first pass requiring human review**, not ground truth.
- Add a `source` field (`ai_prelabel`) and a `reviewed` boolean to each row so
  reviewed-by-human examples are distinguishable from raw AI labels.
- The **human-verified subset** (§5/§6) becomes the gold test set; training labels
  may stay AI-assisted but the evaluation set may not.

### 7c. Failure analysis
After evaluation, export the **list of misclassified test comments** (with true
label, predicted label, text) and ask the LLM to **cluster them into error
patterns** — e.g. "model treats any comment with a stat as analysis," or "short
analysis comments get read as hot takes," or "ref-decision arguments confuse it."
Then **verify each proposed pattern by hand**: pull the actual comments in that
cluster, confirm the pattern is real and not an LLM confabulation, and only then
write it into the evaluation. The AI proposes; I confirm against the raw text.

---

## 8. AI usage disclosure (summary)

- **Label design:** structure proposed by AI from reading real comments; final
  boundary rules decided by me.
- **Annotation:** 204/204 comments AI pre-labeled (Claude Opus). **Not yet
  human-reviewed** — a spot-check is the required next step before these are
  trusted as ground truth.
- **Pipeline code** (clean/filter/label scripts in `data/`, `collect.py`):
  AI-generated.
- **Evaluation & failure analysis:** AI used as described in §7c, with all
  proposed patterns human-verified before reporting.

---

## 9. Pipeline (reproducible)

```
data/<match>.json           raw Reddit thread dump
  -> <match>_clean.json      all comments, {score, body}, sorted by score
  -> <match>_batch.json      substantive takes, labeled hot_take / analysis
labeling_batch.json          master: all batches combined, tagged with `match`
```
`collect.py` pulls fresh r/soccer comments via the no-auth Reddit JSON API for
adding more threads.
