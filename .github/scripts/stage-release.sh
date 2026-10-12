#!/usr/bin/env bash
# Scaffold a version note, export the shipped patch, and open the release PR.
#
# Run by .github/workflows/version.yml, for a patch merge and again after a release
# publishes.
#
#   stage-release.sh <pr-number> <pr-title> <pr-url> <pr-body-file>
#
# Every argument is optional (a manual run, or the run after a publish, has no PR).
# The patch is exported here, not at publish time, so the note describes exactly
# the file the release PR carries.
set -euo pipefail

pr_number="${1:-}" pr_title="${2:-}" pr_url="${3:-}" pr_body="${4:-/dev/null}"
repo="${GITHUB_REPOSITORY:?must be run from GitHub Actions, or set GITHUB_REPOSITORY}"
work="$(mktemp -d)"
# $GITHUB_OUTPUT takes key=value lines only; anything else fails the step.
out() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "$1=$2" >> "$GITHUB_OUTPUT" || true; }
say() { echo "$1"; }

# One release PR at a time. `gh pr list --head` is exact-match, so match the
# release/ prefix with jq.
if [ "$(gh pr list --repo "$repo" --state open --limit 100 \
        --json headRefName \
        --jq '[.[] | select(.headRefName | startswith("release/"))] | length')" != "0" ]; then
  say "a release PR is already open; not staging another"
  out changed false
  exit 0
fi

# Empty rather than "#", so a note with no PR behind it says so.
pr_ref=""
if [ -n "${pr_number}" ]; then
  pr_ref="#${pr_number}"
fi

if ! python tools/version.py prepare \
      --pr "${pr_ref}" --pr-url "${pr_url}" --pr-title "${pr_title}" \
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
if git diff --cached --quiet; then
  # A re-run of a staging that already committed has nothing to add, and an
  # empty commit would fail.
  say "${tag} is already staged in the tree; nothing to commit"
  out changed false
  exit 0
fi
git commit -m "chore(release): prepare ${tag}"
# A stale release/ branch with no open PR is replaced, but only while its tip is
# still this script's scaffold commit; anything else is a rewritten note and must be kept.
remote_tip="$(git ls-remote --heads origin "${branch}" | cut -f1)"
if [ -n "${remote_tip}" ]; then
  git fetch --quiet origin "${branch}"
  tip_subject="$(git log -1 --format=%s "${remote_tip}" 2>/dev/null || true)"
  if [ "${tip_subject}" != "chore(release): prepare ${tag}" ]; then
    say "origin/${branch} ends in \"${tip_subject}\", which this script did not write."
    say "Finish that branch and open its PR, or delete it and run this workflow again."
    out changed false
    exit 1
  fi
fi
git push --force origin "HEAD:refs/heads/${branch}"

{
  echo "Prepares \`${tag}\`${pr_ref:+, after ${pr_ref} changed what ships}."
  echo
  echo "**Edit \`docs/versions/${tag}.md\` before merging.** It is a DRAFT"
  echo "scaffolded from the commits this version carries, and merging this one"
  echo "is what publishes the release - so its text is what players read. Every"
  echo "other note on that page says what the version changes over the last one,"
  echo "and what was discovered on the way."
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
