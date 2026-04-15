#!/usr/bin/env python3
import os
import glob

# Read the handoff files
handoff_dir = r"C:\Users\Owner\OneDrive\HeartSync\.agents\handoffs"
state_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\STATE.md"
board_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\BOARD.md"
protocol_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\PROTOCOL.md"
claude_file = r"C:\Users\Owner\OneDrive\HeartSync\CLAUDE.md"

results = []

# List handoff files
if os.path.exists(handoff_dir):
    handoff_files = sorted(glob.glob(os.path.join(handoff_dir, "*.md")))
    results.append(f"Found {len(handoff_files)} handoff files\n")
    
    # Read each handoff file
    for hf in handoff_files:
        try:
            with open(hf, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                fname = os.path.basename(hf)
                results.append(f"\n\n=== {fname} ===\n{content}\n")
        except Exception as e:
            results.append(f"Error reading {hf}: {e}\n")

# Read state file
if os.path.exists(state_file):
    try:
        with open(state_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            results.append(f"\n\n=== STATE.md ===\n{content}\n")
    except Exception as e:
        results.append(f"Error reading STATE.md: {e}\n")

# Read board file
if os.path.exists(board_file):
    try:
        with open(board_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            results.append(f"\n\n=== BOARD.md ===\n{content}\n")
    except Exception as e:
        results.append(f"Error reading BOARD.md: {e}\n")

# Read protocol file
if os.path.exists(protocol_file):
    try:
        with open(protocol_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            results.append(f"\n\n=== PROTOCOL.md ===\n{content}\n")
    except Exception as e:
        results.append(f"Error reading PROTOCOL.md: {e}\n")

# Read CLAUDE.md
if os.path.exists(claude_file):
    try:
        with open(claude_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            results.append(f"\n\n=== CLAUDE.md ===\n{content}\n")
    except Exception as e:
        results.append(f"Error reading CLAUDE.md: {e}\n")

# Write results to output file
output_file = r"C:\Users\Owner\OneDrive\CAM\heartsync_analysis.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(''.join(results))

print(f"Analysis written to {output_file}")
