import os
import re
import versioneer
from distutils.command.sdist import sdist as _sdist
from setuptools import setup, find_packages

versioneer.versionfile_source = 'async/_version.py'
versioneer.versionfile_build = 'async/_version.py'
versioneer.tag_prefix = 'v'
versioneer.parentdir_prefix = 'gevent_async-'

HERE = os.path.dirname(__file__)


def read_file(filename):
    with open(os.path.join(HERE, filename)) as fh:
        return fh.read().strip(' \t\n\r')


def read_requirements(filename):
    return read_file(filename).splitlines()


def pep440_version(versioneer_version):
    parts = re.match(
        '(?P<number>[0-9.]+)'
        '(?:-(?P<distance>[1-9][0-9]*))?'
        '(?:-(?P<revision>g[0-9a-f]{7}))?'
        '(?:-(?P<dirty>dirty))?', versioneer_version
        ).groupdict()
    version = parts['number']
    if parts['distance']:
        version += '.post0.dev' + parts['distance']
    elif parts['dirty']:
        # If we're building from a dirty tree, make sure that
        # this is flagged as a dev version
        version += '.post0.dev0'

    return version


# Need this part to ensure the published version uses the pep440 version
class cmd_sdist(versioneer.cmd_sdist):
    def run(self):
        versions = versioneer.get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = pep440_version(
            versions["version"])
        return _sdist.run(self)


cmdclass = versioneer.get_cmdclass()
cmdclass['sdist'] = cmd_sdist

README = read_file("README.rst")

setup(
    name='gevent_async',
    version=pep440_version(versioneer.get_version()),
    cmdclass=cmdclass,
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
