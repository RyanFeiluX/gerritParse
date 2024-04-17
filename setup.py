#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time  : 2022/6/12 15:51
# @Author: Ryan Xiao
# @File  : setup.py
import os
from setuptools import setup, find_packages

BASE_PATH = os.path.dirname(__file__)

with open('README.txt', mode='r') as f:
    long_description = f.read()

setup(
    name='gerritParse',
    version='0.6.0',
    author='Ryan Xiao',
    author_email='ryan.007.xiao@hotmail.com',
    url='',
    description='This is a customized parser specific for code review information from gerrit.',
    long_description=long_description,
    packages=find_packages(where='.'),
    install_requires=[],
    python_requires=">=3.5",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
