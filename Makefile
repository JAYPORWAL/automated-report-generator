.PHONY: install install-dev lint format test run docker-build docker-run clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format --check .

format-fix:
	ruff format .
	ruff check --fix .

test:
	pytest -v --cov=src --cov-report=term-missing --cov-fail-under=75

run:
	streamlit run app.py

docker-build:
	docker build -t automated-report-generator .

docker-run:
	docker run -p 8501:8501 --env-file .env automated-report-generator

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -r {} +
