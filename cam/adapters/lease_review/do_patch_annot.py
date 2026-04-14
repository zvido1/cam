import re

path = r'C:\Users\Owner\OneDrive\CAM\cam\adapters\lease_review\lease_pdf_annotator.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Add markdown stripping to _format_annotation_text
old = "    return \"\\n\".join(line for line in lines if line is not None)"
new = """    result = "\\n".join(line for line in lines if line is not None)
    # Strip markdown bold/italic markers
    result = re.sub(r'\\*\\*(.+?)\\*\\*', r'\\1', result)
    result = re.sub(r'\\*(.+?)\\*', r'\\1', result)
    return result"""

if old in content:
    content = content.replace(old, new, 1)
    # Make sure re is imported
    if 'import re' not in content[:300]:
        content = 'import re\n' + content
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed: markdown stripping added to PDF annotator')
else:
    print('ERROR: anchor not found')
