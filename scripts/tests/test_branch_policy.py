"""Exercise the actual workflow shell, without copying its branch regex."""
import os
from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BranchPolicyTests(unittest.TestCase):
    def test_main_workflow_and_compatibility_base(self):
        workflow = (ROOT / '.github/workflows/gitflow.yml').read_text()
        command = textwrap.dedent(workflow.split('        run: |\n', 1)[1])
        cases = [
            ('main', 'feature/avatar-presentation', True),
            ('main', 'feature/telemetry-turns', True),
            ('main', 'chore/branch-cleanup', True),
            ('main', 'bugfix/audio', True),
            ('main', 'release/1.1.0', True),
            ('main', 'hotfix/1.1.1', True),
            ('main', 'feature/gemini-live-api+MVP', False),
            ('main', 'backup-fase-2', False),
            ('main', 'release/next', False),
            ('backp-fase1', 'main', True),
            ('backp-fase1', 'feature/avatar-presentation', False),
            ('develop', 'feature/avatar-presentation', False),
        ]
        for base, head, expected in cases:
            with self.subTest(base=base, head=head):
                result = subprocess.run(
                    ['bash', '-c', command], capture_output=True, text=True,
                    env={**os.environ, 'BASE_REF': base, 'HEAD_REF': head},
                )
                self.assertEqual(result.returncode == 0, expected, result.stdout)
