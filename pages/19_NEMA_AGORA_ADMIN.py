"""NEMA-AGORA administrative operations console.

Admin-only controls for database health, verified SQLite backups, bounded
retention and explicitly confirmed restore. This is not an official NEMA
administration interface.
"""
from __future__ import annotations

from datetime import datetime
import pandas as pd
import streamlit as st

from nema_agora.auth import principal_from_streamlit_user
from nema_agora.backup import backup_database, integrity_check, list_backups, prune_backups, restore_database
from nema_agora.config import backup_dir_from_secrets, backup_retention_from_secrets, database_path_from_secrets, mode_from_secrets
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository
from nema_agora.access import has_permission

st.set_page_config(page_title="NEMA-AGORA Admin", page_icon="🛡️", layout="wide")

st.title("🛡️ NEMA-AGORA Operations Console")
st.caption("Independent student-led prototype — administrative controls are not official NEMA controls.")
st.warning("Use only on an approved deployment. Restore replaces the configured database and must be treated as a destructive operational action.")

mode = mode_from_secrets(st.secrets)
if mode != "persistent":
    st.info("Admin operations are unavailable in demo mode. Persistent mode must be explicitly configured.")
    st.stop()

principal = principal_from_streamlit_user(st.user, st.secrets)
if principal is None:
    st.error("Authentication is required.")
    if hasattr(st, "login") and st.button("Sign in", type="primary"):
        st.login()
    st.stop()

if not principal.is_authorised or not has_permission(principal.role, "user:manage"):
    st.error("Access denied. This console is restricted to the admin role.")
    if hasattr(st, "logout") and st.button("Sign out"):
        st.logout()
    st.stop()

database_path = database_path_from_secrets(st.secrets)
backup_dir = backup_dir_from_secrets(st.secrets)
retention = backup_retention_from_secrets(st.secrets)
if database_path is None or backup_dir is None or retention is None:
    st.error("Configure database_path, backup_dir and backup_retention before using this console.")
    st.stop()

service = NemaAgoraService(NemaAgoraRepository(database_path))
now = datetime.now().astimezone().isoformat(timespec="seconds")

st.subheader("System health")
c1, c2, c3 = st.columns(3)
c1.metric("Database", "Healthy" if integrity_check(database_path) else "FAILED")
backups = list_backups(backup_dir)
c2.metric("Verified backups", len(backups))
c3.metric("Retention target", retention)

if database_path.exists():
    st.caption(f"Database: {database_path}")
st.caption(f"Backup directory: {backup_dir}")

st.divider()
st.subheader("Backup")
if st.button("Create verified backup", type="primary", use_container_width=True):
    try:
        created = backup_database(database_path, backup_dir)
        removed = prune_backups(backup_dir, keep=retention)
        service.record_operation(
            principal, operation="backup_created", occurred_at=now,
            details={"backup": created.name, "pruned": [p.name for p in removed]},
        )
        st.success(f"Verified backup created: {created.name}")
        st.rerun()
    except (OSError, ValueError, FileNotFoundError) as exc:
        st.error(str(exc))

st.divider()
st.subheader("Restore")
backups = list_backups(backup_dir)
if not backups:
    st.info("No recognised backups are available.")
else:
    selected_backup = st.selectbox("Verified backup", backups, format_func=lambda p: p.name)
    st.caption("The selected backup is checked with SQLite integrity_check before restore.")
    confirm = st.checkbox("I understand this will replace the configured database with the selected backup.")
    if st.button("Restore selected backup", type="secondary", disabled=not confirm, use_container_width=True):
        try:
            safety = backup_database(database_path, backup_dir)
            restore_database(selected_backup, database_path, confirm_destructive=True)
            service.record_operation(
                principal, operation="database_restored", occurred_at=now,
                details={"source_backup": selected_backup.name, "pre_restore_safety_backup": safety.name},
            )
            st.success(f"Database restored from {selected_backup.name}. Safety backup: {safety.name}")
            st.rerun()
        except (OSError, ValueError, FileNotFoundError, PermissionError) as exc:
            st.error(str(exc))

st.divider()
st.subheader("Backup inventory")
backups = list_backups(backup_dir)
if backups:
    st.dataframe(
        pd.DataFrame([{"backup": p.name, "size_bytes": p.stat().st_size, "verified": integrity_check(p)} for p in backups]),
        use_container_width=True, hide_index=True,
    )

st.divider()
st.subheader("Administrative audit")
events = service.list_operation_events(principal, limit=100)
if events:
    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
else:
    st.info("No administrative operations have been recorded yet.")

st.caption("Administrative events are stored in the same SQLite database. Production deployments should protect database access and maintain an independent backup/audit strategy.")
