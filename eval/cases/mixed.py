from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

MIXED_CASES = [
    EvalCase(
        name="security_and_quality",
        filename="github_api.py",
        # Hardcoded token (security) plus a bare except swallowing errors (quality).
        expected_types=[ReviewType.SECURITY, ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
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
]
