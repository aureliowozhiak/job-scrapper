#!/usr/bin/env python3
"""Utility to generate password hashes for admin authentication."""
import sys
from passlib.hash import bcrypt


def main():
    """Generate a bcrypt hash for a password."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_password_hash.py <password>")
        print("\nExample:")
        print("  python scripts/generate_password_hash.py mySecurePassword123")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = bcrypt.hash(password)
    
    print(f"\nPassword: {password}")
    print(f"Hash: {hashed}")
    print("\nAdd this hash to your .env file:")
    print(f"ADMIN_PASSWORD_HASH={hashed}")


if __name__ == "__main__":
    main()
