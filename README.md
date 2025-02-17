# Template Diff Action 🔍

A GitHub Action that automatically detects and reviews template version changes in pull requests. It generates clear diffs and posts formatted review comments to help maintainers review template changes effectively.

## Overview

When templates are modified in a pull request, this action:
- Detects template version changes
- Compares versions using semantic versioning
- Generates formatted diffs
- Posts clear review comments
- Provides helpful guidelines and resources

## Setup

Add this workflow to your repository at `.github/workflows/template-review.yml`:

    name: Template Review
    
    on:
      pull_request:
        paths:
          - '.harness/templates/**'
    
    jobs:
      review:
        runs-on: ubuntu-latest
        permissions:
          pull-requests: write
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
              ref: ${{ github.event.pull_request.head.sha }}
              
          - name: Configure Git
            run: |
              git config --global user.email "github-actions[bot]@users.noreply.github.com"
              git config --global user.name "github-actions[bot]"
              git config --global --add safe.directory /github/workspace
    
          - name: Run Template Diff
            uses: ka1ne/template-diff-action@v1
            env:
              GITHUB_TOKEN: ${{ github.token }}
              GITHUB_CONTEXT: ${{ toJSON(github) }}

## Template Requirements

Templates must follow this structure:

    .harness/templates/
      TemplateName/
        v0.1.0.yaml
        v0.2.0.yaml
        ...

### Rules
- Files must use semantic versioning: `vX.Y.Z.yaml`
- Each template needs its own directory
- Version numbers should follow semver guidelines:
  - MAJOR: Breaking changes
  - MINOR: New features, backward compatible
  - PATCH: Bug fixes, backward compatible

## Example Output

When changes are detected, the action posts a comment like this:

    # 🔍 Template Review Required
    ### ⚠️ 1 template modification detected
    
    ## 📦 Template: `MyTemplate`
    ### 🔄 Version Update: `v0.1.0` → `v0.2.0`
    
    > ### 📝 Review Changes
    <details>
    <summary><b>&nbsp;&nbsp;&nbsp;&nbsp;👉 Click to expand diff ⤵️</b></summary>
    
    - old version content
    + new version content
    
    </details>

## Required Permissions

The action needs:
- `pull-requests: write` permission in the workflow
- `GITHUB_TOKEN` for API access
- Git configuration for workspace access

## Development

To contribute:
1. Clone the repository
2. Make your changes
3. Test locally using: `python generate_template_diff.py`
4. Submit a PR with your changes

## License

MIT License - see LICENSE file for details