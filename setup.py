#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="sia",
    version='1.0',
    description="new_order_check lib",
    author="huangyingjun",
    install_requires=[
        "SQLAlchemy",
        "mysql",
        "mysql-connector-python-rf",
        "MySQL-python",
        "tornado",
        "eventlet",
        "redis",
        "requests",
        "netaddr",
    ],

    scripts=[
        "bin/measure.py",
    ],

    packages=find_packages(),
    data_files=[
        ('/etc/new_ordercheck.conf', ['etc/new_ordercheck.conf']),
        ('/var/log/new_ordercheck.conf.log', []),
    ],
)
