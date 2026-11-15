"""Record host, Git and actual Docker image identities before running."""
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def call(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    info = {'mode': 'local' if args.local else 'docker', 'host': platform.platform(),
            'machine': platform.machine(), 'processor': platform.processor(),
            'git_commit': call('git', 'rev-parse', 'HEAD'),
            'git_dirty': bool(call('git', 'status', '--porcelain')),
            'git_diff_sha256': hashlib.sha256(call('git', 'diff', 'HEAD').encode()).hexdigest()}
    if platform.system() == 'Darwin':
        info['hardware'] = {k: call('sysctl', '-n', k) for k in ['hw.model', 'hw.memsize', 'hw.ncpu', 'machdep.cpu.brand_string']}
    if not args.local:
        info['docker_version'] = json.loads(call('docker', 'version', '--format', '{{json .}}'))
        docker_info = json.loads(call('docker', 'info', '--format', '{{json .}}'))
        info['docker_info'] = {k: docker_info[k] for k in ['ServerVersion', 'NCPU', 'MemTotal', 'OperatingSystem', 'KernelVersion', 'Architecture']}
        images = json.loads(call('docker', 'image', 'inspect', 'pyweb34-bench:1'))
        info['images'] = [{k: image[k] for k in ['Id', 'RepoTags', 'RepoDigests', 'Architecture', 'Os']} for image in images]
    Path('results').mkdir(exist_ok=True)
    Path('results/environment.json').write_text(json.dumps(info, indent=2) + '\n')


if __name__ == '__main__':
    main()
