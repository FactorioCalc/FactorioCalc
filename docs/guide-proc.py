import re
import sys

with open('guide0.md', 'r') as f:
    text = f.read()

text,n = re.subn(r'^---\n', '---\n# automatically generated file edit guide0.md instead\n', text)
if n != 1:
    raise RuntimeError("guide0.md does not start with '---'")
text = re.sub(r'(?<!\`)(\`[^`]+\`)', r'{py:obj}\1', text, flags = re.DOTALL)

sys.stdout.write(text)
