#!/usr/bin/env bash
# Scaffold a version note, export the shipped patch, and open the release PR.
#
# Run by .github/workflows/version.yml from two places: once for the merge that
# changed what ships, and once more after a release publishes, to pick up any
# patch merge that landed while that release PR was waiting. Both are the same
# job, so it lives here rather than being written twice in the YAML.
#
#   stage-release.sh <pr-number> <pr-title> <pr-url> <pr-body-file>
#
# The patch is exported here, not at publish time, so the release PR pins what
# the version contains and the note describes exactly that file. A human
# rewrites the note; merging the PR is what publishes the release.
set -euo pipefail

pr_number="${1:-}" pr_title="${2:-}" pr_url="${3:-}" pr_body="${4:-/dev/null}"
repo="${GITHUB_REPOSITORY:?must be run from GitHub Actions, or set GITHUB_REPOSITORY}"
work="$(mktemp -d)"
# $GITHUB_OUTPUT takes key=value lines only. Human-readable notes must not be
# written to it, or the runner rejects the file and fails the step after the
# work has already succeeded ("Invalid format 'staged ...'").
out() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "$1=$2" >> "$GITHUB_OUTPUT" || true; }
say() { echo "$1"; }

# One release PR at a time: a branch already open for a version is someone
# else's to finish, and staging a second would make two versions out of one.
# `gh pr list --head` matches a branch name exactly, not a prefix, so the
# release/ prefix is matched with jq instead.
if [ "$(gh pr list --repo "$repo" --state open --limit 100 \
        --json headRefName \
        --jq '[.[] | select(.headRefName | startswith("release/"))] | length')" != "0" ]; then
  say "a release PR is already open; not staging another"
  out changed false
  exit 0
fi

if ! python tools/version.py prepare \
      --pr "#${pr_number}" --pr-url "${pr_url}" --pr-title "${pr_title}" \
      --pr-body "${pr_body}" > "${work}/prepare.log"; then
  cat "${work}/prepare.log"
  exit 1
fi
cat "${work}/prepare.log"
tag="$(sed -n 's/^tag=//p' "${work}/prepare.log")"
if [ -z "${tag}" ]; then
  say "nothing that ships changed; no version owed"
  out changed false
  exit 0
fi

python tools/export.py --release "${tag}"
git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
branch="release/${tag}"
git checkout -b "${branch}"
git add patch/428113C2.pnach docs/versions/
git commit -m "chore(release): prepare ${tag}"
git push -u origin "${branch}"

{
  echo "Prepares \`${tag}\`, after #${pr_number} changed what ships."
  echo
  echo "**Edit \`docs/versions/${tag}.md\` before merging.** It is a DRAFT"
  echo "scaffolded from that PR, and merging this one is what publishes the"
  echo "release - so its text is what players read. Every other note on that"
  echo "page says what the version changes over the last one, and what was"
  echo "discovered on the way."
  echo
  echo "\`patch/428113C2.pnach\` here is exported from the tree as it stood when"
  echo "this PR opened, so the note and the file describe the same build. If"
  echo "another patch PR merges first, its change is not in this version and is"
  echo "staged as the next one: a version is a snapshot, not a moving target."
  echo
  echo "Merging tags \`${tag}\` and publishes the GitHub Release."
} > "${work}/pr-body.md"
gh pr create --base main --head "${branch}" --title "${tag}" --body-file "${work}/pr-body.md"

say "staged ${tag} on ${branch}"
out changed true
out tag "${tag}"
