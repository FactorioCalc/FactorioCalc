import sys
from sys import stdout,stderr

with open('../README.rst', 'r') as f:
    lines = f.readlines()
    i = 0
    while i < len(lines) and not lines[i].startswith('==='):
        i += 1
    i += 1
    while i < len(lines) and not lines[i].startswith('Read the docs'):
        stdout.write(lines[i])
        i += 1
    if i >= len(lines):
        stderr.write('ERROR: Failed to correctly extract description text from README\n')
        sys.exit(1)



