"""
Packaging template for distributing a skill as an installable package.

Install locally:
    pip install -e .

This registers the skill as an entry point so the orchestrator
discovers it automatically — no need to copy files into plugins/.
"""
from setuptools import setup, find_packages

setup(
    name="orchestrator-skill-{{SKILL_SLUG}}",
    version="0.1.0",
    description="{{SKILL_DESCRIPTION}}",
    author="{{AUTHOR}}",
    py_modules=["{{SKILL_SLUG}}"],
    entry_points={
        "orchestrator.plugins": [
            "{{SKILL_NAME}} = {{SKILL_SLUG}}:register",
        ],
    },
    install_requires=[
        # Add any pip dependencies your skill needs here
    ],
)
