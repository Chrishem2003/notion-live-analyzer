"""
Run this ONCE from your project root after the setup script has copied
modules/auth_store.py into place:

    python create_first_admin.py

It only works if the auth_users table is empty, so it can't be reused
to mint a second admin later. Delete this file (or at least the
password) afterward.
"""
import getpass
from modules import auth_store

email = input("Admin email: ").strip()
name = input("Admin display name: ").strip()
password = getpass.getpass("Admin password: ")

result = auth_store.bootstrap_first_admin(email, name, password)
if result["ok"]:
    print(f"✅ Admin account created for {email}. You can now sign in through portal.py.")
else:
    print(f"❌ {result['error']}")
