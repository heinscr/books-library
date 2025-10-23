#!/usr/bin/env python3
"""
Refactor frontend/styles.css into modular component-based architecture
Splits 851 lines into organized component files
"""

import os
import re

FRONTEND_DIR = "/home/craig/projects/books/frontend"
CSS_DIR = os.path.join(FRONTEND_DIR, "css")

# Read the original styles.css
with open(os.path.join(FRONTEND_DIR, "styles.css"), 'r') as f:
    original_css = f.read()

# Create backup
with open(os.path.join(FRONTEND_DIR, "styles.css.backup"), 'w') as f:
    f.write(original_css)

print("✓ Created styles.css.backup")

# Define sections with their patterns (order matters - more specific first)
sections = {
    'base.css': [
        r'^\*\s*{',
        r'^body\s*{',
        r'^html\s*{',
        r'^:root\s*{'
    ],
    'header.css': [
        r'\.header\b',
        r'\.auth-widget\b',
        r'\.login-',
        r'\.user-avatar\b',
        r'\.user-menu\b',
        r'\.menu-',
        r'\.avatar-'
    ],
    'layout.css': [
        r'\.container\b',
        r'\.controls-row\b',
        r'\.filter-controls\b',
        r'\.stacked-controls\b'
    ],
    'alerts.css': [
        r'\.alert\b',
        r'\.loading\b',
        r'\.spinner\b'
    ],
    'cards.css': [
        r'\.books-grid\b',
        r'\.book-card\b',
        r'\.book-header\b',
        r'\.book-author\b',
        r'\.book-meta\b',
        r'\.book-download\b',
        r'\.book-series\b',
        r'\.read-toggle\b',
        r'\.empty-state\b',
        r'\.author-section\b',
        r'\.author-header\b',
        r'\.author-books\b'
    ],
    'modals.css': [
        r'\.modal\b',
        r'\.close\b'
    ],
    'buttons.css': [
        r'\.btn-',
        r'\.fab-upload\b',
        r'\.checkbox-'
    ],
    'forms.css': [
        r'\.form-group\b',
        r'\.field-hint\b',
        r'\.file-info\b',
        r'\.progress-',
        r'\.detail-',
        r'\.upload-',
        r'input\[type=',
        r'^select\b',
        r'^textarea\b',
        r'^label\b'
    ]
}

# Initialize content storage
section_content = {name: [] for name in sections.keys()}
section_content['uncategorized.css'] = []

# Parse CSS into blocks (handle multi-line blocks properly)
def extract_css_blocks(css_text):
    """Extract CSS blocks with their comments"""
    blocks = []
    lines = css_text.split('\n')
    current_block_lines = []
    in_block = False
    in_comment = False
    brace_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Track multi-line comments
        if '/*' in line and '*/' not in line:
            in_comment = True
        if '*/' in line:
            in_comment = False

        # Skip empty lines between blocks
        if not line.strip() and not in_block and not current_block_lines:
            i += 1
            continue

        # Start collecting lines for a block (including preceding comments)
        if line.strip() and (line.strip().startswith('/*') or in_comment or in_block or brace_count > 0):
            current_block_lines.append(line)
        elif line.strip() and not in_block:
            # This is a selector line
            current_block_lines.append(line)
            in_block = True
        elif current_block_lines:
            current_block_lines.append(line)

        # Track braces
        brace_count += line.count('{') - line.count('}')

        # End of block
        if in_block and brace_count == 0 and '{' in '\n'.join(current_block_lines):
            blocks.append('\n'.join(current_block_lines))
            current_block_lines = []
            in_block = False

        i += 1

    return blocks

# Extract all blocks
css_blocks = extract_css_blocks(original_css)

print(f"✓ Extracted {len(css_blocks)} CSS blocks")

# Categorize each block
for block in css_blocks:
    categorized = False

    # Try to match against patterns
    for section_name, patterns in sections.items():
        for pattern in patterns:
            if re.search(pattern, block, re.MULTILINE):
                section_content[section_name].append(block)
                categorized = True
                break
        if categorized:
            break

    # If no match, add to uncategorized
    if not categorized:
        section_content['uncategorized.css'].append(block)

# Create css directory
os.makedirs(CSS_DIR, exist_ok=True)

# Write each section to its own file
files_created = []
for section_name, blocks in section_content.items():
    if blocks:
        section_path = os.path.join(CSS_DIR, section_name)
        with open(section_path, 'w') as f:
            f.write('\n\n'.join(blocks))
        print(f"✓ Created {section_name} ({len(blocks)} blocks)")
        files_created.append(section_name)

# Create main.css that imports all modules in the right order
import_order = ['base.css', 'header.css', 'layout.css', 'alerts.css',
                'cards.css', 'modals.css', 'buttons.css', 'forms.css', 'uncategorized.css']

main_css_content = '/* Books Library Styles - Modular Architecture */\n\n'
for filename in import_order:
    if filename in files_created:
        main_css_content += f"@import '{filename}';\n"

with open(os.path.join(CSS_DIR, "main.css"), 'w') as f:
    f.write(main_css_content)

print("✓ Created main.css (imports all modules)")

# Create new minimal styles.css that just imports from css/
new_styles_content = '''/* Books Library Styles */
/* Import modular CSS from css/ directory */
@import 'css/main.css';
'''

with open(os.path.join(FRONTEND_DIR, "styles.css"), 'w') as f:
    f.write(new_styles_content)

print("✓ Created new minimal styles.css")
print(f"\n✅ CSS refactoring complete!")
print(f"  Original: 851 lines → Now split into {len(files_created)} files")
print(f"  Backup saved as: styles.css.backup")
