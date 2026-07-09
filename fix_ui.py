with open("ui.py", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print(f"Line 271 (1-indexed): {repr(lines[270])}")
print(f"Line 271 indent: {repr(lines[270][:len(lines[270])-len(lines[270].lstrip())])}")

# Check what's around line 270-272
for i in range(268, min(273, len(lines))):
    print(f"  Line {i+1}: {repr(lines[i][:100])}")