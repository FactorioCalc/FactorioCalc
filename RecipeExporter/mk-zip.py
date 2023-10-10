#!/usr/bin/python3

import json
from shutil import copytree, ignore_patterns
import subprocess

with open('RecipeExporter/info.json') as f:
  j = json.load(f)

version = j['version']

copytree('RecipeExporter', f'RecipeExporter_{version}',
         ignore=ignore_patterns('*~', '#*', 'mk-zip.py'))

subprocess.run(['zip', '-9r', f'RecipeExporter_{version}.zip',  f'RecipeExporter_{version}'],
               check=True)
