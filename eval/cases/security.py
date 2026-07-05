from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

SECURITY_CASES = [
    EvalCase(
        name="hardcoded_api_key",
        filename="openai_client.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        patch=r"""@@ -0,0 +1,7 @@
+import openai
+
+API_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901"
+
+def get_client():
+    openai.api_key = API_KEY
+    return openai
""",
    ),
    EvalCase(
        name="sql_injection_string_concat",
        filename="user_repository.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        patch=r"""@@ -0,0 +1,7 @@
+import sqlite3
+
+def get_user(conn, user_id):
+    cursor = conn.cursor()
+    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
+    cursor.execute(query)
+    return cursor.fetchone()
""",
    ),
    EvalCase(
        name="hardcoded_password",
        filename="db.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        patch=r"""@@ -0,0 +1,11 @@
+import psycopg2
+
+DB_PASSWORD = "SuperSecret123!"
+
+def connect_db():
+    return psycopg2.connect(
+        host="localhost",
+        user="admin",
+        password=DB_PASSWORD,
+        dbname="production",
+    )
""",
    ),
    EvalCase(
        name="path_traversal",
        filename="downloads.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        patch=r"""@@ -0,0 +1,6 @@
+from flask import request
+
+def download():
+    filename = request.args.get("file")
+    with open("/var/app/data/" + filename) as f:
+        return f.read()
""",
    ),
    EvalCase(
        name="subprocess_shell_injection",
        filename="network.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        patch=r"""@@ -0,0 +1,8 @@
+import subprocess
+from flask import request
+
+def ping():
+    host = request.args.get("host")
+    cmd = "ping -c 1 " + host
+    result = subprocess.run(cmd, shell=True, capture_output=True)
+    return result.stdout
""",
    ),
]
