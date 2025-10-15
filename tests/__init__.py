import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "ChangeMe!123")
os.environ.setdefault("ALLOW_INSECURE_ADMIN_CREDENTIALS", "1")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
