import os
import re

def fix_metadata_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace model attribute 'metadata = Column(' with 'meta_data = Column(..., name="metadata")'
    # Handles cases like: metadata = Column(JSON), metadata = Column(String), etc.
    pattern = r'(\s*)metadata\s*=\s*Column\(([^)]*)\)'
    replacement = r'\1meta_data = Column(\2, name="metadata")'
    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        print(f"Fixed: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

def scan_and_fix(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                fix_metadata_in_file(os.path.join(root, file))

if __name__ == "__main__":
    scan_and_fix('app/models/')
