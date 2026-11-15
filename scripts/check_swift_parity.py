"""Compile unchanged upstream function bodies with minimal value-type DTOs.

Swift is an optional verification tool, not required by the Python experiment.
No upstream checkout or macOS accessibility permissions are needed.
"""
import hashlib
import json
import random
import subprocess
import tempfile
from pathlib import Path
from load.dataset import trajectory
from sut.history import trim

ROOT = Path(__file__).resolve().parents[1]


def main():
    excerpt = (ROOT / 'vendor/deskhand/history.swift.inc').read_text()
    provenance = json.loads((ROOT / 'vendor/deskhand/provenance.json').read_text())
    assert hashlib.sha256(excerpt.encode()).hexdigest() == provenance['excerpt_sha256']
    source = '''import Foundation
struct ChatMessage: Codable {
    enum Role: String, Codable { case user, assistant, tool, system }
    var role: Role
    var text: String
    var images: [String]
}
struct Options: Codable { var keepTrees: Int; var keepScreenshots: Int }
struct Request: Codable { var messages: [ChatMessage]; var options: Options }
struct Kernel {
    var options: Options
''' + excerpt + '''
}
while let line = readLine() {
    let request = try JSONDecoder().decode(Request.self, from: Data(line.utf8))
    let output = Kernel(options: request.options).trimmedHistory(request.messages)
    let encoded = try JSONEncoder().encode(output)
    print(String(data: encoded, encoding: .utf8)!)
}
'''
    cases = []
    rng = random.Random(20261115)
    for i in range(100):
        cases.append((trajectory(i, rng.randint(1, 25), rng.randint(1, 30), rng.randint(1, 5),
                                 rng.choice([0, 20]), rng.randint(0, 8))[-1], rng.randint(0, 4), rng.randint(0, 2)))
    cases += [([], 3, 1), ([{'role': 'tool', 'text': '', 'images': ['a', 'b']}], 0, 0),
              ([{'role': 'tool', 'text': 'Без заголовка\nAccessibility tree (2):\nя', 'images': []},
                {'role': 'tool', 'text': 'Без заголовка\nAccessibility tree (1):\nю', 'images': []}], 1, 1)]
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)
        (path / 'main.swift').write_text(source)
        subprocess.run(['swiftc', '-module-cache-path', str(path / 'cache'), str(path / 'main.swift'), '-o', str(path / 'oracle')], check=True)
        lines = '\n'.join(json.dumps({'messages': h, 'options': {'keepTrees': t, 'keepScreenshots': s}})
                          for h, t, s in cases) + '\n'
        outputs = subprocess.check_output([str(path / 'oracle')], input=lines, text=True).splitlines()
    assert len(outputs) == len(cases)
    for i, (raw, (history, trees, screenshots)) in enumerate(zip(outputs, cases)):
        assert json.loads(raw) == trim(history, trees, screenshots), f'Mismatch in case {i}'
    result = {'cases': len(cases), 'passed': True, 'excerpt_sha256': provenance['excerpt_sha256'],
              'swift': subprocess.check_output(['swift', '--version'], text=True).strip()}
    (ROOT / 'results/swift-parity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
