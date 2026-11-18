#!/usr/bin/env bash
# Copyright (c) 2026 Ranvier Systems. All rights reserved.
# Released under Apache 2.0 license as described in the file LICENSE.
set -euo pipefail
if [[ $# != 2 && !( $# == 4 && ${3-} == --notes-file ) ]]; then
  echo "Usage: $0 ARCHIVE EVIDENCE.json [--notes-file PUBLIC-NOTES.md]" >&2
  exit 2
fi
repo=ranvier-labs/lean4-radeon-nightly
archive=$(realpath "$1")
evidence=$(realpath "$2")
notes=
if [[ $# == 4 ]]; then
  notes=$(realpath "$4")
  [[ -f $notes && -r $notes ]] || { echo 'Release notes must be a readable file' >&2; exit 1; }
fi
cd "$(dirname "$0")/.."
[[ $(git branch --show-current) == main ]] || { echo 'Publish from main' >&2; exit 1; }
[[ -z $(git status --porcelain) ]] || { echo 'Working tree must be clean' >&2; exit 1; }
case $(git remote get-url origin) in
  "git@github.com:$repo.git"|"https://github.com/$repo.git"|"https://github.com/$repo") ;;
  *) echo 'origin must be the Radeon distribution repository' >&2; exit 1 ;;
esac
git fetch origin main
[[ $(git rev-parse HEAD) == $(git rev-parse origin/main) ]] || {
  echo 'Local main must match origin/main' >&2; exit 1;
}
make check build
work=$(mktemp -d)
printf 'Publication workspace: %s\n' "$work"
# Retain evidence and downloads if a network operation fails; no published asset is overwritten.
python3 scripts/release.py prepare "$archive" --evidence "$evidence" --output "$work/metadata"
records=("$work/metadata"/nightly-*.json)
tag=$(basename "${records[0]}" .json)
name=$(basename "$archive")
[[ ! -e releases/$tag.json ]] || { echo 'Release record already exists' >&2; exit 1; }
tag_ref=$(git ls-remote --tags origin "refs/tags/$tag")
[[ -z $tag_ref ]] || { echo 'Release tag already exists' >&2; exit 1; }
cat > "$work/notes.md" <<EOF
Experimental Lean Radeon toolchain for Linux x86_64.

Install with: \`elan toolchain install $repo:$tag\`.

See the attached JSON record for the source revision, tested GPU target, ROCm
version, host OS, and validation gates. SHA-256 checksums and the archive file
manifest are attached. The separate compiler source history is not included.
EOF
if [[ -n $notes ]]; then
  printf '\n' >> "$work/notes.md"
  cat "$notes" >> "$work/notes.md"
fi
gh release create "$tag" --repo "$repo" --target "$(git rev-parse HEAD)" --draft --prerelease \
  --title "Lean Radeon $tag" --notes-file "$work/notes.md" \
  "$archive" "$work/metadata/$name.sha256" "$work/metadata/$name.manifest.json" \
  "$work/metadata/$tag.json"
gh release download "$tag" --repo "$repo" --dir "$work/download"
cmp "$archive" "$work/download/$name"
for file in "$work/metadata/"*; do
  cmp "$file" "$work/download/$(basename "$file")"
done
gh release edit "$tag" --repo "$repo" --draft=false --prerelease
cp "$work/metadata/$tag.json" "releases/$tag.json"
python3 scripts/release.py validate releases
git add "releases/$tag.json"
git commit -m "chore: publish $tag"
git push origin HEAD:main
printf 'Published https://github.com/%s/releases/tag/%s\n' "$repo" "$tag"
