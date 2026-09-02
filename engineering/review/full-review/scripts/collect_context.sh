#!/usr/bin/env bash
set -euo pipefail

kind="${1:-}"
target="${2:-}"
base="${3:-}"
out_dir="${OUT_DIR:-./artifacts/full-review}"
mkdir -p "$out_dir"

usage() {
  cat <<EOF
Usage: collect_context.sh <mode> <target> [base_branch]

Modes:
  pr     <number>        Fetch PR metadata, diff, and comments via gh
  commit <sha>           Show commit details and diff
  range  <base..head>    Diff between two refs
  local  [base_branch]   Diff current branch + working tree against the merge-base with a base branch (default: main)

Environment:
  OUT_DIR   Output directory (default: ./artifacts/full-review)
EOF
  exit 1
}

if [[ -z "$kind" ]]; then
  usage
fi

has_gh=false
if command -v gh >/dev/null 2>&1; then
  has_gh=true
fi

case "$kind" in
  pr)
    if [[ -z "$target" ]]; then
      echo "Error: PR number is required."
      usage
    fi
    if [[ "$has_gh" != true ]]; then
      echo "Error: gh CLI is not available. Use commit or range mode, or install gh."
      exit 2
    fi
    if ! gh auth status >/dev/null 2>&1; then
      echo "Error: gh is not authenticated. Run: gh auth login"
      exit 3
    fi
    gh pr view "$target" --json title,body,url,baseRefName,headRefName,author,labels,files,commits,reviewDecision > "$out_dir/pr.json"
    gh pr diff "$target" > "$out_dir/diff.patch"
    gh api "repos/{owner}/{repo}/issues/$target/comments" > "$out_dir/issue_comments.json" 2>/dev/null || true
    gh api "repos/{owner}/{repo}/pulls/$target/comments" > "$out_dir/review_comments.json" 2>/dev/null || true
    gh api "repos/{owner}/{repo}/pulls/$target/reviews" > "$out_dir/reviews.json" 2>/dev/null || true
    echo "Wrote: $out_dir/pr.json, $out_dir/diff.patch, $out_dir/issue_comments.json, $out_dir/review_comments.json, $out_dir/reviews.json"
    ;;

  commit)
    if [[ -z "$target" ]]; then
      echo "Error: Commit SHA is required."
      usage
    fi
    git show "$target" --no-patch --pretty=fuller > "$out_dir/commit.txt"
    git show "$target" --patch --unified=3 > "$out_dir/diff.patch"
    git show "$target" --name-only --pretty=format: | sed '/^$/d' > "$out_dir/files.txt"
    echo "Wrote: $out_dir/commit.txt, $out_dir/diff.patch, $out_dir/files.txt"
    ;;

  range)
    if [[ -z "$target" ]]; then
      echo "Error: Range spec is required (e.g., base..head)."
      usage
    fi
    if [[ -n "$base" ]]; then
      git diff "$base...$target" --unified=3 > "$out_dir/diff.patch"
      git diff "$base...$target" --name-only > "$out_dir/files.txt"
    else
      git diff "$target" --unified=3 > "$out_dir/diff.patch"
      git diff "$target" --name-only > "$out_dir/files.txt"
    fi
    echo "Wrote: $out_dir/diff.patch, $out_dir/files.txt"
    ;;

  local)
    base_branch="${target:-main}"
    merge_base="$(git merge-base "$base_branch" HEAD)"
    git diff "$merge_base" --unified=3 > "$out_dir/diff.patch"
    git diff "$merge_base" --name-only > "$out_dir/files.txt"
    git log "$base_branch"..HEAD --pretty=format:"%h %s" > "$out_dir/commits.txt"
    echo "Wrote: $out_dir/diff.patch, $out_dir/files.txt, $out_dir/commits.txt"
    ;;

  *)
    echo "Error: Unknown mode '$kind'."
    usage
    ;;
esac
