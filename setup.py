from setuptools import setup, find_packages

from util import get_version, read_requirements, read_file


NAME = 'gevent_async'
VERSION = get_version(NAME)
README = read_file("README.rst")
CHANGES = ''


setup(
    name=NAME,
    version=VERSION,
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities"
    ],
    author='Olivier Carrere',
    description=('A small set of utilities to help with writing synchronous'
                 'code flows in a collaborative multitasking context.'),
    author_email='olivier.carrere@gmail.com',
    url='http://github.com/kapouille/gevent_async',
    keywords='gevent state asychronous synchronous',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'test': read_requirements('requirements-test.txt'),
    },
)
