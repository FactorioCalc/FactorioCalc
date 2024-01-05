import re
import sys
from pathlib import Path

sys.path.insert(0, Path(__file__).parents[1].as_posix())
import factoriocalc

with open('guide0.md', 'r') as f:
    text = f.read()

text,n = re.subn(r'^---\n', '---\n# automatically generated file edit guide0.md instead\n', text)
if n != 1:
    raise RuntimeError("guide0.md does not start with '---'")
text = re.sub(r'(?<!\`)(\`[^`]+\`)', r'{py:obj}\1', text, flags = re.DOTALL)

text = re.sub(r'\{VERSION\}', factoriocalc.__version__, text)

sys.stdout.write(text)
