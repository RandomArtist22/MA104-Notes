#!/usr/bin/env python3
"""
MA104 Site Publisher
Builds the site and prepares it for GitHub Pages deployment.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

DIST_DIR = Path("dist")
DOCS_DIR = Path("docs")


def run_command(cmd, cwd=None):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def main():
    print("🚀 MA104 Site Publisher")
    print("=" * 50)
    
    # Step 1: Build the site
    print("\n📦 Step 1: Building site...")
    result = subprocess.run([sys.executable, "build.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Build failed: {result.stderr}")
        return 1
    
    # Step 2: Create docs folder for GitHub Pages (if using docs/ folder deployment)
    print("\n📁 Step 2: Setting up docs folder...")
    
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    
    shutil.copytree(DIST_DIR, DOCS_DIR)
    print(f"   ✓ Copied dist/ to docs/")
    
    # Step 3: Add .nojekyll file to disable Jekyll processing
    (DOCS_DIR / ".nojekyll").touch()
    print("   ✓ Added .nojekyll file")
    
    # Step 4: Copy README
    readme_source = Path("README.md")
    if readme_source.exists():
        shutil.copy2(readme_source, DOCS_DIR / "README.md")
        print("   ✓ Copied README.md")
    
    print("\n" + "=" * 50)
    print("✅ Site ready for deployment!")
    print("\n📋 Deployment Options:")
    print("\n1. Deploy to GitHub Pages (docs/ folder):")
    print("   - Commit and push the docs/ folder")
    print("   - Go to Settings → Pages → Build from branch")
    print("   - Select 'main' branch and '/docs' folder")
    print("\n2. Deploy to GitHub Pages (gh-pages branch):")
    print("   git subtree push --prefix dist origin gh-pages")
    print("\n3. Deploy to other hosting (Netlify, Vercel, etc):")
    print("   Upload the contents of the dist/ folder")
    
    # Check if git repo
    if Path(".git").exists():
        print("\n🤖 Git detected. Would you like to:")
        print("   [1] Commit docs/ folder to main branch")
        print("   [2] Push dist/ to gh-pages branch")
        print("   [3] Do nothing (manual deployment)")
        
        try:
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                print("\n📤 Committing docs/ folder...")
                run_command("git add docs/")
                run_command(f'git commit -m "Update site - {datetime.now().strftime("%Y-%m-%d %H:%M")}"')
                run_command("git push origin main")
                print("   ✓ Committed and pushed docs/ folder")
                print("\n🌐 Enable GitHub Pages:")
                print("   Settings → Pages → Build from branch → main → /docs")
                
            elif choice == "2":
                print("\n📤 Pushing to gh-pages branch...")
                # Check if gh-pages exists
                result = subprocess.run("git branch -r | grep gh-pages", shell=True, capture_output=True)
                if result.returncode == 0:
                    # Branch exists, force push
                    run_command("git push origin `git subtree split --prefix dist main`:gh-pages --force")
                else:
                    # First time push
                    run_command("git subtree push --prefix dist origin gh-pages")
                print("   ✓ Pushed to gh-pages branch")
                print("\n🌐 Enable GitHub Pages:")
                print("   Settings → Pages → Build from branch → gh-pages → /(root)")
                
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled. You can deploy manually later.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
