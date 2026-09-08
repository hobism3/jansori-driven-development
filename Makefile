# Jansori — build / run / seed / verify harness (U4 · CMP-13).
#
# Targets:
#   make install  - install the server + dev deps (pytest, hypothesis, httpx)
#   make run      - start the loopback server on an EMPTY in-memory store (127.0.0.1:8765)
#   make seed     - populate a RUNNING server from fixtures/seed/*.json (generic, DEV-38)
#   make verify   - real-server contract suite (boots/tears down a real server; US-17)
#   make pbt      - property-based tests (Hypothesis; PBT-01..10)
#   make test     - full test suite (unit + pbt + golden + verify)
#
# Windows note: these use a POSIX-style recipe. If GNU Make is unavailable, run the
# underlying command shown in each recipe directly (e.g. `python -m server.app.main`).
# Override the interpreter with `make run PY=python3`.

PY ?= python

.PHONY: install run seed verify pbt test

install:
	$(PY) -m pip install -e ".[dev]"

run:
	$(PY) -m server.app.main

seed:
	$(PY) scripts/seed.py

verify:
	$(PY) -m pytest tests/verify -q

pbt:
	$(PY) -m pytest tests/pbt -q

test:
	$(PY) -m pytest tests -q
