import os
import re
import sys
from subprocess import check_output, CalledProcessError

GIT_DESCRIBE_VERSION_REGEX = re.compile(
    r'''^
    # Version tags start with a 'v'
    v
    (?P<version>
        # Leading numbers
        [0-9]+
        # Match anything after this
        # (non-greedy in order to not capture the git info)
        .*?
    )
    # This block is optional: tagged revisions have no revision info.
    # Don't capture it all, we capture each component separately
    (?:
        -
        (?P<revision_info>
            # Number of commits since tag
            (?P<commit_count>[1-9][0-9]*)
            -
            # Git flag
            g
            # Abbreviated commit hash
            (?P<commit_hash>[0-9a-f]{7})
        )
    )?
    $''',
    re.VERBOSE)

PIP_EDITABLE_REQUIREMENT = re.compile(r'''
    ^-e
    \s
    (?P<link>
        (?P<vcs>git|svn|hg|bzr)
        .+
        \#egg=(?P<package>.+)
        (?:-(?P<version>\d(?:\.\d)*))?
    )
    $
''', re.VERBOSE)

HERE = os.path.dirname(__file__)


def read_file(filename):
    with open(filename) as fh:
        return fh.read().strip(' \t\n\r')


def read_requirements(filename):
    requirements = []
    for requirement in read_file(filename).splitlines():
        match = PIP_EDITABLE_REQUIREMENT.match(requirement)
        requirements.append(match.group('package') if match else requirement)
    return requirements


def get_git_info(pkg_dir):
    '''Get the software version from the git tags

    Returns 'None' if a version could not be found.
    Logs any problems with standard logging.
    '''

    pkg_dir = os.path.abspath(pkg_dir)
    try:
        git_dir = (
            check_output(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=pkg_dir)
        ).strip()
    except CalledProcessError as e:
        sys.stderr.write(
            'WARNING: Could not determine git repository root for {}: {}\n'
            .format(
                pkg_dir,
                e
            ))
        return

    if git_dir != pkg_dir:
        # This probably isn't the TNG git repo, perhaps someone has this file
        # somewhere within another git repository
        sys.stderr.write(
            'WARNING: Ignoring git tags for version info in {} because the '
            'repository root was not in the expected place.\n'
            .format(
                pkg_dir,
            ))
        return

    try:
        git_description = (
            check_output(
                ['git', 'describe', '--match=v[0-9].*'],
                cwd=git_dir)
        ).strip()
    except CalledProcessError as e:
        sys.stderr.write(
            'WARNING: Problem retrieving git version tag for repository at '
            '{}: {}'
            .format(
                git_dir,
                e
            ))
        return

    mo = GIT_DESCRIBE_VERSION_REGEX.match(git_description)

    if mo:
        return mo.groupdict()

    return


def get_git_version(declared_version):
    '''Get a modified package version to include git revision information
    '''
    git_info = get_git_info(HERE)

    if not git_info:
        return declared_version

    revision_info = git_info.get('revision_info', None)

    if revision_info:
        git_version = git_info['version']
        if declared_version == git_version:
            raise Exception(
                'Commits found since tag matching the current declared '
                'version. You may have forgotten to update the version '
                'number after tagging a release. Declared version: {}. '
                'Git version {}. Revision info: {}'
                .format(
                    declared_version,
                    git_version,
                    revision_info,
                ))
        return declared_version + '.dev' + revision_info
    else:
        return declared_version


def get_version(distribution):
    '''Get the current package version
    '''
    try:
        version = read_file('VERSION.txt').strip()
    except IOError:
        # There is no version file; this is probably not a source checkout
        # Assume that this was installed as a package

        import pkg_resources

        version = pkg_resources.get_distribution(distribution).version
    else:
        # Add git revision info to the version string
        version = get_git_version(version)

    return version
