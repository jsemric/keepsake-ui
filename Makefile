.PHONY: test
test:
	@PYTHONPATH=. coverage run --omit keepsake_ui/main.py --source keepsake_ui -m pytest
	@coverage report

.PHONY: clean
clean:
	@rm -fr htmlcov .coverage .pytest_cache
