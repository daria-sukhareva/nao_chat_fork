#!/usr/bin/env bash
# Assembles the files one arm adds to the demo project, ready to copy into /app/kwwhat.
set -euo pipefail

usage() {
	echo "usage: $0 <A|B|N|D> <demo chat-bi dir> <output dir>" >&2
	exit 2
}

[[ $# -eq 3 ]] || usage
arm=$1
demo_dir=$2
out_dir=$3
study_dir=$(cd "$(dirname "$0")" && pwd)

case $arm in
	A | N) overlays=(common) ;;
	B) overlays=(common arm-b) ;;
	D)
		echo "Arm D's degradations are not defined yet." >&2
		exit 1
		;;
	*) usage ;;
esac

[[ -f $demo_dir/RULES.md ]] || { echo "No RULES.md in $demo_dir" >&2; exit 1; }
[[ ! -e $out_dir ]] || { echo "$out_dir already exists" >&2; exit 1; }
[[ ! -e ${out_dir%/}.sha256 ]] || { echo "${out_dir%/}.sha256 already exists" >&2; exit 1; }

mkdir -p "$out_dir"
cp "$demo_dir/RULES.md" "$out_dir/RULES.md"

for overlay in "${overlays[@]}"; do
	rsync -a --exclude 'RULES.md.append' "$study_dir/$overlay/" "$out_dir/"
	if [[ -f $study_dir/$overlay/RULES.md.append ]]; then
		printf '\n' >>"$out_dir/RULES.md"
		cat "$study_dir/$overlay/RULES.md.append" >>"$out_dir/RULES.md"
	fi
done

manifest="${out_dir%/}.sha256"
(cd "$out_dir" && find . -type f | LC_ALL=C sort | xargs shasum -a 256) >"$manifest"
echo "Arm $arm assembled in $out_dir, file hashes in $manifest"
