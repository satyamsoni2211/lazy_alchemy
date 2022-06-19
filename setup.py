from pathlib import Path

from setuptools import setup, find_packages

from lazy_alchemy import version

here = Path(__file__).resolve().parent
README = (here / "README.md").read_text(encoding="utf-8")
PACKAGE_NAME = "lazy_alchemy"

setup(
    name=PACKAGE_NAME,
    version=version,
    license="MIT",
    packages=find_packages(exclude=["test"]),
    description="Lazy-Alchemy is a Python package that loads the DB models lazily.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Satyam Soni",
    author_email="satyamsoni@hotmail.co.uk",
    url="https://github.com/satyamsoni2211/lazy_alchemy",
    keywords=["sqlalchemy", "alchemy", "mysql", "postgres",
              "mssql", "sql", "sqlite", "lazy", "performance",
              "orm", "mapper", "performance", "database", "lazy",
              "relational", "classes", "oops", "metaclass"],
    install_requires=[
        "sqlalchemy",
    ],
    classifiers=[
        # See https://pypi.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    platforms=["any"],
    python_requires=">=3.6",
)
