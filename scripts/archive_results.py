"""Publish small measured artifacts, excluding local installation paths."""
import hashlib
import json
import tarfile
from pathlib import Path


def main():
    target = Path('data/measured-results.tar.gz')
    with tarfile.open(target, 'w:gz') as tar:
        for directory in ['results/raw/main', 'results/raw/repeat', 'results/raw/smoke',
                          'results/processed/main', 'results/processed/repeat', 'results/processed/smoke']:
            tar.add(directory, arcname=directory)
        tar.add('results/swift-parity.json')
        tar.add('results/repeatability.json')
    files = [target, Path('data/base-image.json')]
    Path('data/SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\n' for p in files))
    print(f'Archive: {target.stat().st_size} bytes')


if __name__ == '__main__':
    main()
