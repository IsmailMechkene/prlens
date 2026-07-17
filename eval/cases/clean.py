from eval.runner import EvalCase
from prlens.models.review import Severity

CLEAN_CASES = [
    EvalCase(
        name="clean_error_handling",
        filename="math_utils.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,5 @@
+def divide(numerator: float, denominator: float) -> float:
+    'Return numerator / denominator; raise ValueError if denominator is zero.'
+    if denominator == 0:
+        raise ValueError("denominator must not be zero")
+    return numerator / denominator
""",
    ),
    EvalCase(
        name="clean_dataclass",
        filename="geometry.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,9 @@
+from dataclasses import dataclass
+
+@dataclass
+class Point:
+    x: float
+    y: float
+
+    def distance_to(self, other: "Point") -> float:
+        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
""",
    ),
    EvalCase(
        name="clean_pure_calculation",
        filename="temperature.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,3 @@
+def celsius_to_fahrenheit(celsius: float) -> float:
+    'Convert a temperature from Celsius to Fahrenheit.'
+    return celsius * 9 / 5 + 32
""",
    ),
    EvalCase(
        name="clean_safe_subprocess_no_shell",
        filename="network_utils.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,6 @@
+import subprocess
+
+def ping_host(host: str) -> str:
+    'Ping a host once and return the raw output.'
+    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=5)
+    return result.stdout
""",
    ),
    EvalCase(
        name="clean_parameterized_sql_query",
        filename="user_repository_safe.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,5 @@
+def get_user_by_email(conn, email: str):
+    'Look up a single user row by email using a parameterized query.'
+    cursor = conn.cursor()
+    cursor.execute("SELECT id, email, name FROM users WHERE email = ?", (email,))
+    return cursor.fetchone()
""",
    ),
    EvalCase(
        name="clean_recursive_factorial",
        filename="math_recursive.py",
        expected_types=[],
        expected_min_severity=Severity.INFO,
        should_have_comments=False,
        patch=r"""@@ -0,0 +1,7 @@
+def factorial(n: int) -> int:
+    'Return n! for a non-negative integer n.'
+    if n < 0:
+        raise ValueError("n must be non-negative")
+    if n in (0, 1):
+        return 1
+    return n * factorial(n - 1)
""",
    ),
]
