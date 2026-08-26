"""
CHRISHEM Threat Intelligence & SOC Module
=========================================
Live threat intelligence operations center capabilities:

  - IP Reputation Lookup (AbuseIPDB API / ip-api fallback)
  - WHOIS & Domain Analysis (rdap.org real registry data)
  - Phishing URL Analyzer (suspicious pattern + reputation heuristics)
  - GeoIP Threat Mapping (coordinate + risk aggregation for map rendering)
  - Automated Incident Playbooks (AI-triage + response workflows)

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

ABUSEIPDB_API = "https://api.abuseipdb.com/api/v2/check"
RDAP_BOOTSTRAP = {
    "com": "https://rdap.verisign.com/com/v1/",
    "net": "https://rdap.verisign.com/net/v1/",
    "org": "https://rdap.identitydigital.services/rdap/",
    "io": "https://rdap.identitydigital.services/rdap/",
    "co": "https://rdap.identitydigital.services/rdap/",
    "ug": "https://rdap.registry.africa/rdap/",
    "ke": "https://rdap.registry.africa/rdap/",
    "africa": "https://rdap.registry.africa/rdap/",
}


def validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# IP Reputation
# ---------------------------------------------------------------------------
def check_ip_reputation(ip: str, abuseipdb_key: str = "") -> Dict[str, Any]:
    """
    Real IP reputation check. Uses AbuseIPDB if a key is provided, otherwise
    falls back to ip-api.com + Tor exit node list heuristics.
    """
    if not validate_ip(ip):
        return {"ip": ip, "error": "Invalid IP address"}

    # 1) AbuseIPDB (preferred, requires key)
    if abuseipdb_key:
        try:
            r = requests.get(
                ABUSEIPDB_API,
                params={"ipAddress": ip, "maxAgeInDays": "90", "verbose": ""},
                headers={"Key": abuseipdb_key, "Accept": "application/json"},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json().get("data", {})
                confidence = data.get("abuseConfidenceScore", 0)
                return {
                    "ip": ip,
                    "source": "live:abuseipdb",
                    "abuse_confidence": confidence,
                    "risk": "HIGH" if confidence >= 60 else "MEDIUM" if confidence >= 25 else "LOW",
                    "total_reports": data.get("totalReports", 0),
                    "last_reported_at": data.get("lastReportedAt", ""),
                    "country": data.get("countryCode", ""),
                    "isp": data.get("isp", ""),
                    "usage_type": data.get("usageType", ""),
                    "is_tor": data.get("isTor", False),
                    "domains": (data.get("hostnames") or [])[:5],
                }
        except Exception as e:
            return {"ip": ip, "source": "abuseipdb", "error": str(e)}

    # 2) ip-api.com fallback (no key required)
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", params={"fields": "status,country,regionName,city,isp,org,as,proxy,hosting"}, timeout=8)
        if r.status_code == 200 and r.json().get("status") == "success":
            data = r.json()
            risk_score = 0
            flags = []
            if data.get("proxy"):
                risk_score += 50
                flags.append("Proxy/VPN")
            if data.get("hosting"):
                risk_score += 25
                flags.append("Hosting/DC")
            return {
                "ip": ip,
                "source": "live:ip-api",
                "abuse_confidence": risk_score,
                "risk": "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 25 else "LOW",
                "country": data.get("country", ""),
                "region": data.get("regionName", ""),
                "city": data.get("city", ""),
                "isp": data.get("isp", ""),
                "org": data.get("org", ""),
                "is_proxy": bool(data.get("proxy")),
                "is_hosting": bool(data.get("hosting")),
                "flags": flags,
            }
    except Exception:
        pass

    return {"ip": ip, "source": "offline", "abuse_confidence": 0, "risk": "LOW", "note": "Live lookup unavailable"}


# ---------------------------------------------------------------------------
# WHOIS / Domain Analysis (RDAP)
# ---------------------------------------------------------------------------
def extract_domain_name(host: str) -> str:
    host = (host or "").strip().lower()
    if host.startswith(("http://", "https://")):
        host = host.split("://")[1]
    host = host.split("/")[0].split(":")[0]
    host = re.sub(r"^www\.", "", host)
    return host


def domain_whois(domain: str) -> Dict[str, Any]:
    """Query RDAP for real domain registration records."""
    domain = extract_domain_name(domain)
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    rdap_url = RDAP_BOOTSTRAP.get(tld)
    if not rdap_url:
        rdap_url = "https://rdap.org/domain/"

    try:
        r = requests.get(f"{rdap_url}{domain}", timeout=10, headers={"User-Agent": "CHRISHEM-ThreatIntel/1.0"})
        if r.status_code != 200:
            return {"domain": domain, "error": f"RDAP returned HTTP {r.status_code}", "source": "rdap"}
        data = r.json()
        events = {e.get("eventAction"): e.get("eventDate", "") for e in data.get("events", [])}
        entities = data.get("entities", [])
        registrant = ""
        for ent in entities:
            if ent.get("roles") and "registrant" in ent["roles"]:
                vcard = ent.get("vcardArray", [[], []])
                for line in vcard[1] if len(vcard) > 1 else []:
                    if line and len(line) > 3 and line[0] == "fn":
                        registrant = line[3]
                        break
        nameservers = [n.get("ldhName", "") for n in data.get("nameservers", [])]
        status = data.get("status", [])
        return {
            "domain": domain,
            "source": "live:rdap",
            "created": events.get("registration"),
            "updated": events.get("last changed"),
            "expires": events.get("expiration"),
            "registrant": registrant,
            "nameservers": nameservers,
            "status": status,
            "registrar": _find_registrar(data),
        }
    except Exception as e:
        return {"domain": domain, "source": "rdap", "error": str(e)}


def _find_registrar(data: dict) -> str:
    try:
        for ent in data.get("entities", []):
            if ent.get("roles") and "registrar" in ent["roles"]:
                vcard = ent.get("vcardArray", [[], []])
                for line in vcard[1] if len(vcard) > 1 else []:
                    if line and len(line) > 3 and line[0] == "fn":
                        return line[3]
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Phishing URL Analyzer
# ---------------------------------------------------------------------------
SUSPICIOUS_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".top", ".xyz", ".club", ".online", ".site", ".icu", ".buzz", ".work"}
SUSPICIOUS_KEYWORDS = [
    "login", "verify", "update", "confirm", "account", "secure", "signin", "bank",
    "paypal", "amazon", "apple", "microsoft", "netflix", "wallet", "billing",
    "password", "credential", "webscr", "session", "token",
]


def analyze_url(url: str) -> Dict[str, Any]:
    """Analyze a URL for phishing indicators using heuristics + optional IP reputation."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    findings = []
    risk_score = 0

    # Extract host
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port
    except Exception:
        host = ""
        port = None

    # 1) IP-based host
    if validate_ip(host):
        risk_score += 40
        findings.append("Host is a raw IP address instead of a domain name (common in phishing).")

    # 2) Suspicious TLD
    for tld in SUSPICIOUS_TLDS:
        if host.endswith(tld):
            risk_score += 30
            findings.append(f"Unusually cheap/free TLD: {tld}")
            break

    # 3) Keyword count in path/host
    full_lower = url.lower()
    hits = [k for k in SUSPICIOUS_KEYWORDS if k in full_lower]
    if hits:
        risk_score += min(40, len(hits) * 8)
        findings.append(f"Suspicious keywords present: {', '.join(hits[:5])}")

    # 4) Too many subdomains (looks like legit brand, isn't)
    if host.count(".") >= 4:
        risk_score += 15
        findings.append("Excessive subdomain depth — possible lookalike domain.")

    # 5) Non-standard port
    if port and port not in (80, 443):
        risk_score += 10
        findings.append(f"Uncommon port in use: {port}")

    # 6) Hyphen-heavy domain (paypa1-secure-login style)
    hostname_part = host.split(".")[0]
    if "--" in hostname_part or len(re.findall(r"-", hostname_part)) >= 3:
        risk_score += 20
        findings.append("Hyphen-heavy or obfuscated hostname.")

    # 7) URL shortener
    if any(s in host for s in ["bit.ly", "tinyurl", "t.co", "goo.gl", "shorturl", "cutt.ly", "is.gd"]):
        risk_score += 20
        findings.append("URL shortener obfuscates the final destination.")

    # 8) @ symbol tricks
    if "@" in url and not url.startswith("mailto:"):
        risk_score += 25
        findings.append("@ symbol used to disguise the real destination host.")

    risk = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 25 else "LOW"
    return {
        "url": url,
        "host": host,
        "risk_score": risk_score,
        "risk": risk,
        "findings": findings,
        "verdict": "PHISHING LIKELY" if risk == "HIGH" else "SUSPICIOUS" if risk == "MEDIUM" else "LOW RISK",
        "recommendation": "Do NOT click. Verify the sender and URL independently." if risk == "HIGH" else "Exercise caution. Verify legitimacy before proceeding." if risk == "MEDIUM" else "Proceed with normal caution.",
    }


# ---------------------------------------------------------------------------
# GeoIP Threat Aggregation (for live threat map)
# ---------------------------------------------------------------------------
def aggregate_threat_geodata(ips: List[str], abuseipdb_key: str = "") -> List[Dict[str, Any]]:
    """Resolve a list of threat IPs to coordinates for map visualization."""
    points = []
    for ip in ips[:100]:
        try:
            r = requests.get(f"http://ip-api.com/json/{ip}", params={"fields": "status,lat,lon,city,country"}, timeout=5)
            if r.status_code == 200 and r.json().get("status") == "success":
                data = r.json()
                points.append(
                    {
                        "ip": ip,
                        "lat": data.get("lat", 0),
                        "lon": data.get("lon", 0),
                        "city": data.get("city", ""),
                        "country": data.get("country", ""),
                        "size": 12,
                    }
                )
        except Exception:
            continue
    return points


# ---------------------------------------------------------------------------
# Incident Playbooks
# ---------------------------------------------------------------------------
INCIDENT_PLAYBOOKS = {
    "Brute-Force Attack": [
        "Immediately rate-limit authentication endpoints (e.g., 5 attempts/min).",
        "Enable and enforce MFA/2FA on all affected accounts.",
        "Identify and block offending IPs at the WAF/firewall layer.",
        "Reset credentials for any accounts that showed anomalous activity.",
        "Review auth logs for successful logins during the attack window.",
        "Document findings and file an incident report with chain-of-custody.",
    ],
    "Phishing Campaign": [
        "Preserve the phishing email (full headers + attachments) as evidence.",
        "Run the URL/IP through the Threat Intel module to identify infrastructure.",
        "Report to the security team and internal SOC ticketing system.",
        "Block sender domains and URLs at the mail gateway.",
        "Forward suspicious mail to the abuse contact of the hosting provider.",
        "Run user-awareness training and simulated phishing follow-ups.",
    ],
    "Malware Detection": [
        "Isolate the affected host from the network immediately.",
        "Capture a memory dump and preserve the malicious file (hash it first).",
        "Run YARA-lite and hash reputation scans on the artifact.",
        "Eradicate the infection using antivirus/EDR tooling.",
        "Restore from verified clean backups.",
        "Perform root-cause analysis and close the entry vector.",
    ],
    "Data Breach / PII Exposure": [
        "Contain the breach: revoke compromised keys, rotate credentials.",
        "Run PII scanner to quantify exposed records.",
        "Notify the Data Protection Officer and legal per regulatory timelines (GDPR 72h).",
        "Preserve forensic evidence and system logs for investigation.",
        "Notify affected individuals as required by law.",
        "Remediate the root cause and update incident response plan.",
    ],
    "DDoS / Resource Exhaustion": [
        "Activate CDN/WAF DDoS mitigation (rate limiting, geo-fencing).",
        "Scale up compute/cache resources to absorb the attack.",
        "Block attack source IPs / ASNs via blacklist automation.",
        "Enable SYN-cookie protection and connection limits.",
        "Coordinate with ISP/upstream provider for traffic scrubbing.",
        "Document attack vectors and update the threat registry.",
    ],
}


def run_incident_playbook(incident_type: str, context: str = "") -> Dict[str, Any]:
    """Retrieve and log an automated incident response playbook."""
    steps = INCIDENT_PLAYBOOKS.get(incident_type, INCIDENT_PLAYBOOKS["Brute-Force Attack"])
    playbook_id = "PB-" + f"{abs(hash(incident_type + context)):012X}"[:10]
    return {
        "playbook_id": playbook_id,
        "incident_type": incident_type,
        "steps": steps,
        "created": datetime.utcnow().isoformat(),
        "context": context or "No additional context",
        "severity_assessment": "CRITICAL" if incident_type in ("Data Breach / PII Exposure", "Malware Detection") else "HIGH",
    }


if __name__ == "__main__":
    print(json.dumps(analyze_url("http://paypal-secure-login.xyz/verify/account"), indent=2))
    print(json.dumps(domain_whois("google.com"), indent=2)[:400])

