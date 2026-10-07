#!/bin/sh
set -eu

allowlist_file=/etc/nginx/conf.d/admin-allowlist.conf
: > "$allowlist_file"

for ip in ${NGINX_ADMIN_ALLOWED_IPS:-}; do
    printf 'allow %s;\n' "$ip" >> "$allowlist_file"
done