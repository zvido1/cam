#!/usr/bin/env python3
import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Paths
handoff_dir = r"C:\Users\Owner\OneDrive\HeartSync\.agents\handoffs"
state_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\STATE.md"
board_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\BOARD.md"
protocol_file = r"C:\Users\Owner\OneDrive\HeartSync\.agents\PROTOCOL.md"
claude_file = r"C:\Users\Owner\OneDrive\HeartSync\CLAUDE.md"
output_file = r"C:\Users\Owner\OneDrive\CAM\heartsync_content.txt"

all_content = []

# Helper function to safely read files
def read_file(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    except Exception as e:
        return f"Error reading {path}: {e}"
    return None

# Read all files
print("Reading CLAUDE.md...")
claude_content = read_file(claude_file)
if claude_content:
    all_content.append(f"=== CLAUDE.md ===\n{claude_content}\n\n")

print("Reading STATE.md...")
state_content = read_file(state_file)
if state_content:
    all_content.append(f"=== STATE.md ===\n{state_content}\n\n")

print("Reading BOARD.md...")
board_content = read_file(board_file)
if board_content:
    all_content.append(f"=== BOARD.md ===\n{board_content}\n\n")

print("Reading PROTOCOL.md...")
protocol_content = read_file(protocol_file)
if protocol_content:
    all_content.append(f"=== PROTOCOL.md ===\n{protocol_content}\n\n")

print("Reading handoff files...")
if os.path.exists(handoff_dir):
    handoff_files = sorted(glob.glob(os.path.join(handoff_dir, "*.md")))
    print(f"Found {len(handoff_files)} handoff files")
    for hf in handoff_files:
        fname = os.path.basename(hf)
        content = read_file(hf)
        if content:
            all_content.append(f"=== {fname} ===\n{content}\n\n")
else:
    print(f"Handoff directory not found: {handoff_dir}")

# Write to output
print(f"Writing to {output_file}...")
with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
    f.write(''.join(all_content))

print("Done!")
