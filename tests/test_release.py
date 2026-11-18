# Copyright (c) 2026 Ranvier Systems. All rights reserved.
# Released under Apache 2.0 license as described in the file LICENSE.
import io
import tarfile
import tempfile
import json
import subprocess
import unittest
from pathlib import Path
from scripts import release


class ReleaseTests(unittest.TestCase):
    def record(self):
        tag = 'nightly-2026-11-14'
        name = 'lean-4.31.0-radeon-nightly.20261114-linux.tar.zst'
        return {
            'schema_version': 1, 'release_id': tag,
            'source_commit': 'a' * 40, 'version': '4.31.0-radeon-nightly.20261114',
            'platform': 'linux/x86_64', 'gpu_target': 'gfx1151',
            'rocm_version': '7.0', 'host_os': 'Ubuntu 24.04',
            'validation': {'build': 'passed', 'tests': 'passed',
                           'installed_smoke': 'passed', 'gpu_execution': 'passed'},
            'archive': {'name': name, 'sha256': 'b' * 64, 'size': 42,
                        'url': f'https://github.com/{release.REPO}/releases/download/{tag}/{name}'},
        }

    def test_record(self):
        release.validate_record(self.record())

    def test_invalid_records(self):
        for field, value in [('release_id', 'nightly-2026-02-30'),
                             ('source_commit', 'main'), ('platform', 'linux/aarch64'),
                             ('gpu_target', 'sm_90'), ('schema_version', 2),
                             ('version', '../escape'), ('host_os', '')]:
            with self.subTest(field=field):
                record = self.record()
                record[field] = value
                with self.assertRaises(ValueError):
                    release.validate_record(record)

    def test_no_unverified_release(self):
        for gate in self.record()['validation']:
            record = self.record()
            record['validation'][gate] = 'skipped'
            with self.assertRaises(ValueError):
                release.validate_record(record)

    def test_reject_mutable_urls_and_wrong_checksums(self):
        for field, value in [('url', 'https://example.org/binary'), ('sha256', 'bad'),
                             ('size', 0), ('size', 2**31), ('name', 'arbitrary.tar.zst')]:
            record = self.record()
            record['archive'][field] = value
            with self.assertRaises(ValueError):
                release.validate_record(record)

    def archive(self, extra=None, root='lean-test'):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as tar:
            for path in release.REQUIRED:
                info = tarfile.TarInfo(root + '/' + path)
                info.size = 1
                tar.addfile(info, io.BytesIO(b'x'))
            if extra:
                tar.addfile(extra)
        stream.seek(0)
        return tarfile.open(fileobj=stream)

    def test_binary_archive(self):
        with self.archive() as tar:
            manifest = release.audit_tar(tar)
        self.assertEqual(len(manifest), len(release.REQUIRED))

    def test_release_root_matches_filename(self):
        with self.archive() as tar, self.assertRaisesRegex(ValueError, 'archive root'):
            release.audit_tar(tar, 'lean-different-release-linux')

    def test_private_sources_and_unsafe_entries(self):
        for name in ['lean-test/src/lean/Lean.lean', 'lean-test/lib/Lean.lean',
                     'lean-test/lib/runtime.cpp', '../secret', '/secret',
                     'lean-test/.git/config', 'other/bin/lean', 'lean-test/lib/token.log']:
            with self.subTest(name=name), self.archive(tarfile.TarInfo(name)) as tar:
                with self.assertRaises(ValueError):
                    release.audit_tar(tar)

    def test_symlinks_rejected(self):
        info = tarfile.TarInfo('lean-test/lib/external')
        info.type = tarfile.SYMTYPE
        info.linkname = '/private/source'
        with self.archive(info) as tar, self.assertRaises(ValueError):
            release.audit_tar(tar)

    def test_missing_runtime(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w'):
            pass
        stream.seek(0)
        with tarfile.open(fileobj=stream) as tar, self.assertRaises(ValueError):
            release.audit_tar(tar)

    def test_immutable_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'release.json'
            release.write_record(path, self.record())
            with self.assertRaises(FileExistsError):
                release.write_record(path, self.record())

    def test_unexpected_metadata_rejected(self):
        record = self.record()
        record['private_log'] = 'must not be copied to public metadata'
        with self.assertRaises(ValueError):
            release.validate_record(record)

    def test_prepare_real_compressed_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = self.record()
            tar_path = root / 'binary.tar'
            with self.archive(root=record['archive']['name'].removesuffix('.tar.zst')) as tar:
                tar.fileobj.seek(0)
                tar_path.write_bytes(tar.fileobj.read())
            archive = root / record['archive']['name']
            subprocess.run(['zstd', '-q', str(tar_path), '-o', str(archive)], check=True)
            evidence = root / 'evidence.json'
            del record['archive']
            evidence.write_text(json.dumps(record))
            output = root / 'metadata'
            command = ['python3', 'scripts/release.py', 'prepare', str(archive),
                       '--evidence', str(evidence), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            actual = json.loads((output / (record['release_id'] + '.json')).read_text())
            release.validate_record(actual)
            self.assertEqual(actual['archive']['size'], archive.stat().st_size)
            self.assertEqual(len(json.loads((output / (archive.name + '.manifest.json')).read_text())),
                             len(release.REQUIRED))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
