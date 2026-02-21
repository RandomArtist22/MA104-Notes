#!/usr/bin/env python3
"""
MA104 Documentation Site Generator
Processes Obsidian markdown files with #MA104 tag and generates a static site.
"""

import re
import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
SOURCE_DIR = Path("/home/ramcharan/Documents/Obsidian Vault/Resources")
OUTPUT_DIR = Path("/home/ramcharan/Documents/tools/obsidian_to_github_site/dist")
TAG_TO_FIND = "#MA104"

# Kanagawa-themed colors for syntax highlighting in code blocks
CODE_THEMES = {
    'keyword': '#957fb8',    # oni-violet
    'string': '#98bb6c',     # spring-green
    'comment': '#727169',    # fuji-gray
    'number': '#dca561',     # autumn-yellow
    'function': '#7e9cd8',   # crystal-blue
    'operator': '#e46876',   # wave-red
}

BLOCK_LEVEL_TAG_RE = re.compile(
    r'^<(?:h[1-6]|ul|ol|li|pre|blockquote|table|thead|tbody|tr|th|td|hr|p|div|img)\b',
    re.IGNORECASE,
)
BLOCK_PLACEHOLDER_RE = re.compile(r'^@@(?:CODEBLOCK|DISPLAYMATH)_\d+@@$')


def extract_title(content: str, filename: str) -> str:
    """Extract title from markdown content or filename."""
    # Try to find H1
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Fallback to filename
    name = Path(filename).stem
    name = name.replace('-', ' ').replace('_', ' ')
    return name.title()


def extract_tags(content: str) -> list:
    """Extract tags from markdown content."""
    tags = re.findall(r'#(\w+)', content)
    return list(set(tags))


def has_tag(content: str, tag: str) -> bool:
    """Check if content has a specific tag."""
    tags = extract_tags(content)
    return tag.lstrip('#') in tags


def parse_obsidian_links(content: str, file_mapping: dict) -> str:
    """Convert Obsidian [[links]] to HTML links."""
    def replace_link(match):
        link_text = match.group(1)
        # Check if there's a display text
        if '|' in link_text:
            target, display = link_text.split('|', 1)
        else:
            target = display = link_text
        
        # Find target file
        target_clean = target.strip()
        target_file = None
        
        # Try exact match first
        if target_clean in file_mapping:
            target_file = file_mapping[target_clean]
        else:
            # Try case-insensitive
            for key, value in file_mapping.items():
                if key.lower() == target_clean.lower():
                    target_file = value
                    break
        
        if target_file:
            return f'<a href="{target_file}">{display}</a>'
        else:
            # Dead link - still render but styled differently
            return f'<span class="dead-link" title="Missing: {target}">{display}</span>'
    
    return re.sub(r'\[\[(.*?)\]\]', replace_link, content)


def is_block_level_html(block: str) -> bool:
    """Return True if a block already represents block-level HTML."""
    stripped = block.strip()
    if not stripped:
        return False
    if BLOCK_PLACEHOLDER_RE.fullmatch(stripped):
        return True
    return bool(BLOCK_LEVEL_TAG_RE.match(stripped))


def convert_markdown_to_html(content: str) -> str:
    """Convert markdown to HTML."""
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Store blocks temporarily
    code_blocks = []
    display_math_blocks = []
    inline_math_blocks = []

    def store_code_block(match):
        lang = (match.group(1) or 'text').strip() or 'text'
        code = match.group(2).rstrip('\n')
        code_blocks.append((lang, code))
        return f"@@CODEBLOCK_{len(code_blocks)-1}@@"

    def store_display_math_block(match):
        math = match.group(0)
        display_math_blocks.append(math.strip())
        # Keep display math as a standalone block
        return f"\n\n@@DISPLAYMATH_{len(display_math_blocks)-1}@@\n\n"

    def store_inline_math_block(match):
        math = match.group(0)
        inline_math_blocks.append(math)
        return f"@@INLINEMATH_{len(inline_math_blocks)-1}@@"

    def restore_placeholders(text: str) -> str:
        for i, (lang, code) in enumerate(code_blocks):
            escaped_code = escape_html(code)
            text = text.replace(
                f"@@CODEBLOCK_{i}@@",
                f'<pre><code class="language-{lang}">{escaped_code}</code></pre>',
            )

        for i, math in enumerate(display_math_blocks):
            text = text.replace(f"@@DISPLAYMATH_{i}@@", math)

        for i, math in enumerate(inline_math_blocks):
            text = text.replace(f"@@INLINEMATH_{i}@@", math)

        return text

    # Extract code first, then math (so markdown in code fences is untouched)
    content = re.sub(r'```([^\n`]*)\n(.*?)```', store_code_block, content, flags=re.DOTALL)
    content = re.sub(r'\$\$(.*?)\$\$', store_display_math_block, content, flags=re.DOTALL)
    content = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', store_inline_math_block, content)

    # Headers
    content = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', content, flags=re.MULTILINE)
    content = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', content, flags=re.MULTILINE)
    content = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
    content = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    content = re.sub(r'^(<h[1-6][^>]*>.*?</h[1-6]>)$', r'\n\n\1\n\n', content, flags=re.MULTILINE)

    # Blockquotes
    def process_blockquote(match):
        lines = match.group(1).strip().split('\n')
        processed_lines = []
        for line in lines:
            # Remove leading > and space
            processed_lines.append(re.sub(r'^>\s?', '', line))
        inner = '\n'.join(processed_lines)
        # Recursively process inner content
        inner = convert_simple_inline(inner)
        return f'\n\n<blockquote>\n{inner}\n</blockquote>\n\n'
    
    content = re.sub(r'((?:^>.*(?:\n|$))+)', process_blockquote, content, flags=re.MULTILINE)

    # Tables
    def process_table(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')

        html = ['<table>']
        html.append('<thead>')

        # Header row
        header_cells = [convert_simple_inline(cell.strip()) for cell in lines[0].split('|') if cell.strip()]
        html.append('<tr>' + ''.join(f'<th>{cell}</th>' for cell in header_cells) + '</tr>')
        html.append('</thead>')
        html.append('<tbody>')

        # Data rows (skip separator line)
        for line in lines[2:]:
            cells = [convert_simple_inline(cell.strip()) for cell in line.split('|') if cell.strip()]
            if cells:
                html.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')

        html.append('</tbody>')
        html.append('</table>')
        return '\n\n' + '\n'.join(html) + '\n\n'

    # Match tables: lines starting with | and containing |
    content = re.sub(r'(^\|.*\|$(?:\n^\|[-:\s|]+\|$(?:\n^\|.*\|$)*))', process_table, content, flags=re.MULTILINE)

    # Horizontal rule
    content = re.sub(r'^---+$', '<hr>', content, flags=re.MULTILINE)
    content = re.sub(r'^(<hr>)$', r'\n\n\1\n\n', content, flags=re.MULTILINE)

    # Lists
    def process_ul(match):
        lines = match.group(0).split('\n')
        items = []
        current_item = None

        for line in lines:
            bullet_match = re.match(r'^[\s]*[-*+]\s+(.+)$', line)
            if bullet_match:
                if current_item is not None:
                    items.append(current_item.strip())
                current_item = bullet_match.group(1).rstrip()
                continue

            continuation_match = re.match(r'^[ \t]{2,}(.+)$', line)
            if continuation_match and current_item is not None:
                current_item += '\n' + continuation_match.group(1).rstrip()

        if current_item is not None:
            items.append(current_item.strip())

        html_items = []
        for item in items:
            item_content = convert_simple_inline(item)
            html_items.append(f'<li>{item_content}</li>')
        return '\n\n<ul>\n' + '\n'.join(html_items) + '\n</ul>\n\n'

    def process_ol(match):
        lines = match.group(0).split('\n')
        items = []
        current_item = None

        for line in lines:
            item_match = re.match(r'^[\s]*\d+\.\s+(.+)$', line)
            if item_match:
                if current_item is not None:
                    items.append(current_item.strip())
                current_item = item_match.group(1).rstrip()
                continue

            continuation_match = re.match(r'^[ \t]{2,}(.+)$', line)
            if continuation_match and current_item is not None:
                current_item += '\n' + continuation_match.group(1).rstrip()

        if current_item is not None:
            items.append(current_item.strip())

        html_items = []
        for item in items:
            item_content = convert_simple_inline(item)
            html_items.append(f'<li>{item_content}</li>')
        return '\n\n<ol>\n' + '\n'.join(html_items) + '\n</ol>\n\n'

    # Process lists with continuation lines (indented by at least 2 spaces)
    content = re.sub(
        r'((?:^[\s]*[-*+]\s+.+(?:\n^[ \t]{2,}.+)*\n?)+)',
        process_ul,
        content,
        flags=re.MULTILINE,
    )

    # Process ordered lists
    content = re.sub(
        r'((?:^[\s]*\d+\.\s+.+(?:\n^[ \t]{2,}.+)*\n?)+)',
        process_ol,
        content,
        flags=re.MULTILINE,
    )

    # Paragraphs (wrap remaining text)
    paragraphs = []
    for block in re.split(r'\n{2,}', content):
        block = block.strip()
        if not block:
            continue

        if not is_block_level_html(block):
            block = convert_simple_inline(block)
            paragraphs.append(f'<p>{block}</p>')
        else:
            paragraphs.append(block)

    html = '\n\n'.join(paragraphs)
    return restore_placeholders(html)


def convert_simple_inline(text: str) -> str:
    """Convert simple inline markdown without block elements."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Preserve markdown hard line breaks only.
    text = re.sub(r' {2,}\n', '<br>\n', text)
    text = re.sub(r'\\\n', '<br>\n', text)
    text = re.sub(r'\n+', ' ', text)

    # Protect inline code from markdown emphasis parsing.
    inline_code_blocks = []

    def store_inline_code(match):
        inline_code_blocks.append(match.group(1))
        return f"@@INLINECODE_{len(inline_code_blocks)-1}@@"

    text = re.sub(r'`([^`]+)`', store_inline_code, text)

    # Bold and Italic
    text = re.sub(r'\*\*\*([^*\n]+)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)___([^_\n]+)___(?!\w)', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'(?<!\w)__([^_\n]+)__(?!\w)', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'<em>\1</em>', text)

    # Images before links to avoid partial conversion of ![...](...)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    for i, code in enumerate(inline_code_blocks):
        escaped_code = escape_html(code)
        text = text.replace(f"@@INLINECODE_{i}@@", f'<code>{escaped_code}</code>')

    return text.strip()


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def find_ma104_files(source_dir: Path) -> list:
    """Find all markdown files with #MA104 tag."""
    files = []
    
    for md_file in source_dir.glob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            if has_tag(content, TAG_TO_FIND):
                title = extract_title(content, md_file.name)
                files.append({
                    'path': md_file,
                    'title': title,
                    'original_name': md_file.stem,
                    'content': content
                })
        except Exception as e:
            print(f"Warning: Could not read {md_file}: {e}")
    
    return files


def sort_files(files: list) -> list:
    """Sort files: Course Overview first, then lectures by number."""
    def sort_key(f):
        title = f['title'].lower()
        if 'overview' in title:
            return (0, 0)
        # Extract lecture number
        match = re.search(r'lecture\s+(\d+)', title, re.IGNORECASE)
        if match:
            return (1, int(match.group(1)))
        # Handle "9 & 10" case
        match = re.search(r'lecture\s+(\d+)\s*&\s*\d+', title, re.IGNORECASE)
        if match:
            return (1, int(match.group(1)))
        return (2, title)
    
    return sorted(files, key=sort_key)


def generate_filename(title: str, original: str) -> str:
    """Generate URL-friendly filename."""
    # Try to use lecture number
    match = re.search(r'lecture\s+(\d+(?:\s*&\s*\d+)?)', title, re.IGNORECASE)
    if match:
        num = match.group(1).replace(' ', '').replace('&', '-')
        return f"lecture-{num}.html"
    if 'overview' in title.lower():
        return "index.html"
    return f"{slugify(original)}.html"


def apply_template(template: str, data: dict) -> str:
    """Simple template engine - replaces {{key}} with values."""
    def replace_conditionals(content: str, data: dict) -> str:
        """Handle {{#key}}...{{/key}} conditionals."""
        for key in list(data.keys()):
            pattern = r'\{\{#' + re.escape(key) + r'\}\}(.*?)\{\{/' + re.escape(key) + r'\}\}'
            if data[key]:
                content = re.sub(pattern, r'\1', content, flags=re.DOTALL)
            else:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Handle negative conditionals {{^key}}...{{/key}}
        for key in list(data.keys()):
            pattern = r'\{\{\^' + re.escape(key) + r'\}\}(.*?)\{\{/' + re.escape(key) + r'\}\}'
            if not data[key]:
                content = re.sub(pattern, r'\1', content, flags=re.DOTALL)
            else:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content
    
    def replace_loops(content: str, data: dict) -> str:
        """Handle {{#key}}...{{/key}} loops for lists."""
        for key, value in data.items():
            if isinstance(value, list):
                pattern = r'\{\{#' + re.escape(key) + r'\}\}(.*?)\{\{/' + re.escape(key) + r'\}\}'
                
                def expand_loop(match):
                    template_part = match.group(1)
                    results = []
                    for item in value:
                        part = template_part
                        if isinstance(item, dict):
                            for k, v in item.items():
                                part = part.replace(f'{{{{{k}}}}}', str(v))
                        else:
                            part = part.replace('{{.}}', str(item))
                        results.append(part)
                    return '\n'.join(results)
                
                content = re.sub(pattern, expand_loop, content, flags=re.DOTALL)
        return content
    
    result = template
    result = replace_loops(result, data)
    result = replace_conditionals(result, data)
    
    # Replace simple variables
    for key, value in data.items():
        if not isinstance(value, (list, dict)):
            result = result.replace(f'{{{{{key}}}}}', str(value))
    
    return result


def build_site():
    """Main build function."""
    print("🔍 Finding MA104 files...")
    
    # Find all files
    files = find_ma104_files(SOURCE_DIR)
    print(f"Found {len(files)} files with #MA104 tag")
    
    # Sort files
    files = sort_files(files)
    
    # Generate filenames and build mapping
    file_mapping = {}
    for f in files:
        f['filename'] = generate_filename(f['title'], f['original_name'])
        file_mapping[f['original_name']] = f['filename']
        # Also add without extension for link matching
        file_mapping[f['original_name'].replace('.md', '')] = f['filename']
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Read template
    template = (Path(__file__).parent / 'template.html').read_text()
    
    # Copy CSS
    css_source = Path(__file__).parent / 'style.css'
    css_dest = OUTPUT_DIR / 'style.css'
    shutil.copy2(css_source, css_dest)
    print(f"📋 Copied CSS to {css_dest}")
    
    # Build navigation data
    lectures = []
    for f in files:
        if 'overview' not in f['title'].lower():
            lectures.append({
                'title': f['title'].replace('MA 104: Ordinary Differential Equations - ', ''),
                'filename': f['filename'],
                'active': False
            })
    
    # Generate each page
    for i, f in enumerate(files):
        print(f"📝 Processing: {f['original_name']}")
        
        # Convert content
        content = f['content']
        
        # Remove the tag line if present
        content = re.sub(r'\*\*Tags:\*\*\s*#MA104\s*\n?', '', content)
        content = re.sub(r'Tags:\s*#MA104\s*\n?', '', content)
        
        # Convert Obsidian links
        content = parse_obsidian_links(content, file_mapping)
        
        # Convert markdown to HTML
        html_content = convert_markdown_to_html(content)
        
        # Prepare navigation
        nav_lectures = []
        for lec in lectures:
            is_active = lec['filename'] == f['filename']
            nav_lectures.append({
                'title': lec['title'],
                'filename': lec['filename'],
                'active': is_active,
                'active_class': 'active' if is_active else ''
            })
        
        # Previous and next
        prev_file = files[i-1] if i > 0 else None
        next_file = files[i+1] if i < len(files) - 1 else None
        
        has_prev = prev_file is not None
        has_next = next_file is not None
        
        prev_title = ''
        prev_filename = ''
        if prev_file:
            prev_title = prev_file['title'].replace('MA 104: Ordinary Differential Equations - ', '')
            prev_filename = prev_file['filename']
        
        next_title = ''
        next_filename = ''
        if next_file:
            next_title = next_file['title'].replace('MA 104: Ordinary Differential Equations - ', '')
            next_filename = next_file['filename']
        
        # Build page data
        is_index = 'overview' in f['title'].lower()
        page_data = {
            'title': f['title'],
            'content': html_content,
            'lectures': nav_lectures,
            'base_path': '',
            'is_index': is_index,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_title': prev_title,
            'prev_filename': prev_filename,
            'next_title': next_title,
            'next_filename': next_filename
        }
        
        # Apply template
        html = apply_template(template, page_data)
        
        # Write file
        output_file = OUTPUT_DIR / f['filename']
        output_file.write_text(html, encoding='utf-8')
        print(f"   ✓ Generated: {output_file}")
    
    print(f"\n✅ Build complete! {len(files)} pages generated in {OUTPUT_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR.absolute()}")


if __name__ == '__main__':
    build_site()
