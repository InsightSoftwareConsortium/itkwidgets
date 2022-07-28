#!/usr/bin/env python3

import subprocess
import sys

if len(sys.argv) < 2:
    print('Usage: ' + sys.argv[0] + ' <ReleaseNotesFilePath.md>')
    sys.exit(1)
output_file = sys.argv[1]

with open(output_file, 'w') as fp:
    tags = subprocess.check_output(['git', 'tag', '--sort=creatordate']).decode('utf-8')
    recent_tags = tags.split()[-2:]
    previous_tag = recent_tags[0]
    current_tag = recent_tags[1]

    version = current_tag[1:]
    fp.write('# itkwidgets {0}\n\n'.format(version))

    fp.write('`itkwidgets` provides interactive widgets to visualize images, point sets, and 3D geometry on the web.\n\n')

    fp.write('## Installation\n\n')
    fp.write('```\n')
    fp.write('pip install itkwidgets\n')
    fp.write('```\n')
    fp.write('or\n')
    fp.write('```\n')
    fp.write('conda install -c conda-forge itkwidgets\n')
    fp.write('```\n')
    fp.write('\n')

    fp.write('## Changes from {0} to {1}\n'.format(previous_tag, current_tag))
    subjects = subprocess.check_output(['git', 'log', '--pretty=%s:%h',
        '--no-merges', '{0}..{1}'.format(previous_tag, current_tag)]).decode('utf-8')

    bug_fixes = []
    platform_fixes = []
    doc_updates = []
    enhancements = []
    performance_improvements = []
    style_changes = []
    for subject in subjects.split('\n'):
        prefix = subject.split(':')[0]
        commit = subject.split(':')[-1]
        if prefix == 'BUG':
            description = subject.split(':')[1]
            bug_fixes.append((description, commit))
        elif prefix == 'COMP':
            description = subject.split(':')[1]
            platform_fixes.append((description, commit))
        elif prefix == 'DOC':
            description = subject.split(':')[1]
            doc_updates.append((description, commit))
        elif prefix == 'ENH':
            description = subject.split(':')[1]
            enhancements.append((description, commit))
        elif prefix == 'PERF':
            description = subject.split(':')[1]
            performance_improvements.append((description, commit))
        elif prefix == 'STYLE':
            description = subject.split(':')[1]
            style_changes.append((description, commit))

    commit_link_prefix = 'https://github.com/InsightSoftwareConsortium/itkwidgets/commit/'

    if enhancements:
        fp.write('\n### Enhancements\n\n')
        for subject, commit in enhancements:
            if subject.find('Bump itkwidgets version for development') != -1:
                continue
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))

    if performance_improvements:
        fp.write('\n### Performance Improvements\n\n')
        for subject, commit in performance_improvements:
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))

    if doc_updates:
        fp.write('\n### Documentation Updates\n\n')
        for subject, commit in doc_updates:
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))

    if platform_fixes:
        fp.write('\n### Platform Fixes\n\n')
        for subject, commit in platform_fixes:
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))

    if bug_fixes:
        fp.write('\n### Bug Fixes\n\n')
        for subject, commit in bug_fixes:
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))

    if style_changes:
        fp.write('\n### Style Changes\n\n')
        for subject, commit in style_changes:
            fp.write('- {0}'.format(subject))
            fp.write(' ([{0}]({1}{0}))\n'.format(commit, commit_link_prefix))
