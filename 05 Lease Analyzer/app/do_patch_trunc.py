path = r'C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\app\summary_generator.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Restore evaluator reasoning to 200 chars (was changed to 120)
old = "                        if len(short_reason) > 120:\n                            short_reason = short_reason[:117] + \"...\""
new = "                        if len(short_reason) > 200:\n                            short_reason = short_reason[:197] + \"...\""

if old in content:
    content = content.replace(old, new, 1)
    print('Evaluator reasoning restored to 200 chars')
else:
    print('Already at 200 or not found')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done.')
