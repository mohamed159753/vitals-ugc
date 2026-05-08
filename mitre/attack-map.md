# MITRE ATT&CK Map — Vitals

## Coverage Summary

| Technique | ID | Tactic | Notes |
|---|---|---|---|
| Network Service Discovery | T1046 | Reconnaissance | nmap reveals ports 22 and 8080 |
| Exploit Public-Facing Application | T1190 | Initial Access | SQL injection via `/api/patients/search?name=` — unsafe string interpolation |
| Valid Accounts | T1078 | Initial Access | Guest JWT obtained from `/api/auth/guest` with zero credentials |
| Access Token Manipulation | T1134 | Privilege Escalation | JWT forged using master secret extracted via SQLi |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution | PostgreSQL `COPY TO PROGRAM` executes reverse shell as `postgres` |
| Abuse Elevation Control Mechanism: Sudo and Sudo Caching | T1548.003 | Privilege Escalation | `postgres ALL=(ALL) NOPASSWD: ALL` — passwordless sudo to root |
| Data from Local System | T1005 | Collection | Flags read from `/home/nurse/local.txt` and `/root/proof.txt` |

## Attack Chain Flow
Reconnaissance     → T1046  — Port scan, service fingerprinting
Initial Access     → T1190  — SQL injection on patient search endpoint
→ T1078  — Guest JWT with no credentials required
Discovery          →        — Swagger UI exposes full API surface (/api/docs)
Credential Access  → T1134  — jwt_master_secret extracted from system_config via UNION SQLi
Privilege Escalation → T1134 — Admin JWT forged, unlocks /api/admin/query
Execution          → T1059.004 — COPY TO PROGRAM reverse shell → postgres shell
Privilege Escalation → T1548.003 — sudo su → root (NOPASSWD misconfiguration)
Collection         → T1005  — local.txt + proof.txt

## Notes

- T1190 and T1078 both apply at Initial Access — the guest JWT alone grants
  access to the vulnerable search endpoint, making both techniques active simultaneously
- The sudoers misconfiguration is narratively justified via the systemd override
  comment (`/etc/systemd/system/postgresql@14-main.service.d/override.conf`),
  consistent with realistic legacy infrastructure debt
- No CVE is directly exploited — CVE-2025-1094 is thematic inspiration for the
  UTF-8 encoding error behavior surfaced in the search endpoint error response
