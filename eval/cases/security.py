from eval.runner import EvalCase
from prlens.models.review import ReviewType, Severity

SECURITY_CASES = [
    EvalCase(
        name="hardcoded_api_key",
        filename="openai_client.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        expected_keywords=["hardcod", "api key", "secret", "credential", "environment variable"],
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
        expected_keywords=["sql injection", "injection", "parameteriz", "concaten", "sanitiz"],
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
        expected_keywords=["hardcod", "password", "credential", "secret", "environment variable"],
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
        expected_keywords=["travers", "../", "arbitrary file", "sanitiz", "validat", "path"],
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
        expected_keywords=["shell", "command injection", "injection", "arbitrary command", "sanitiz"],
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
    EvalCase(
        name="insecure_deserialization_pickle",
        filename="session.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.CRITICAL,
        expected_keywords=["pickle", "deserializ", "untrusted", "arbitrary code", "rce"],
        patch=r"""@@ -0,0 +1,4 @@
+import pickle
+
+def load_session(raw_cookie):
+    return pickle.loads(raw_cookie)
""",
    ),
    EvalCase(
        name="weak_hash_for_password",
        filename="auth.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=["md5", "weak", "hash", "bcrypt", "argon", "salt", "collision"],
        patch=r"""@@ -0,0 +1,4 @@
+import hashlib
+
+def hash_password(password):
+    return hashlib.md5(password.encode()).hexdigest()
""",
    ),
    EvalCase(
        name="ssrf_unvalidated_url_fetch",
        filename="preview.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=["ssrf", "server-side request", "url", "validat", "internal", "allowlist", "whitelist"],
        patch=r"""@@ -0,0 +1,6 @@
+import requests
+from flask import request
+
+def fetch_preview():
+    url = request.args.get("url")
+    return requests.get(url).content
""",
    ),
    EvalCase(
        name="disabled_tls_verification",
        filename="http_client.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=["verify", "tls", "ssl", "certificate", "man-in-the-middle", "mitm", "interception"],
        patch=r"""@@ -0,0 +1,4 @@
+import requests
+
+def fetch_data(url):
+    return requests.get(url, verify=False)
""",
    ),
    EvalCase(
        name="xss_unescaped_template",
        filename="greeting.py",
        expected_types=[ReviewType.SECURITY],
        expected_min_severity=Severity.ERROR,
        expected_keywords=["xss", "cross-site", "escap", "sanitiz", "inject", "template"],
        patch=r"""@@ -0,0 +1,5 @@
+from flask import request, render_template_string
+
+def greet():
+    name = request.args.get("name")
+    return render_template_string("<h1>Hello " + name + "</h1>")
""",
    ),
]
