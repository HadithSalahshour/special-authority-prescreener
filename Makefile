.PHONY: install run test check

install:
	python3 -m pip install -r requirements.txt

run:
	python3 run_local.py

test:
	python3 -m unittest discover -s tests

check:
	python3 -m ruff check .
	python3 -m unittest discover -s tests
