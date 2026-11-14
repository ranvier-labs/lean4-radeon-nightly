#!/usr/bin/env python3
# Copyright (c) 2026 Ranvier Systems. All rights reserved.
# Released under Apache 2.0 license as described in the file LICENSE.
"""Validate source-free Radeon distributions and immutable release records."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile

REPO = 'ranvier-labs/lean4-radeon-nightly'
REQUIRED = {'bin/lean', 'bin/lake', 'bin/leanc', 'lib/lean/Lean/Rdna.olean',
            'lib/lean/Init.olean', 'lib/lean/libleanshared.so',
            'include/lean/lean.h', 'LICENSE', 'LICENSES'}
GATES = {'build', 'tests', 'installed_smoke', 'gpu_execution'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_record(record):
    require(set(record) == {'schema_version', 'release_id', 'source_commit', 'version',
                            'platform', 'gpu_target', 'rocm_version', 'host_os',
                            'validation', 'archive'}, 'unexpected or missing record fields')
    require(record.get('schema_version') == 1, 'unsupported schema version')
    tag = record.get('release_id', '')
    match = re.fullmatch(r'nightly-(\d{4}-\d{2}-\d{2})(?:-rev[1-9]\d*)?', tag)
    require(match is not None, 'invalid release ID')
    datetime.date.fromisoformat(match[1])
    require(re.fullmatch(r'[0-9a-f]{40}', record.get('source_commit', '')), 'expected source SHA')
    version = record.get('version', '')
    require(re.fullmatch(r'[0-9][0-9A-Za-z.+-]*', version), 'invalid version')
    require('radeon-nightly' in version, 'expected Radeon nightly version')
    require(record.get('platform') == 'linux/x86_64', 'unsupported host platform')
    require(re.fullmatch(r'gfx[0-9a-f]{3,4}', record.get('gpu_target', '')), 'invalid AMD target')
    for field in ('rocm_version', 'host_os'):
        require(isinstance(record.get(field), str) and record[field].strip(), f'missing {field}')
    gates = record.get('validation', {})
    require(set(gates) == GATES and all(v == 'passed' for v in gates.values()),
            'build, tests, installed smoke and GPU execution must pass')
    archive = record.get('archive', {})
    require(set(archive) == {'name', 'url', 'size', 'sha256'}, 'unexpected archive fields')
    name = f'lean-{version}-linux.tar.zst'
    require(archive.get('name') == name, 'nonstandard Lean archive name')
    require(archive.get('url') == f'https://github.com/{REPO}/releases/download/{tag}/{name}',
            'expected immutable release asset URL')
    require(re.fullmatch(r'[0-9a-f]{64}', archive.get('sha256', '')), 'invalid SHA-256')
    require(type(archive.get('size')) is int and archive['size'] > 0, 'invalid archive size')


def audit_tar(tar):
    root = None
    seen = set()
    manifest = []
    for member in tar:
        path = PurePosixPath(member.name)
        require(not path.is_absolute() and '..' not in path.parts and path.parts,
                f'unsafe archive path: {member.name}')
        root = root or path.parts[0]
        require(path.parts[0] == root and root.startswith('lean-'), 'expected one Lean directory')
        require(member.isdir() or member.isfile(), f'links/devices forbidden: {member.name}')
        relative = PurePosixPath(*path.parts[1:])
        if len(path.parts) == 1:
            require(member.isdir(), 'archive root must be a directory')
            continue
        require(not any(part.startswith('.') for part in relative.parts), 'hidden file forbidden')
        require(relative.parts[0] in {'bin', 'lib', 'include', 'share', 'LICENSE', 'LICENSES'},
                f'non-distribution path: {relative}')
        require(relative.suffix not in {'.lean', '.c', '.cpp', '.cc', '.ll', '.log', '.py'},
                f'source or build log forbidden: {relative}')
        require(str(relative) not in seen, f'duplicate archive path: {relative}')
        seen.add(str(relative))
        if member.isfile():
            digest = hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest()
            manifest.append({'path': str(relative), 'size': member.size, 'sha256': digest})
    require(REQUIRED <= {entry['path'] for entry in manifest}, 'missing required toolchain files')
    return sorted(manifest, key=lambda entry: entry['path'])


def audit_archive(path):
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['zstd', '-q', '-d', '-c', str(path)], stdout=stream, check=True)
        stream.seek(0)
        with tarfile.open(fileobj=stream) as tar:
            return audit_tar(tar)


def write_record(path, record):
    validate_record(record)
    with path.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('records', type=Path)
    audit = commands.add_parser('audit')
    audit.add_argument('archive', type=Path)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('archive', type=Path)
    prepare.add_argument('--evidence', type=Path, required=True)
    prepare.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'validate':
        for path in sorted(args.records.glob('*.json')):
            record = json.loads(path.read_text())
            validate_record(record)
            require(path.stem == record['release_id'], 'record filename must match release ID')
            print(f'validated {path.name}')
    elif args.command == 'audit':
        print(json.dumps(audit_archive(args.archive), indent=2))
    else:
        record = json.loads(args.evidence.read_text())
        record['schema_version'] = 1
        name = args.archive.name
        with args.archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        record['archive'] = {'name': name, 'size': args.archive.stat().st_size,
                             'sha256': digest,
                             'url': f'https://github.com/{REPO}/releases/download/{record["release_id"]}/{name}'}
        validate_record(record)
        manifest = audit_archive(args.archive)
        require(not args.output.exists(), 'output directory already exists; use a fresh directory')
        args.output.mkdir(parents=True)
        write_record(args.output / f'{record["release_id"]}.json', record)
        (args.output / f'{name}.sha256').write_text(f'{digest}  {name}\n')
        (args.output / f'{name}.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Prepared verified metadata in {args.output}')


if __name__ == '__main__':
    main()
