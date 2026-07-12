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
]
