# Makefile for automating steps
REQUIREMENTS_FILE=requirements.txt
DEV_REQUIREMENTS_FILE=dev_requirements.txt
build:
	pipenv requirements > ${REQUIREMENTS_FILE}
	pipenv requirements --dev > ${DEV_REQUIREMENTS_FILE}

setup: build
	echo "building"