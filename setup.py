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
    include_package_data=True,
    description="Lazy-load SQLAlchemy table metadata on demand, with full SA2, async, and Pydantic support.",
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
        "sqlalchemy>=2.0.14,<2.1.0",
        "pydantic>=2.0,<3.0",
        "sqlmodel>=0.0.16,<1.0",
        "greenlet",
    ],
    extras_require={
        "dev": [
            "pytest>=7",
            "pytest-asyncio",
            "aiosqlite",
            "mypy",
            "ruff",
            "coverage",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    platforms=["any"],
    python_requires=">=3.10",
)