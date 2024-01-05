import sys
import os
from pathlib import Path
import nbformat

sys.path.insert(0, Path(__file__).parents[1].as_posix())
import factoriocalc

lab_environment = f'''
# automatically generated file, see demo-prep.py
name: xeus-python-kernel
channels:
  - https://repo.mamba.pm/emscripten-forge
  - https://repo.mamba.pm/conda-forge
dependencies:
  - pip:
    - factoriocalc-{factoriocalc.__version__}-py3-none-any.whl
'''

with open('_jl/environment.yml', 'w') as f:
    f.write(lab_environment)

with open('docs/guide-nb.ipynb') as f:
    nb = nbformat.read(f, 4)

nb.metadata.kernelspec = {
    'name': 'xeus-python',
    'display_name': 'Python (XPython)',
    'language': 'python'
}

intro_p2 = \
f"""This is the Jupyter notebook version of the guide for use with
JupyterLite and the xeus-python kernel.  It was written for version 
{factoriocalc.__version__} of FactorioCalc.
"""

cells = []
for cell in nb.cells:
    if '_intro_p2' in cell.metadata.get('tags', []):
        if cell.cell_type == 'markdown':
            cell.source = intro_p2
        else:
            continue
    cells.append(cell)
    
nb.cells = cells

with open(f'_jl/files/guide-{factoriocalc.__version__}.ipynb', 'w') as f:
    nbformat.write(nb, f)
