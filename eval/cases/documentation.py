from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

DOCUMENTATION_CASES = [
    EvalCase(
        name="missing_docstring_public_api",
        filename="payment.py",
        expected_types=[ReviewType.DOCUMENTATION, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=["docstring", "documentation", "document", "undocumented"],
        patch=r"""@@ -0,0 +1,8 @@
+class PaymentProcessor:
+    def charge(self, amount, currency, customer_id):
+        gateway = self._get_gateway(currency)
+        return gateway.submit(amount, customer_id)
+
+    def refund(self, transaction_id, amount):
+        gateway = self._get_gateway_for_transaction(transaction_id)
+        return gateway.reverse(transaction_id, amount)
""",
    ),
    EvalCase(
        name="misleading_comment_out_of_sync",
        filename="users.py",
        expected_types=[ReviewType.DOCUMENTATION, ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=[
            "comment", "misleading", "inaccurate", "does not match", "doesn't match",
            "inconsistent", "contradic", "30 days", "out of date",
        ],
        patch=r"""@@ -0,0 +1,3 @@
+def get_active_users(users):
+    # Returns only users created in the last 30 days
+    return [u for u in users if u["status"] == "active"]
""",
    ),
]
