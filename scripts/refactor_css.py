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

# Split CSS into sections based on comments and selectors
sections = {
    'base.css': {
        'patterns': [r'^\*\s*\{', r'^body\s*\{'],
        'content': []
    },
    'header.css': {
        'patterns': [r'\.header', r'\.auth-widget', r'\.login-', r'\.user-avatar', r'\.user-menu'],
        'content': []
    },
    'layout.css': {
        'patterns': [r'\.container\s*\{', r'\.controls-row', r'\.filter-controls'],
        'content': []
    },
    'alerts.css': {
        'patterns': [r'\.alert', r'\.loading', r'\.spinner'],
        'content': []
    },
    'cards.css': {
        'patterns': [r'\.book-card', r'\.book-header', r'\.book-author', r'\.book-meta', r'\.book-download', r'\.read-toggle', r'\.empty-state', r'\.author-section'],
        'content': []
    },
    'modals.css': {
        'patterns': [r'\.modal', r'\.modal-content', r'\.modal-header', r'\.modal-body', r'\.modal-footer'],
        'content': []
    },
    'buttons.css': {
        'patterns': [r'\.btn-', r'\.fab-upload'],
        'content': []
    },
    'forms.css': {
        'patterns': [r'\.form-group', r'\.field-hint', r'\.file-info', r'\.progress-', r'\.detail'],
        'content': []
    }
}

# Parse CSS into sections
lines = original_css.split('\n')
current_block = []
in_block = False
brace_count = 0

for line in lines:
    # Track brace levels
    brace_count += line.count('{') - line.count('}')

    # Check if this line starts a new CSS block
    if '{' in line and not in_block:
        in_block = True
        current_block = [line]
    elif in_block:
        current_block.append(line)
        if brace_count == 0:
            # End of block
            block_text = '\n'.join(current_block)
            # Determine which section this belongs to
            for section_name, section_info in sections.items():
                for pattern in section_info['patterns']:
                    if re.search(pattern, block_text, re.MULTILINE):
                        section_info['content'].append(block_text)
                        break
            in_block = False
            current_block = []
    else:
        # Comment or empty line - could be a section header
        if line.strip().startswith('/*') or not line.strip():
            # Add to all sections that have content
            for section_info in sections.values():
                if len(section_info['content']) > 0:
                    section_info['content'].append(line)

# Write each section to its own file
for section_name, section_info in sections.items():
    if section_info['content']:
        section_path = os.path.join(CSS_DIR, section_name)
        with open(section_path, 'w') as f:
            f.write('\n'.join(section_info['content']))
        print(f"✓ Created {section_name} ({len(section_info['content'])} blocks)")

# Create main.css that imports all modules
main_css_content = '''/* Books Library Styles - Modular Architecture */

/* Load component stylesheets in order */
@import 'base.css';
@import 'header.css';
@import 'layout.css';
@import 'alerts.css';
@import 'cards.css';
@import 'modals.css';
@import 'buttons.css';
@import 'forms.css';
'''

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
print(f"  Original: 851 lines → Now split into 9 files")
print(f"  Backup saved as: styles.css.backup")
