# MA104 Documentation Site

A beautiful, Kanagawa-themed documentation viewer for MA104 (Ordinary Differential Equations) lecture notes.

> **Note:** 🤖 This site contains AI-generated summaries of lecture notes from the Obsidian vault. The original notes were processed and enhanced using AI to improve readability and organization.

![Kanagawa Theme](https://img.shields.io/badge/theme-kanagawa-7e9cd8?style=flat-square)
![GitHub Pages](https://img.shields.io/badge/deployed%20on-github%20pages-6a9589?style=flat-square)

## Features

- 🎨 **Kanagawa Color Theme** - A beautiful dark theme inspired by Japanese woodblock prints
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🔗 **Obsidian Link Support** - Converts `[[Wiki Links]]` to HTML links
- 📊 **MathJax Support** - Renders LaTeX math equations
- ⚡ **Fast & Lightweight** - Static HTML, no JavaScript frameworks
- 🧭 **Navigation** - Sidebar with all lectures, next/previous links

## Quick Start

### 1. Build the Site

```bash
python3 build.py
```

This generates the static site in the `dist/` folder.

### 2. Deploy to GitHub Pages

#### Option A: Using the `docs/` folder (Easiest)

```bash
python3 publish.py
# Choose option 1 to commit the docs/ folder
```

Then on GitHub:
- Go to **Settings → Pages**
- Select **Build from branch**
- Choose **main** branch and **/docs** folder
- Click Save

Your site will be live at `https://yourusername.github.io/your-repo-name/`

#### Option B: Using the `gh-pages` branch

```bash
python3 publish.py
# Choose option 2 to push to gh-pages branch
```

Then on GitHub:
- Go to **Settings → Pages**
- Select **Build from branch**
- Choose **gh-pages** branch
- Click Save

### 3. Local Preview

```bash
cd dist
python3 -m http.server 8080
# Open http://localhost:8080 in your browser
```

## File Structure

```
.
├── build.py              # Site generator script
├── publish.py            # Deployment helper script
├── template.html         # HTML template
├── style.css             # Kanagawa-themed styles
├── dist/                 # Generated site (build output)
├── docs/                 # Copy of dist for GitHub Pages deployment
└── .github/
    └── workflows/        # GitHub Actions (optional)
```

## How It Works

1. **Source**: Markdown files with `#MA104` tag from your Obsidian vault (`/home/ramcharan/Documents/Obsidian Vault/Resources`)
2. **Build**: `build.py` converts Markdown → HTML using the Kanagawa theme
3. **Output**: Static HTML files in `dist/` ready for hosting

## Updating Content

When you add or modify notes in Obsidian:

```bash
python3 build.py      # Rebuild the site
python3 publish.py    # Deploy changes
```

## Customization

### Changing Colors

Edit the CSS variables in `style.css`:

```css
:root {
  --kana-crystal-blue: #7e9cd8;
  --kana-spring-green: #98bb6c;
  --kana-carp-yellow: #e6c384;
  /* ... more Kanagawa colors ... */
}
```

### Changing Source Directory

Edit `build.py` and modify:

```python
SOURCE_DIR = Path("/path/to/your/vault")
```

### Adding Tags

By default, the site finds files with `#MA104` tag. To change this:

```python
TAG_TO_FIND = "#YourTag"
```

## License

MIT License - Feel free to use this for your own notes!

## Credits

- [Kanagawa Theme](https://github.com/rebelot/kanagawa.nvim) - The beautiful color palette
- [MathJax](https://www.mathjax.org/) - Math rendering
- [Inter](https://rsms.me/inter/) & [JetBrains Mono](https://www.jetbrains.com/lp/mono/) - Fonts
