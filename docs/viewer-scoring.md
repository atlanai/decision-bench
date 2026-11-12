# Input eligibility in the website

The frozen corpus and recorded predictions remain unchanged. The viewer excludes
DSN-1 icon rows when the recorded request has no images_sent. The text state for
these rows explicitly says the task cannot be answered without the image.

This policy is based on actual image delivery, not a model's brand or configured
vision capability. It applies to all models. Excluded answers do not count as
correct, incorrect, operational failures, confidence errors, or scored cost and
latency observations. They also do not enter row agreement counts, task verdicts,
heat maps or paired comparisons. Raw predictions stay available for audit.

Receipt OCR, chart values and extracted document text remain eligible: those
representations contain evidence for their tasks. Their modality differs from
image inputs; the viewer retains that distinction.

The website recomputes metrics over eligible rows and labels exclusions and
scored denominators. Historical downloadable scores and run metadata retain their
original unadjusted aggregates. The leaderboard ranks a model only in the views
where it was scored on every row, so a model with excluded rows is ranked on the
Text track and not on All inputs. The paired comparison uses the rows eligible
for both models, and its interval is calculated on those rows.

Jev's recorded run has 30 excluded icons, leaving 976 correct answers in 1,041
eligible cases (93.8%). This is a scoring correction, not a new model run.
