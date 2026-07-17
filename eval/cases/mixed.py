from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

MIXED_CASES = [
    EvalCase(
        name="security_and_quality",
        filename="github_api.py",
        # Hardcoded token (security) plus a bare except swallowing errors (quality).
        expected_types=[ReviewType.SECURITY, ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=[
            "hardcod", "token", "secret", "credential",  # the security half
            "except", "bare", "swallow", "silent",       # the quality half
        ],
        patch=r"""@@ -0,0 +1,13 @@
+import requests
+
+TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"
+
+def fetch_repos(user):
+    try:
+        resp = requests.get(
+            f"https://api.github.com/users/{user}/repos",
+            headers={"Authorization": f"token {TOKEN}"},
+        )
+        return resp.json()
+    except:
+        return None
""",
    ),
    EvalCase(
        name="n_plus_one_query",
        filename="orders.py",
        # A query issued per iteration instead of a single batched query.
        expected_types=[ReviewType.PERFORMANCE],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["n+1", "loop", "quer", "batch", "single", "round trip", "per order"],
        patch=r"""@@ -0,0 +1,8 @@
+def get_order_totals(order_ids, db):
+    totals = []
+    for order_id in order_ids:
+        order = db.query("SELECT * FROM orders WHERE id = ?", order_id)
+        items = db.query("SELECT * FROM items WHERE order_id = ?", order_id)
+        total = sum(item.price for item in items)
+        totals.append({"order": order.id, "total": total})
+    return totals
""",
    ),
    EvalCase(
        name="security_and_performance",
        filename="user_search.py",
        # SQL injection via concatenation (security) plus a per-name query loop (performance).
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=["sql injection", "injection", "concaten", "parameteriz", "sanitiz"],
        patch=r"""@@ -0,0 +1,8 @@
+def search_users(db, names):
+    results = []
+    for name in names:
+        query = "SELECT * FROM users WHERE name = '" + name + "'"
+        rows = db.execute(query).fetchall()
+        for row in rows:
+            results.append(row)
+    return results
""",
    ),
    EvalCase(
        name="performance_and_quality_nested_loop_duplication",
        filename="matcher.py",
        # O(n*m) nested-loop lookup duplicated across two near-identical functions.
        expected_types=[ReviewType.PERFORMANCE, ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=[
            "nested loop", "o(n", "quadratic", "set", "complexity",  # the performance half
            "duplicat", "identical", "repeat", "same logic",         # the quality half
        ],
        patch=r"""@@ -0,0 +1,15 @@
+def find_common_items(list_a, list_b):
+    common = []
+    for a in list_a:
+        for b in list_b:
+            if a == b:
+                common.append(a)
+    return common
+
+def find_common_ids(ids_a, ids_b):
+    common = []
+    for a in ids_a:
+        for b in ids_b:
+            if a == b:
+                common.append(a)
+    return common
""",
    ),
    EvalCase(
        name="security_and_style_hardcoded_secret_bad_naming",
        filename="api_client.py",
        # Hardcoded API secret plus inconsistent naming conventions; the secret is
        # the more severe finding.
        #
        # The literal is deliberately a generic hex blob rather than something shaped
        # like a real vendor key. GitHub push protection matches those by prefix and
        # blocks the push, fake value or not — it cannot know a fixture is invented.
        # The field name and the Bearer header are what make this read as a hardcoded
        # credential; the prefix was never load-bearing. Do not "improve" it to look
        # realistic, and do not allowlist the finding to get a push through.
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        expected_keywords=["hardcod", "secret", "api key", "credential", "environment variable"],
        patch=r"""@@ -0,0 +1,8 @@
+class ApiClient:
+    def __init__(self, baseUrl):
+        self.baseUrl = baseUrl
+        self.API_Secret = "4f2b8e91c07d3a65b18e2f7c9d0a3b56"
+
+    def Send(self, payload):
+        headers = {"Authorization": f"Bearer {self.API_Secret}"}
+        return requests.post(self.baseUrl, json=payload, headers=headers)
""",
    ),
]
