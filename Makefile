# Plain commands; see docs/running.md. Nothing here is required.
PY ?= python3

.PHONY: test validate secrets report serve check

test:
	$(PY) -m unittest discover -s tests -v

validate:
	$(PY) -m decision_bench validate

secrets:
	$(PY) scripts/check_secrets.py

report:
	$(PY) -m decision_bench report

serve: report
	$(PY) -m decision_bench serve

check: test validate secrets
	node --check site/app.js
