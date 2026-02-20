pytest:
	pip install -r tests/requirements.txt
	pytest tests/ -v

pytest-unit:
	pytest tests/unit/ -v

pytest-integration:
	pytest tests/integration/ -v

pytest-coverage:
	pytest tests/ --cov=api/gateway_api --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

pytest-fast:
	pytest tests/ -v --tb=short

pytest-verbose:
	pytest tests/ -vv -s

pytest-specific:
	pytest tests/unit/test_security.py -v

pytest-watch:
	pytest-watch tests/ -v

pytest-debug:
	pytest tests/ -v --pdb

.PHONY: pytest pytest-unit pytest-integration pytest-coverage pytest-fast pytest-verbose pytest-specific pytest-watch pytest-debug
