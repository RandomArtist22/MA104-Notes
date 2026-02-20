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


def convert_markdown_to_html(content: str) -> str:
    """Convert markdown to HTML."""
    # Store code blocks temporarily
    code_blocks = []
    # Store math blocks temporarily
    math_blocks = []
    
    def store_code_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2)
        code_blocks.append((lang, code))
        return f"{{«CODEBLOCK{len(code_blocks)-1}}}}}"
    
    def store_math_block(match):
        math = match.group(0)
        math_blocks.append(math)
        return f"{{«MATHBLOCK{len(math_blocks)-1}}}}}"
    
    # Extract code blocks first (before math, to avoid conflicts)
    content = re.sub(r'```(\w+)?\n(.*?)```', store_code_block, content, flags=re.DOTALL)
    
    # Extract display math ($$...$$) - must be before inline math
    content = re.sub(r'\$\$(.*?)\$\$', store_math_block, content, flags=re.DOTALL)
    
    # Extract inline math ($...$) - be careful to not match escaped dollars
    content = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', store_math_block, content)
    
    # Headers
    content = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', content, flags=re.MULTILINE)
    content = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', content, flags=re.MULTILINE)
    content = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
    content = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    
    # Bold and Italic
    content = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', content)
    content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)
    content = re.sub(r'___([^_]+)___', r'<strong><em>\1</em></strong>', content)
    content = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', content)
    content = re.sub(r'_([^_]+)_', r'<em>\1</em>', content)
    
    # Inline code (after bold/italic to avoid conflicts)
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
    
    # Links
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)
    
    # Images
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', content)
    
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
        return f'<blockquote>\n{inner}\n</blockquote>'
    
    content = re.sub(r'((?:^>.*\n?)+)', process_blockquote, content, flags=re.MULTILINE)
    
    # Tables
    def process_table(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        
        html = ['<table>']
        html.append('<thead>')
        
        # Header row
        header_cells = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
        html.append('<tr>' + ''.join(f'<th>{cell}</th>' for cell in header_cells) + '</tr>')
        html.append('</thead>')
        html.append('<tbody>')
        
        # Data rows (skip separator line)
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                html.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
        
        html.append('</tbody>')
        html.append('</table>')
        return '\n'.join(html)
    
    # Match tables: lines starting with | and containing |
    content = re.sub(r'(^\|.*\|$(?:\n^\|[-:\s|]+\|$(?:\n^\|.*\|$)*))', process_table, content, flags=re.MULTILINE)
    
    # Horizontal rule
    content = re.sub(r'^---+$', '<hr>', content, flags=re.MULTILINE)
    
    # Lists
    def process_ul(match):
        items = match.group(0).strip().split('\n')
        html_items = []
        for item in items:
            item_content = re.sub(r'^[\s]*[-*+]\s+', '', item)
            item_content = convert_simple_inline(item_content)
            html_items.append(f'<li>{item_content}</li>')
        return '<ul>\n' + '\n'.join(html_items) + '\n</ul>'
    
    def process_ol(match):
        items = match.group(0).strip().split('\n')
        html_items = []
        for item in items:
            item_content = re.sub(r'^[\s]*\d+\.\s+', '', item)
            item_content = convert_simple_inline(item_content)
            html_items.append(f'<li>{item_content}</li>')
        return '<ol>\n' + '\n'.join(html_items) + '\n</ol>'
    
    # Process unordered lists (consecutive lines starting with -, *, or +)
    content = re.sub(r'((?:^[\s]*[-*+]\s+.+\n?)+)', process_ul, content, flags=re.MULTILINE)
    
    # Process ordered lists
    content = re.sub(r'((?:^[\s]*\d+\.\s+.+\n?)+)', process_ol, content, flags=re.MULTILINE)
    
    # Restore code blocks
    for i, (lang, code) in enumerate(code_blocks):
        escaped_code = escape_html(code)
        content = content.replace(f'{{«CODEBLOCK{i}}}}}', 
            f'<pre><code class="language-{lang}">{escaped_code}</code></pre>')
    

    # Restore math blocks (keep raw $...$ for MathJax)
    for i, math in enumerate(math_blocks):
        content = content.replace(f'{{«MATHBLOCK{i}}}}}',
            math)
    # Paragraphs (wrap remaining text)
    paragraphs = []
    for block in content.split('\n\n'):
        block = block.strip()
        if block and not block.startswith('<'):
            block = convert_simple_inline(block)
            paragraphs.append(f'<p>{block}</p>')
        else:
            paragraphs.append(block)
    
    return '\n\n'.join(paragraphs)


def convert_simple_inline(text: str) -> str:
    """Convert simple inline markdown without block elements."""
    # Bold and Italic
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'___([^_]+)___', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
    text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


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
