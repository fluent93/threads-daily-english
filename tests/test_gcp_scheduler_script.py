import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "manage_gcp_scheduler.sh"


class GoogleCloudSchedulerScriptTests(unittest.TestCase):
    def test_script_is_valid_bash(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_defines_only_the_two_required_daily_jobs(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"7 8 * * *" "publish"', source)
        self.assertIn('"7 14 * * *" "answer"', source)
        self.assertIn('time-zone "Asia/Seoul"', source)
        self.assertIn("workflow_dispatch", source)
        self.assertIn("--max-retry-attempts 3", source)

    def test_requires_token_without_printing_it(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('if [[ -z "${GITHUB_DISPATCH_TOKEN:-}" ]]', source)
        self.assertNotIn("set -x", source)


if __name__ == "__main__":
    unittest.main()
