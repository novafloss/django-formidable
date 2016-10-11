# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

setup(
    name='django-formidable',
    version='0.4.0.dev0',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='django-formidable is a full django application which '
                'allows you to create, edit, delete and use forms.',
    long_description=README,
    url='https://github.com/novafloss/django-formidable',
    author='Guillaume Camera, Guillaume Gérard',
    author_email='guillaume.camera@people-doc.com, '
                 'guillaume.gerard@people-doc.com',
    install_requires=[
        'Django<1.9',
        'djangorestframework',
        'markdown',
        'python-dateutil',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
