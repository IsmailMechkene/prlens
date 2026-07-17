from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

STYLE_CASES = [
    EvalCase(
        name="inconsistent_naming_convention",
        filename="account.py",
        expected_types=[ReviewType.STYLE, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=[
            "camelcase", "camel case", "pascalcase", "pascal case", "snake_case",
            "snake case", "pep 8", "pep8", "naming", "convention",
        ],
        patch=r"""@@ -0,0 +1,7 @@
+class UserAccount:
+    def __init__(self, userName, account_balance):
+        self.userName = userName
+        self.AccountBalance = account_balance
+
+    def GetBalance(self):
+        return self.AccountBalance
""",
    ),
    EvalCase(
        name="non_descriptive_variable_names",
        filename="calc.py",
        expected_types=[ReviewType.STYLE, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=[
            "descriptive", "meaningful", "variable name", "naming", "single-letter",
            "single letter", "unclear", "rename",
        ],
        patch=r"""@@ -0,0 +1,5 @@
+def calc(a, b, c):
+    x = a * b
+    y = x + c
+    z = y / 2
+    return z
""",
    ),
]
