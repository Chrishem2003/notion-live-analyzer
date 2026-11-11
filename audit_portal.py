"""Compatibility shim for the canonical, hardened audit portal module.

Keep legacy imports working while ensuring encryption and password policy have
one implementation. New code should import from :mod:`modules.audit_portal`.
"""
from modules.audit_portal import *  # noqa: F401,F403
from modules.audit_portal import LEGACY_SALT as CHRISHEM_SALT
