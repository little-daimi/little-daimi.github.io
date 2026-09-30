#!/usr/bin/env bash
# Build locally, upload a complete release, and switch the published symlink.
set -Eeuo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
BLOG_SSH_HOST=${BLOG_SSH_HOST:-blog}
[[ $BLOG_SSH_HOST =~ ^[a-zA-Z0-9_.@:-]+$ && $BLOG_SSH_HOST != -* ]] || {
    printf 'Invalid BLOG_SSH_HOST\n' >&2
    exit 2
}
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o UpdateHostKeys=no)
cd "$PROJECT_DIR"

if "${SSH[@]}" "$BLOG_SSH_HOST" 'systemctl is-active --quiet daimi-sync.timer'; then
    printf 'Automatic publishing is enabled. Commit your changes and push main instead.\n' >&2
    printf 'For an emergency manual release, stop daimi-sync.timer first.\n' >&2
    exit 1
fi
BLOG_DEPLOY_BASE=$("${SSH[@]}" "$BLOG_SSH_HOST" 'if test -d /etc/daimi/state/releases; then printf /etc/daimi/state; else printf /etc/daimi; fi')
[[ $BLOG_DEPLOY_BASE == /etc/daimi || $BLOG_DEPLOY_BASE == /etc/daimi/state ]] || exit 1

npm run clean
npm run build
npm run check

if [[ -n $(find public -type l -print -quit) ]]; then
    printf 'Static output must not contain symlinks\n' >&2
    exit 1
fi

# mktemp reserves a unique release directory without touching the live version.
RELEASE_DIR=$("${SSH[@]}" "$BLOG_SSH_HOST" "test -d '$BLOG_DEPLOY_BASE/releases' && mktemp -d '$BLOG_DEPLOY_BASE/releases/release-XXXXXXXXXX'")
[[ $RELEASE_DIR =~ ^/etc/daimi/(state/)?releases/release-[a-zA-Z0-9]+$ ]] || {
    printf 'Unexpected remote release path\n' >&2
    exit 1
}
chmod_cmd="find '$RELEASE_DIR' -type d -exec chmod 0755 {} +; find '$RELEASE_DIR' -type f -exec chmod 0644 {} +"
printf 'Uploading to %s:%s\n' "$BLOG_SSH_HOST" "$RELEASE_DIR"
tar -C public -czf - . | "${SSH[@]}" "$BLOG_SSH_HOST" "set -e; tar -xzf - --no-same-owner --no-same-permissions -C '$RELEASE_DIR'; $chmod_cmd"

# Verify every uploaded file before replacing the current pointer.
MANIFEST=$(mktemp)
trap 'unlink "$MANIFEST"' EXIT
(cd public && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$MANIFEST"
"${SSH[@]}" "$BLOG_SSH_HOST" "cd '$RELEASE_DIR' && sha256sum --check --status" < "$MANIFEST"

RELEASE_NAME=${RELEASE_DIR##*/}
"${SSH[@]}" "$BLOG_SSH_HOST" "set -e; test -s '$RELEASE_DIR/index.html'; test -s '$RELEASE_DIR/about/index.html'; test -s '$RELEASE_DIR/friends/index.html'; ln -s 'releases/$RELEASE_NAME' '$BLOG_DEPLOY_BASE/.current-$RELEASE_NAME'; mv -Tf '$BLOG_DEPLOY_BASE/.current-$RELEASE_NAME' '$BLOG_DEPLOY_BASE/current'"
printf 'Published https://imi-imiab.com (%s)\n' "$RELEASE_NAME"
