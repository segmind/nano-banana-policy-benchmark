"""Offline checks for safe, repeatable environment setup."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import setup_venv as setup


class EnvironmentSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.version = '.'.join(map(str, sys.version_info[:3]))
        (self.root/'.python-version').write_text(self.version)
        root_patch = patch.object(setup, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def invoke(self, args=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = setup.main(args or [])
        return code, stdout.getvalue(), stderr.getvalue()

    def make_environment(self, target, windows=None):
        if windows is None:
            windows = sys.platform == 'win32'
        target.mkdir(parents=True)
        (target/'pyvenv.cfg').write_text('include-system-site-packages = false\n')
        interpreter = target/('Scripts/python.exe' if windows else 'bin/python')
        interpreter.parent.mkdir()
        interpreter.write_bytes(b'Interpreter mocked in this test')

    def test_wrong_python_stops_before_creating_or_running_anything(self):
        (self.root/'.python-version').write_text('0.0.0')
        with patch.object(setup.venv, 'EnvBuilder') as builder, patch.object(setup.subprocess, 'run') as run:
            code, _, stderr = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn('Python 0.0.0 is required', stderr)
        builder.assert_not_called()
        run.assert_not_called()
        self.assertFalse((self.root/'.venv').exists())

    def test_new_environment_uses_bundled_pip_and_leaves_credentials_untouched(self):
        secret_file = self.root/'.env'
        secret_file.write_text('Private fixture must stay untouched\n')
        target = self.root/'environment with spaces'
        result = subprocess.CompletedProcess([], 0, self.version+'\nTrue\n', '')
        with patch.object(setup.venv, 'EnvBuilder') as builder, patch.object(setup.subprocess, 'run', return_value=result) as run:
            builder.return_value.create.side_effect = self.make_environment
            code, stdout, stderr = self.invoke(['--directory', str(target)])
        self.assertEqual(code, 0, stderr)
        builder.assert_called_once_with(with_pip=True)
        builder.return_value.create.assert_called_once_with(target)
        self.assertEqual(run.call_args.args[0][1], '-I')
        activation = target/('Scripts/Activate.ps1' if sys.platform == 'win32' else 'bin/activate')
        self.assertIn(str(activation), stdout)
        self.assertEqual(secret_file.read_text(), 'Private fixture must stay untouched\n')

    def test_existing_environment_is_checked_and_reused_without_overwriting_files(self):
        target = self.root/'.venv'
        self.make_environment(target)
        marker = target/'keep.txt'
        marker.write_text('Keep existing contents')
        result = subprocess.CompletedProcess([], 0, self.version+'\nTrue\n', '')
        with patch.object(setup.venv, 'EnvBuilder') as builder, patch.object(setup.subprocess, 'run', return_value=result):
            code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        builder.assert_not_called()
        self.assertEqual(marker.read_text(), 'Keep existing contents')

    def test_existing_non_environment_directory_is_not_modified(self):
        target = self.root/'.venv'
        target.mkdir()
        (target/'keep.txt').write_text('Keep this')
        with patch.object(setup.venv, 'EnvBuilder') as builder, patch.object(setup.subprocess, 'run') as run:
            code, _, stderr = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn('left unchanged', stderr)
        self.assertEqual((target/'keep.txt').read_text(), 'Keep this')
        builder.assert_not_called()
        run.assert_not_called()

    def test_wrong_version_or_nonisolated_existing_python_is_rejected(self):
        self.make_environment(self.root/'.venv')
        for output in ['0.0.0\nTrue\n', self.version+'\nFalse\n']:
            result = subprocess.CompletedProcess([], 0, output, '')
            with self.subTest(output=output), patch.object(setup.venv, 'EnvBuilder') as builder, patch.object(setup.subprocess, 'run', return_value=result):
                code, _, stderr = self.invoke()
                self.assertEqual(code, 2)
                self.assertIn('not overwritten', stderr)
                builder.assert_not_called()

    def test_creation_failure_explains_venv_and_ensurepip_without_clearing_files(self):
        with patch.object(setup.venv, 'EnvBuilder') as builder:
            builder.return_value.create.side_effect = subprocess.CalledProcessError(1, 'ensurepip')
            code, _, stderr = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn('venv and ensurepip', stderr)
        self.assertIn('never cleared', stderr)

    def test_windows_commands_quote_paths_without_changing_execution_policy(self):
        target = self.root/"Steve's environment"
        self.make_environment(target, windows=True)
        result = subprocess.CompletedProcess([], 0, self.version+'\nTrue\n', '')
        with patch.object(setup.sys, 'platform', 'win32'), patch.object(setup.subprocess, 'run', return_value=result) as run:
            code, stdout, stderr = self.invoke(['--directory', str(target)])
        self.assertEqual(code, 0, stderr)
        self.assertIn("Steve''s environment", stdout)
        self.assertIn(str(target/'Scripts/Activate.ps1').replace("'", "''"), stdout)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('ExecutionPolicy', stdout)


if __name__ == '__main__':
    unittest.main()
