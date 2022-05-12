# -*- coding: utf-8 -*-
import os

from setuptools import find_packages
from setuptools import setup


base_dir = os.path.dirname(__file__)
setup(
    name='ito-snapmanager',
    version='0.0.1',
    description='Managing snapshots of OpenStack VMs on Ceph RBD images.',
    author='nubium',
    author_email='provoz@nubium.cz',
    setup_requires='setuptools',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
    ],
    scripts=['snapmanager/snapmanager.py'],
    packages=find_packages(),
    include_package_data=True,
)
