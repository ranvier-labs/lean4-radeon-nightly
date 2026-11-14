#!/usr/bin/env python3
# Copyright (c) 2026 Ranvier Systems. All rights reserved.
# Released under Apache 2.0 license as described in the file LICENSE.
"""Build a local discovery index, leaving latest null until a release exists."""
import json
from pathlib import Path
from release import validate_record

records = []
for path in Path('releases').glob('*.json'):
    record = json.loads(path.read_text())
    validate_record(record)
    records.append(record)


def order(record):
    date, _, revision = record['release_id'].removeprefix('nightly-').partition('-rev')
    return date, int(revision or 0)


records.sort(key=order, reverse=True)
Path('_build').mkdir(exist_ok=True)
Path('_build/index.json').write_text(json.dumps({
    'schema_version': 1,
    'latest': records[0]['release_id'] if records else None,
    'releases': records,
}, indent=2) + '\n')
