import ast
with open("ui.py", encoding="utf-8") as f:
    source = f.read()
ast.parse(source)
print(f"Syntax OK - {len(source)} chars, {source.count(chr(10))+1} lines")
