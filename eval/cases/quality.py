from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

QUALITY_CASES = [
    EvalCase(
        name="deep_nesting_long_function",
        filename="order_processing.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["nest", "complex", "readab", "refactor", "indent", "extract"],
        patch=r"""@@ -0,0 +1,15 @@
+def process_orders(orders):
+    results = []
+    for order in orders:
+        if order.get("status") == "active":
+            for item in order.get("items", []):
+                if item.get("quantity", 0) > 0:
+                    if item.get("price", 0) > 0:
+                        for discount in item.get("discounts", []):
+                            if discount.get("valid"):
+                                if discount.get("percent", 0) > 0:
+                                    total = item["price"] * item["quantity"]
+                                    total = total * (1 - discount["percent"] / 100)
+                                    if total > 0:
+                                        results.append(total)
+    return results
""",
    ),
    EvalCase(
        name="code_duplication",
        filename="tax.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["duplicat", "identical", "repeat", "dry", "same logic", "shared"],
        patch=r"""@@ -0,0 +1,15 @@
+def calculate_us_tax(amount):
+    if amount < 0:
+        raise ValueError("Amount must be positive")
+    rate = 0.07
+    tax = amount * rate
+    total = amount + tax
+    return round(total, 2)
+
+def calculate_eu_tax(amount):
+    if amount < 0:
+        raise ValueError("Amount must be positive")
+    rate = 0.07
+    tax = amount * rate
+    total = amount + tax
+    return round(total, 2)
""",
    ),
    EvalCase(
        name="bare_except_pass",
        filename="config_loader.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["except", "bare", "silent", "swallow", "exception", "hide"],
        patch=r"""@@ -0,0 +1,8 @@
+import json
+
+def load_config(path):
+    try:
+        with open(path) as f:
+            return json.load(f)
+    except:
+        pass
""",
    ),
    EvalCase(
        name="god_function",
        filename="signup.py",
        # The function is a genuine grab-bag of responsibilities, but its most
        # severe findings are security issues (SQL injection, weak hashing,
        # unauthenticated SMTP). Accept either QUALITY or SECURITY as a pass.
        expected_types=[ReviewType.QUALITY, ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=[
            "responsib", "concern", "too many", "refactor", "separat",  # the quality reading
            "injection", "sha256", "hash", "smtp", "sanitiz",           # the security reading
        ],
        patch=r"""@@ -0,0 +1,32 @@
+def handle_signup(request):
+    # parse request
+    data = json.loads(request.body)
+    email = data["email"]
+    password = data["password"]
+
+    # validate
+    if "@" not in email:
+        return {"error": "invalid email"}
+    if len(password) < 8:
+        return {"error": "weak password"}
+
+    # hash password
+    hashed = hashlib.sha256(password.encode()).hexdigest()
+
+    # write to database
+    conn = sqlite3.connect("app.db")
+    conn.execute("INSERT INTO users (email, pw) VALUES (?, ?)", (email, hashed))
+    conn.commit()
+
+    # send welcome email
+    smtp = smtplib.SMTP("localhost")
+    smtp.sendmail("noreply@app.com", email, "Welcome!")
+    smtp.quit()
+
+    # write analytics log
+    with open("analytics.log", "a") as f:
+        f.write(f"signup:{email}\n")
+
+    # generate report
+    report = {"total_users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]}
+    return {"status": "ok", "report": report}
""",
    ),
    EvalCase(
        name="mutable_default_argument",
        filename="cart.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["mutable", "default argument", "default value", "shared", "none"],
        patch=r"""@@ -0,0 +1,3 @@
+def add_item(item, items=[]):
+    items.append(item)
+    return items
""",
    ),
    EvalCase(
        name="magic_numbers_no_constants",
        filename="shipping.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=["magic number", "magic", "constant", "hardcod", "literal"],
        patch=r"""@@ -0,0 +1,7 @@
+def calculate_shipping(weight):
+    if weight > 50:
+        return weight * 4.75 + 12.99
+    elif weight > 20:
+        return weight * 3.25 + 8.5
+    else:
+        return weight * 2.1 + 4.99
""",
    ),
    EvalCase(
        name="unused_variables_dead_code",
        filename="payments.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.INFO,
        expected_keywords=["unused", "dead code", "never used", "not used", "no effect", "redundant"],
        patch=r"""@@ -0,0 +1,7 @@
+def process_payment(amount, currency):
+    tax_rate = 0.08
+    discount = 0.1
+    processed_amount = amount
+    if currency == "USD":
+        processed_amount = amount * 1.0
+    return processed_amount
""",
    ),
    EvalCase(
        name="overly_broad_exception_handling",
        filename="profile.py",
        expected_types=[ReviewType.QUALITY],
        expected_min_severity=Severity.WARNING,
        expected_keywords=["broad", "exception", "swallow", "silent", "generic", "specific", "hide"],
        patch=r"""@@ -0,0 +1,5 @@
+def fetch_user_profile(user_id, db):
+    try:
+        return db.get_profile(user_id)
+    except Exception:
+        return None
""",
    ),
]
