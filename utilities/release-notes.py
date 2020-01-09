#!/usr/bin/env python3

import subprocess
import sys

if len(sys.argv) < 2:
    print('Usage: ' + sys.argv[0] + ' <ReleaseNotesFilePath.md>')
    sys.exit(1)
output_file = sys.argv[1]

with open(output_file, 'w') as fp:
    tags = subprocess.check_output(['git', 'tag', '--sort=taggerdate']).decode('utf-8')
    recent_tags = tags.split()[-2:]
    previous_tag = recent_tags[0]
    current_tag = recent_tags[1]

    version = current_tag[1:]
    fp.write('# itkwidgets {0}\n\n'.format(version))

    fp.write('`itkwidgets` provides interactive Jupyter widgets to visualize images, point sets, and meshes in 3D or 2D.\n\n')

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
    subjects = subprocess.check_output(['git', 'log', '--pretty=%s',
        '--no-merges', '{0}..{1}'.format(previous_tag, current_tag)]).decode('utf-8')

    bug_fixes = []
    platform_fixes = []
    doc_updates = []
    enhancements = []
    performance_improvements = []
    style_changes = []
    for subject in subjects.split('\n'):
        prefix = subject.split(':')[0]
        if prefix == 'BUG':
            description = subject.split(':')[1]
            bug_fixes.append(description)
        elif prefix == 'COMP':
            description = subject.split(':')[1]
            platform_fixes.append(description)
        elif prefix == 'DOC':
            description = subject.split(':')[1]
            doc_updates.append(description)
        elif prefix == 'ENH':
            description = subject.split(':')[1]
            enhancements.append(description)
        elif prefix == 'PERF':
            description = subject.split(':')[1]
            performance_improvements.append(description)
        elif prefix == 'STYLE':
            description = subject.split(':')[1]
            style_changes.append(description)

    if enhancements:
        fp.write('\n### Enhancements\n\n')
        for subject in enhancements:
            if subject.find('Bump itkwidgets version for development') != -1:
                continue
            fp.write('- {0}\n'.format(subject))

    if performance_improvements:
        fp.write('\n### Performance Improvements\n\n')
        for subject in performance_improvements:
            fp.write('- {0}\n'.format(subject))

    if doc_updates:
        fp.write('\n### Documentation Updates\n\n')
        for subject in doc_updates:
            fp.write('- {0}\n'.format(subject))

    if platform_fixes:
        fp.write('\n### Platform Fixes\n\n')
        for subject in platform_fixes:
            fp.write('- {0}\n'.format(subject))

    if bug_fixes:
        fp.write('\n### Bug Fixes\n\n')
        for subject in bug_fixes:
            fp.write('- {0}\n'.format(subject))

    if style_changes:
        fp.write('\n### Style Changes\n\n')
        for subject in style_changes:
            fp.write('- {0}\n'.format(subject))
