"""运行全部测试并保存可核查的 JSON 与文本结果。"""

import io
import hashlib
import json
import platform
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test.id())


def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    stream = io.StringIO()
    start = perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    elapsed = perf_counter() - start
    log = stream.getvalue()
    (reports / "tests.txt").write_text(log, encoding="utf-8")
    data = {
        "run_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "python": sys.version, "platform": platform.platform(),
        "tests_run": result.testsRun, "passed": len(result.passed),
        "elapsed_seconds": elapsed, "passed_tests": result.passed,
        "failures": [(test.id(), error) for test, error in result.failures],
        "errors": [(test.id(), error) for test, error in result.errors],
        "successful": result.wasSuccessful(),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [ROOT / "Myapp.py", *sorted((ROOT / "quiz").glob("*.py")),
                         *sorted((ROOT / "tests").glob("*.py"))]
        },
    }
    (reports / "tests.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(log)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
