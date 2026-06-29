#!/bin/sh
# Install/refresh the dream-loop post-commit hook into this repo's .git/hooks.
# The hook itself is versioned at .workflow/_dream/hooks/post-commit; .git/hooks
# is not tracked, so this copies the tracked source into place.
set -e
root=$(git rev-parse --show-toplevel)
hooks_dir=$(git rev-parse --git-path hooks)
src="$root/.workflow/_dream/hooks/post-commit"
dest="$hooks_dir/post-commit"
mkdir -p "$hooks_dir"
cp "$src" "$dest"
chmod +x "$dest" 2>/dev/null || true
echo "installed post-commit hook -> $dest"
