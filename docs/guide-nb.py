import re
import sys
import base64
from pathlib import Path

import nbformat
from myst_nb.core.read import read_myst_markdown_notebook

with open('guide0.md', 'r') as f:
    text = f.read()

text,n = re.subn(r'^---\n', '---\n# automatically generated file edit guide0.md instead\n', text)
if n != 1:
    raise RuntimeError("guide0.md does not start with '---'")

# remove any eval-rst directoves
text = re.sub(r'```\{eval-rst\}.+?\n```', r'', text, flags = re.DOTALL)

# `~package.symbol` => `symbol`
text = re.sub(r'(?<!\`)`~.+?\.([^`.]+)\`', r'`\g<1>`', text)

# (target)= => <a name="target"></a>
text = re.sub(r'^\((.+)\)\=', '<a name="\g<1>"></a>', text, flags = re.MULTILINE)

# pad all headings with '+++' so that they are in there own markdown cell
text = re.sub(r'\n\n(\#.+)\n\n','\n\n+++\n\n\g<1>\n\n+++\n\n', text)

baseUrl = 'https://factoriocalc.readthedocs.io/en/devel'
referenceUrl = f'{baseUrl}/reference.html'
text = re.sub(r'\[(.+?)\]\(reference\.rst(.*?)\)', f'[\g<1>]({referenceUrl}\g<2>)', text)

# convert myst markdown file to notebook

nb = read_myst_markdown_notebook(text)
nb.nbformat_minor = 0

cells = []

for cell in nb.cells:
    if 'remove-cell' in cell.metadata.get('tags', []):
        continue
    del cell['id']
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

    # inline images as attachments
    
nb.cells = cells

nbformat.validate(nb)

nbformat.write(nb, sys.stdout)
