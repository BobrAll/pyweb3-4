import hashlib
import io
import json
import tarfile
from pathlib import Path


def main():
    for line in Path('data/SHA256SUMS').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if checksum != actual:
            raise SystemExit(f'Checksum mismatch: {name}')
    with tarfile.open('data/measured-results.tar.gz', 'r:gz') as tar:
        for batch in ['main', 'repeat', 'smoke']:
            prefix = f'results/raw/{batch}/'
            records = []
            for member in tar.getmembers():
                if member.name.startswith(prefix) and member.isfile() and member.name.endswith('.json'):
                    data = json.load(tar.extractfile(member))
                    if 'manifest' in data: records.append(data)
            expected = 20 if batch == 'smoke' else 130
            assert len(records) == expected, (batch, len(records))
            assert all(s['invariants_ok'] for record in records for s in record['samples'])
            print(f'{batch}: {len(records)} runs, invariants OK')
    print('Archive SHA-256 verified')


if __name__ == '__main__':
    main()
