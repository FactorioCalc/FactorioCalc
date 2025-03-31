import re
import sys
import os
import base64
from pathlib import Path

import nbformat
from myst_nb.core.read import read_myst_markdown_notebook

sys.path.insert(0, Path(__file__).parents[1].as_posix())
import factoriocalc

readthedocs_version = os.environ.get('READTHEDOCS_VERSION', 'devel')

with open('guide0.md', 'r') as f:
    text = f.read()

text,n = re.subn(r'^---\n', '---\n# automatically generated file edit guide0.md instead\n', text)
if n != 1:
    raise RuntimeError("guide0.md does not start with '---'")

# remove any eval-rst directoves
text = re.sub(r'```\{eval-rst\}.+?\n```', r'', text, flags = re.DOTALL)

# `~package.symbol` => `symbol`
text = re.sub(r'(?<!\`)`~.+?\.([^`.]+)\`', r'`\g<1>`', text)

baseUrl = f'https://factoriocalc.readthedocs.io/en/{readthedocs_version}'
referenceUrl = f'{baseUrl}/reference.html'
text = re.sub(r'\[(.+?)\]\(reference\.rst(.*?)\)', fr'[\g<1>]({referenceUrl}\g<2>)', text)

# pad all headings with '+++' so that they are in there own markdown cell
text = re.sub(r'\n\n(\(.+?\)=\n)?(\#.+)\n\n',r'\n\n+++\n\n\g<1>\g<2>\n\n+++\n\n', text)
n = 1
while n > 0:
    text,n = re.subn(r'\+\+\+\n\n(\(.+?\)=\n)?(\#.+)\n\n(?!\+\+\+)',r'+++\n\n\g<1>\g<2>\n\n+++\n\n', text)


# (target)= => <a name="target"></a>
text = re.sub(r'^\((.+)\)\=', r'<a name="\g<1>"></a>', text, flags = re.MULTILINE)

# convert myst markdown file to notebook

nb = read_myst_markdown_notebook(text)
nb.nbformat_minor = 0

intro_p2 = \
f"""This is the Jupyter notebook version of the guide for version
{factoriocalc.__version__} of FactorioCalc.  If FactorioCalc is not
already available in your Python environment uncomment the line below to
install it:
"""

intro_p2_code = f"#%pip install factoriocalc=={factoriocalc.__version__}"

cells = []
for cell in nb.cells:
    del cell['id']
    if 'remove-cell' in cell.metadata.get('tags', []):
        continue
    if '_intro_p2' in cell.metadata.get('tags', []):
        cell.source = intro_p2
        cells.append(cell)
        cell = nbformat.v4.new_code_cell(source=intro_p2_code)
        del cell['id']
        cell.metadata['tags'] = ['_intro_p2']
        cells.append(cell)
        continue
    if cell.cell_type == 'markdown':
        images = []
        def handle_image(m):
            fn = Path(m[2]).with_suffix('.jpg')
            with open(fn, 'rb') as image:
                encoded = base64.b64encode(image.read()).decode()
            return f'![{m[1]}](data:image/jpeg;base64,{encoded})'
        cell.source = re.sub(r'\!\[(.+?)\]\((.+?)\)', handle_image, cell.source)
        attachments = {}
    cells.append(cell)

nb.cells = cells

nbformat.validate(nb)

nbformat.write(nb, sys.stdout)
