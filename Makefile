# Plain commands; see docs/running.md. Nothing here is required.
PY ?= python3

.PHONY: test validate secrets report site serve check

test:
	$(PY) -m unittest discover -s tests -v

validate:
	$(PY) -m decision_bench validate

secrets:
	$(PY) scripts/check_secrets.py

report:
	$(PY) -m decision_bench report

site:
	npm ci --prefix web && npm run build --prefix web

serve: report site
	$(PY) -m decision_bench serve

check: test validate secrets site
