from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

PERFORMANCE_CASES = [
    EvalCase(
        name="quadratic_string_concatenation_in_loop",
        filename="report.py",
        expected_types=[ReviewType.PERFORMANCE, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=["concaten", "join", "immutab", "quadratic", "o(n", "string", "copy"],
        patch=r"""@@ -0,0 +1,5 @@
+def build_report(rows):
+    report = ""
+    for row in rows:
+        report += str(row) + "\n"
+    return report
""",
    ),
    EvalCase(
        name="load_entire_file_instead_of_streaming",
        filename="log_scanner.py",
        expected_types=[ReviewType.PERFORMANCE, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=[
            "memory", "entire file", "whole file", "stream", "line by line",
            "iterat", "large file",
        ],
        patch=r"""@@ -0,0 +1,4 @@
+def find_error_lines(path):
+    with open(path) as f:
+        data = f.read()
+    return [line for line in data.split("\n") if "ERROR" in line]
""",
    ),
]
