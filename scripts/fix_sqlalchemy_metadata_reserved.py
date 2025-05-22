import os
import re

# Configuration
MODEL_DIR = "app/models/"
PROJECT_DIR = "."  # Root of your project
OLD_ATTR = "metadata"
NEW_ATTR = "meta_info"  # Change as desired

def find_python_files(root):
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)

def replace_in_file(filepath, replacements):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    original = content

    for old, new in replacements:
        content = re.sub(old, new, content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated: {filepath}")

def scan_and_fix_models():
    # 1. Find all model files and lines with 'metadata = Column('
    model_files = list(find_python_files(MODEL_DIR))
    affected_files = []
    for file in model_files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        # Look for lines like: metadata = Column(
        if re.search(rf"\b{OLD_ATTR}\s*=\s*Column\(", content):
            affected_files.append(file)

    # 2. Rename attribute in model files, preserve DB column name
    for file in affected_files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        # Replace 'metadata = Column(' with 'meta_info = Column(..., name="metadata")'
        # Only add name="metadata" if not already present
        def repl(match):
            before = match.group(1)
            col_args = match.group(2)
            # If name="metadata" is already present, don't add it again
            if "name=\"metadata\"" in col_args or "name='metadata'" in col_args:
                return f"{before}{NEW_ATTR} = Column({col_args})"
            # Add name="metadata" as a kwarg
            if col_args.strip().endswith(","):
                new_args = f"{col_args} name=\"metadata\""
            elif col_args.strip():
                new_args = f"{col_args}, name=\"metadata\""
            else:
                new_args = "name=\"metadata\""
            return f"{before}{NEW_ATTR} = Column({new_args})"

        new_content = re.sub(
            rf"(^\s*){OLD_ATTR}\s*=\s*Column\((.*?)\)",
            repl,
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        if new_content != content:
            with open(file, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Refactored model attribute in: {file}")

    return affected_files

def update_usages_project_wide(affected_files):
    # 3. Update all usages of OLD_ATTR to NEW_ATTR across the project
    # We'll search for the old attribute name and replace with the new one,
    # but avoid changing unrelated 'metadata' (e.g., SQLAlchemy's MetaData)
    # We'll use a conservative regex: dot notation or attribute access
    usage_patterns = [
        (rf"\.{OLD_ATTR}\b", f".{NEW_ATTR}"),
        (rf"\b{OLD_ATTR}\b", NEW_ATTR),  # For kwargs, dict keys, etc.
    ]
    # Build a set of files to scan: all .py files in the project
    all_py_files = list(find_python_files(PROJECT_DIR))
    for file in all_py_files:
        # Don't re-edit model files already fixed above
        if file in affected_files:
            continue
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        original = content
        # Only replace if the file actually references the model attribute
        if re.search(rf"\.{OLD_ATTR}\b", content) or re.search(rf"\b{OLD_ATTR}\b", content):
            # Avoid changing SQLAlchemy's MetaData instantiations
            if "MetaData(" in content and "metadata =" in content:
                # Only replace attribute access, not MetaData objects
                content = re.sub(rf"\.(?<!MetaData\(){OLD_ATTR}\b", f".{NEW_ATTR}", content)
            else:
                for old, new in usage_patterns:
                    content = re.sub(old, new, content)
        if content != original:
            with open(file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated usages in: {file}")

def main():
    print("Scanning and fixing SQLAlchemy 'metadata' attribute usage...")
    affected_model_files = scan_and_fix_models()
    if not affected_model_files:
        print("No model files with 'metadata' attribute found. Nothing to fix.")
        return
    update_usages_project_wide(affected_model_files)
    print("\n✅ All 'metadata' attributes have been renamed to 'meta_info' and usages updated.")
    print("👉 Please review changes, run your tests (e.g., pytest), and verify your app.")

if __name__ == "__main__":
    main()
