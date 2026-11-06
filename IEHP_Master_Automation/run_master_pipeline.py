"""Run the IEHP case analysis directly from repo files, without opening Jupyter.

Usage: python run_master_pipeline.py --repo .
Inputs: Two Source E partition CSVs (plain or zipped) plus optional guide sources.
Outputs: analysis_outputs/integrated_iehp_dashboard/*.csv
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from zipfile import ZipFile

import pandas as pd

PART_PATTERN = 'medi-cal-ffs-provider-listing_10_26_26_PART'


def discover_source_e(root: Path):
    """Find exact Source E CSVs; support archives containing split CSV files."""
    found = {}
    for path in root.rglob('*.csv'):
        if PART_PATTERN.lower() in path.name.lower():
            part = 1 if 'part 1' in path.name.lower() else 2 if 'part 2' in path.name.lower() else None
            if part:
                found[part] = ('file', path, None)
    if len(found) < 2:
        for archive in root.rglob('*.zip'):
            # Avoid scanning unrelated result packages, but still support two Source E source archives.
            try:
                with ZipFile(archive) as z:
                    for item in z.namelist():
                        name = Path(item).name.lower()
                        if PART_PATTERN.lower() not in name or not name.endswith('.csv'):
                            continue
                        part = 1 if 'part 1' in name else 2 if 'part 2' in name else None
                        if part and part not in found:
                            found[part] = ('zip', archive, item)
            except Exception as ex:
                print(f'WARNING: could not inspect {archive}: {ex}', file=sys.stderr)
            if len(found) == 2:
                break
    if len(found) != 2:
        raise FileNotFoundError(
            'Expected Source E PART 1 and PART 2 CSVs in repo (or ZIP archives). '
            'Add the source CSV files to the repository and rerun. Found parts: '
            + ', '.join(str(x) for x in sorted(found))
        )
    return found


def load_source_e(found):
    frames = []
    for part in (1, 2):
        mode, path, member = found[part]
        where = str(path) + (f' :: {member}' if member else '')
        print('Reading Source E:', where, flush=True)
        if mode == 'zip':
            with ZipFile(path) as z:
                with z.open(member) as stream:
                    d = pd.read_csv(stream, dtype=str, encoding='cp1252', keep_default_na=False, low_memory=False)
        else:
            d = pd.read_csv(path, dtype=str, encoding='cp1252', keep_default_na=False, low_memory=False)
        d['source_e_partition'] = part
        frames.append(d)
    combined = pd.concat(frames, ignore_index=True)
    print(f'Source E loaded: {len(combined):,} rows; {len(combined.columns)} columns', flush=True)
    return combined


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.', help='Repo root containing input data and scripts')
    ap.add_argument('--require-access', action='store_true', help='Fail if Source A + H access-risk rankings are unavailable')
    args = ap.parse_args()
    root = Path(args.repo).expanduser().resolve()
    core = Path(__file__).resolve().with_name('iehp_master_core.py')
    if not core.is_file():
        raise FileNotFoundError('Missing iehp_master_core.py next to runner')
    e = load_source_e(discover_source_e(root))
    context = {'__name__': '__main__', 'repo_root': root, 'providers_df': e}
    exec(compile(core.read_text(encoding='utf-8'), str(core), 'exec'), context)
    out = root / 'analysis_outputs' / 'integrated_iehp_dashboard'
    readiness = out / '00_SOURCE_READINESS_AND_LIMITATIONS.csv'
    if not readiness.is_file():
        raise RuntimeError(f'No readiness report created: {readiness}')
    report = pd.read_csv(readiness, dtype=str).fillna('')
    a_ready = ((report.source == 'A+H') & (report.status == 'READY')).any()
    e_ready = ((report.source == 'E') & (report.status == 'READY')).any()
    text = [
        '# IEHP automatic run',
        f'- UTC execution time: {datetime.now(timezone.utc).isoformat()}',
        f'- Source E ready: {e_ready}',
        f'- Source A+H access ranking ready: {a_ready}',
        '- FFS provider listing counts are not available appointment capacity.',
        '- Source A population is all Medi-Cal; it does not identify transitioning members.',
        '',
        report.to_markdown(index=False),
    ]
    (out / 'RUN_SUMMARY.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    if args.require_access and not a_ready:
        print('ACCESS ANALYSIS INCOMPLETE: add Sources A and H. See readiness report.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
