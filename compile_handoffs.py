#!/usr/bin/env python3
import os
import glob

handoff_dir = r"C:\Users\Owner\OneDrive\HeartSync\.agents\handoffs"
output_file = r"C:\Users\Owner\OneDrive\CAM\all_handoffs_combined.txt"

# Read all handoff files
all_content = []

if os.path.exists(handoff_dir):
    handoff_files = sorted(glob.glob(os.path.join(handoff_dir, "*.md")))
    print(f"Found {len(handoff_files)} handoff files")
    
    for hf in handoff_files:
        fname = os.path.basename(hf)
        try:
            with open(hf, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                all_content.append(f"\n\n{'='*80}\n{fname}\n{'='*80}\n{content}")
        except Exception as e:
            print(f"Error reading {fname}: {e}")

# Write combined file
with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
    for text in all_content:
        f.write(text)

print(f"Wrote {len(all_content)} handoffs to {output_file}")
