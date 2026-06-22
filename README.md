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

## Results

| Model | Accuracy | Macro-F1 (approx.) | Notes |
|---|---|---|---|
| Zero-shot baseline (LLM prompt) | **0.758** | ~0.75 | catches analysis (recall 0.91) but over-predicts it (precision 0.59) |
| Fine-tuned DistilBERT | **0.667** | **~0.40** | predicts `hot_take` for every input — collapsed to the majority class |

**The fine-tuned model performed *worse* than the baseline (−0.091 accuracy).**

### Confusion matrix — fine-tuned model (test set, n=33)

| | Predicted: analysis | Predicted: hot_take |
|---|---|---|
| **Actual: analysis** | 0 | 11 |
| **Actual: hot_take** | 0 | 22 |

(`confusion_matrix.png` is the committed image version of this table.)

The matrix makes the failure unambiguous: the model predicted `hot_take` **33/33
times** and never once predicted `analysis`. Its 0.667 accuracy is *exactly* the
"always guess the majority class" rate — the model learned nothing useful about
the distinction.

## Why the fine-tuned model failed (honest analysis)

This is the classic **majority-class collapse** that happens when fine-tuning a
large model on a **small, imbalanced dataset**:

- Only **217 examples** total (~152 train), with a **67/33** class split.
- Predicting the majority class (`hot_take`) every time already yields ~67%
  training accuracy, which is a strong, easy local minimum.
- With so few `analysis` examples and no class weighting, 3 epochs of standard
  cross-entropy gave the model little reason to ever risk predicting the minority
  class. It minimized loss by ignoring the input.

Notably, the **zero-shot baseline did the opposite** — it *over*-predicted
`analysis`. So the two models fail in opposite directions, and neither has
actually learned the boundary defined in planning.md §2.

### Three wrong predictions (all `analysis` → `hot_take`)

Because the model labeled the entire `analysis` class wrong, the instructive point
is that it misses even **unambiguous, detail-rich** analysis — confirming it isn't
reading content at all:

1. **"They have a trainer who understands the German game and countered it
   perfectly... they stopped the Germans by marking man to man, it shut down a lot
   of Germany's playstyle."** (true: `analysis`, predicted: `hot_take`)
   A textbook tactical breakdown with an explicit mechanism (man-marking). If any
   comment is analysis, this is — yet the model still defaulted to `hot_take`.

2. **"Egypt's third goal was one of the worst defended corners I've ever seen.
   Trezeguet... was completely open and unmarked for like 5 seconds before the
   corner was taken."** (true: `analysis`, predicted: `hot_take`)
   A specific, checkable observation about a single defensive sequence — the exact
   "concrete reason" the analysis label is built on. Missed.

3. **"if you swap the goalies only the game is probably 3-2... xG and shots says it
   was a lot closer than this. Most of their chances ended in goals."** (true:
   `analysis`, predicted: `hot_take`)
   Statistical reasoning (xG, shot conversion) plus a counterfactual. Missed.

These aren't subtle boundary errors — they're complete failures to engage, which
is the signature of majority-class collapse rather than a genuine misread.

## Hypothesis revisited

My pre-fine-tuning hypothesis (planning.md / baseline reflection) predicted that
fine-tuning would *raise* `hot_take` recall and push `analysis` precision over
0.65. **This was refuted.** The model didn't learn a sharper boundary — it
abandoned the minority class entirely. The root cause is dataset size and
imbalance, not the label definitions.

**What I'd change to fix it (future work):** class weights or oversampling the
`analysis` class, a lower learning rate / fewer epochs to avoid overfitting to the
majority prior, and collecting more `analysis` examples to push the split closer
to 50/50.
