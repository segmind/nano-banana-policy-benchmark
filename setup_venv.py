#!/usr/bin/env python3
"""Create or safely reuse an isolated environment with the pinned Python version."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'.venv', help='Environment directory (default: .venv beside this script)')
    args = parser.parse_args(argv)
    try:
        expected = (ROOT/'.python-version').read_text(encoding='utf-8').strip()
        current = '.'.join(map(str, sys.version_info[:3]))
        if current != expected:
            print(f'Python {expected} is required; this interpreter is {current}. Run this script with the pinned interpreter.', file=sys.stderr)
            return 2
        target = args.directory.absolute()
        interpreter = target/('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        if target.is_symlink():
            print(f'{target} is a symlink and was left unchanged. Choose another environment directory.', file=sys.stderr)
            return 2
        if target.exists():
            if not (target/'pyvenv.cfg').is_file() or not interpreter.is_file():
                print(f'{target} already exists but is not a virtual environment. It was left unchanged.', file=sys.stderr)
                return 2
        else:
            # ensurepip uses Python's bundled wheel; no dependency download,
            # provider request, credential-file access or pip upgrade is needed.
            venv.EnvBuilder(with_pip=True).create(target)
        result = subprocess.run(
            [str(interpreter), '-I', '-c', "import sys; print('.'.join(map(str, sys.version_info[:3]))); print(sys.prefix != sys.base_prefix)"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        if result.stdout.splitlines() != [expected, 'True']:
            print(f'{target} is not an isolated Python {expected} environment. It was not overwritten; inspect it or choose another directory.', file=sys.stderr)
            return 2
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Environment setup failed: {error}\nCheck that the pinned Python installation includes venv and ensurepip. Existing files are never cleared.', file=sys.stderr)
        return 2
    if sys.platform == 'win32':
        activation = "& '" + str(target/'Scripts/Activate.ps1').replace("'", "''") + "'"
        direct = "& '" + str(interpreter).replace("'", "''") + "'"
    else:
        activation = 'source ' + shlex.quote(str(target/'bin/activate'))
        direct = shlex.quote(str(interpreter))
    print(f'Environment ready: {target}')
    print(f'Activate: {activation}')
    print(f'Or run directly: {direct} benchmark.py models')
    print('The benchmark uses the standard library; no pip install is required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
