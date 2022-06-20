# Makefile for automating steps
REQUIREMENTS_FILE=requirements.txt
DEV_REQUIREMENTS_FILE=dev_requirements.txt

# setting default to building distribution files
.DEFAULT_GOAL=build

dep:
	# building requirement files for dev and prd
	pipenv requirements > ${REQUIREMENTS_FILE}
	pipenv requirements --dev > ${DEV_REQUIREMENTS_FILE}

install: 
	@pip install -r ${DEV_REQUIREMENTS_FILE}

clean:
	@echo "cleaning stale builds and distributions"
	@rm -rf dist/ build/ *.egg-info htmlcov

test:
	@pytest

cov:
	coverage run -m pytest && coverage html && open htmlcov/index.html 

build: test clean
	@pip install build
	@echo "building distribution and wheel files"
	python setup.py sdist bdist_wheel

clean_build: install build

pypi: clean_build
	# building and releasing distribution to pypi
	# this can be run as is in the pipeline 
	@pip install twine
	@twine upload dist/* -u ${TWINE_USERNAME} -p ${TWINE_PASSWORD} --non-interactive --skip-existing --verbose
