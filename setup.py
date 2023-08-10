#!/usr/bin/env python

from setuptools import find_packages, setup

with open("README.md", "r") as fs:
    long_description = fs.read()

setup(
    name="pynanomapper",
    version="1.2.0-beta",
    author="Nina JELIAZKOVA",
    author_email="jeliazkova.nina@gmail.com",
    description="eNanoMapper API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ideaconsult/pynanomapper",
    project_urls={
        "Issue tracker": "https://github.com/ideaconsult/pynanomapper/issues",
    },
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="enanomapper nanoinformatics cheminformatics ambit",
    python_requires="~=3.5",
    packages=find_packages(),
    install_requires=[
        "jproperties",
        "nexusformat",
        "pandas",
        "pyyaml >= 5.1",
        "requests",
    ],
)
