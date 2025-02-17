import os
import re
import semver
import subprocess
from pathlib import Path
import json
import traceback

TEMPLATE_DIR = '.harness/templates'
ENGINEERING_STANDARDS_URL = "https://developer.harness.io/docs/contributing"
VERSION_PATTERN = r'v(\d+\.\d+\.\d+)\.ya?ml$'

def post_comment_to_pr(content):
    """Post the diff as a comment to the PR using the GitHub API."""
    # Always print in local testing mode when using act
    if os.environ.get('CI') != 'true' or os.environ.get('ACT'):
        print("Local testing mode: Printing output instead of posting to PR")
        print("\n=== PR Comment Content ===\n")
        print(content)
        return

    import requests
    
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
        
    # Get PR number from GitHub context
    github_context = json.loads(os.environ.get('GITHUB_CONTEXT', '{}'))
    pr_number = github_context.get('event', {}).get('pull_request', {}).get('number')
    if not pr_number:
        raise ValueError("Could not determine PR number from GitHub context")
    
    # GitHub API endpoints
    api_url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{pr_number}/comments"
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.post(api_url, headers=headers, json={'body': content})
    response.raise_for_status()

def setup_git():
    """Configure git for the workspace."""
    try:
        subprocess.run(
            ['git', 'config', '--global', '--add', 'safe.directory', '/github/workspace'],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Warning: Could not configure git safe.directory")

def find_changed_templates():
    """Find template files that were changed in this PR."""
    if os.environ.get('CI') != 'true' or os.environ.get('ACT'):
        # For local testing, just get all template files
        templates = []
        for root, _, files in os.walk(TEMPLATE_DIR):
            for file in files:
                if re.search(VERSION_PATTERN, file):
                    templates.append(os.path.join(root, file))
        return templates

    # Configure git first
    setup_git()

    # For PR changes, use git diff with the base branch
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    head_ref = os.environ.get('GITHUB_HEAD_REF', 'HEAD')
    
    print(f"Base ref: {base_ref}")
    print(f"Head ref: {head_ref}")
    
    # First, fetch the base branch
    try:
        subprocess.run(['git', 'fetch', 'origin', base_ref], check=True)
        print(f"Successfully fetched origin/{base_ref}")
    except subprocess.CalledProcessError as e:
        print(f"Error fetching base branch: {e}")
        raise

    # Get changed files between base and head
    diff_command = ['git', 'diff', '--name-only', f'origin/{base_ref}']
    print(f"Running diff command: {' '.join(diff_command)}")
    
    result = subprocess.run(diff_command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running diff command: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, diff_command)
        
    changed_files = result.stdout.splitlines()
    print(f"Changed files: {changed_files}")
    
    templates = [f for f in changed_files if f.startswith(TEMPLATE_DIR) and re.search(VERSION_PATTERN, f)]
    print(f"Detected template changes: {templates}")
    return templates

def get_previous_version(template_path):
    """Find the previous version of a template based on semver."""
    directory = os.path.dirname(template_path)
    filename = os.path.basename(template_path)
    template_name = os.path.basename(directory)
    
    try:
        # Extract version from filename (format: v0.1.0.yaml)
        current_version_match = re.search(VERSION_PATTERN, filename)
        if not current_version_match:
            raise ValueError(f"Invalid version format in filename: {filename}. Expected format: vX.Y.Z.yaml")
        
        current_version = current_version_match.group(1)
        
        # Get all versions in the directory
        versions = []
        for file in os.listdir(directory):
            version_match = re.search(VERSION_PATTERN, file)
            if version_match:
                version = version_match.group(1)
                if semver.compare(version, current_version) < 0:  # Only include older versions
                    versions.append(version)
        
        if not versions:
            raise ValueError(
                f"No previous versions found for template: {template_name}\n"
                "This appears to be the first version. If this is not intended, please ensure:\n"
                "1. You're using the correct version number\n"
                "2. Previous versions follow the format vX.Y.Z.yaml\n"
                "3. You're creating the template in the correct directory"
            )
        
        # Find closest previous version
        prev_version = max(versions, key=lambda v: semver.VersionInfo.parse(v))
        return os.path.join(directory, f"v{prev_version}.{filename.split('.')[-1]}")
    
    except Exception as e:
        return str(e)

def generate_diff_output():
    """Generate markdown diff output for all changed templates."""
    changed_templates = find_changed_templates()
    
    if not changed_templates:
        # Show disclaimer only when no changes detected
        diff_output = [
            "# Template Changes\n",
            "## ⚠️ Important Notice\n",
            "Please ensure your changes follow our engineering standards and contribution guidelines:\n",
            f"- Review the [Engineering Standards & Contribution Guidelines]({ENGINEERING_STANDARDS_URL})\n",
            "- Follow semantic versioning (MAJOR.MINOR.PATCH) for template versions\n",
            "- Template files must follow the format: `vX.Y.Z.yaml` (e.g., `v0.1.0.yaml`)\n",
            "- Place templates in their respective directories: `.harness/templates/TemplateName/`\n",
            "- Include appropriate documentation updates\n",
            "- Test your changes thoroughly\n\n",
            "## Changes Overview\n",
            "\n⚠️ No template changes detected in `.harness/templates`\n"
        ]
        return '\n'.join(diff_output)
    
    # More technical, focused on the review process
    diff_output = [
        "# 🔍 Template Review Required\n",
        f"### 📦 {len(changed_templates)} template modification{'' if len(changed_templates) == 1 else 's'} detected\n",
        "_Awaiting your technical assessment_ ⚡\n\n"
    ]

    for template in changed_templates:
        template_name = os.path.basename(os.path.dirname(template))
        diff_output.append(f"## 📦 Template: `{template_name}`\n")
        
        prev_template = get_previous_version(template)
        if isinstance(prev_template, str) and not os.path.exists(prev_template):
            # This is an error message
            diff_output.append(f"⚠️ **Warning**: {prev_template}\n")
            diff_output.append("<details><summary>🔍 View Current Template</summary>\n\n")
            with open(template, 'r') as f:
                content = f.read()
            diff_output.append("```yaml\n" + content + "\n```\n")
            diff_output.append("</details>\n")
            continue
            
        diff_command = ['git', 'diff', '--no-index', prev_template, template]
        result = subprocess.run(diff_command, capture_output=True, text=True)
        
        current_version = re.search(VERSION_PATTERN, os.path.basename(template)).group(1)
        prev_version = re.search(VERSION_PATTERN, os.path.basename(prev_template)).group(1)
        
        diff_output.append(f"### 🔄 Version Update: `v{prev_version}` → `v{current_version}`\n")
        diff_output.append("\n> ### 📝 &nbsp; Review Changes\n")
        diff_output.append("<details>\n")
        diff_output.append("<summary><b>&nbsp;&nbsp;&nbsp;&nbsp;👉 Click to expand diff &nbsp;⤵️</b></summary>\n\n")
        diff_output.append("```diff\n" + result.stdout + "\n```\n")
        diff_output.append("</details>\n\n")
    
    # Add footer with helpful links
    diff_output.extend([
        "\n---\n",
        "### 🔍 Helpful Resources\n",
        f"- [Engineering Standards & Guidelines]({ENGINEERING_STANDARDS_URL})\n",
        "- [Semantic Versioning](https://semver.org)\n",
        "\n> 💡 _Please ensure all changes are thoroughly tested before merging_\n"
    ])
    
    return '\n'.join(diff_output)

if __name__ == '__main__':
    try:
        print("Starting template diff generation...")
        print(f"Current directory contents: {os.listdir('.')}")
        print(f"Template directory contents: {os.listdir(TEMPLATE_DIR)}")
        
        diff_content = generate_diff_output()
        print(f"Found diff content: {diff_content}")
        
        if os.environ.get('CI') != 'true' or os.environ.get('ACT'):
            print("\nLocal test completed successfully!")
            print(diff_content)
        else:
            print("Attempting to post comment to PR...")
            post_comment_to_pr(diff_content)
            print("Successfully posted comment")
    except Exception as e:
        print(f"::error::Failed to generate diff: {str(e)}")
        traceback.print_exc()
        exit(1) 