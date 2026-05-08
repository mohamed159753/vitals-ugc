# Vitals — OffSec Proving Grounds UGC Candidate

> A realistic vulnerable healthcare infrastructure VM simulating a misconfigured  
> hospital patient monitoring environment. Built for the OffSec Proving Grounds  
> User-Generated Content program.

---

## Overview

| Field       | Value                           |
|-------------|---------------------------------|
| OS          | Ubuntu 22.04 LTS                |
| Difficulty  | Intermediate                    |
| CVE         | CVE-2025-1094 (inspired)        |
| Stack       | Flask · PostgreSQL 14.15 · JWT  |
| Theme       | Hospital patient monitoring API |
| Ports       | 22 (SSH), 8080 (HTTP)           |

---

## Attack Chain

```
Port scan
  → Swagger UI recon (/api/docs)
    → Guest JWT (no credentials required)
      → SQL injection on /api/patients/search
        → jwt_master_secret extracted from system_config
          → Admin JWT forged
            → COPY TO PROGRAM RCE → postgres shell
              → Passwordless sudo misconfiguration → root
```

---

## MITRE ATT&CK Coverage

| Technique | ID | Tactic |
|---|---|---|
| Network Service Discovery | T1046 | Reconnaissance |
| Exploit Public-Facing Application | T1190 | Initial Access |
| Valid Accounts | T1078 | Initial Access |
| Access Token Manipulation | T1134 | Privilege Escalation |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution |
| Abuse Elevation Control Mechanism: Sudo and Sudo Caching | T1548.003 | Privilege Escalation |
| Data from Local System | T1005 | Collection |

---

## Vulnerabilities

### 1 — SQL Injection (Initial Access → Credential Theft)
The `/api/patients/search?name=` endpoint constructs its query via unsafe string 
interpolation instead of parameterized queries:

```python
query = "SELECT id, name, ward, condition FROM patients WHERE name ILIKE '%%%s%%'" % name
```

A UNION-based payload extracts the `jwt_master_secret` from the `system_config` table,
which is the pivot point for the entire chain. The error response leaks PostgreSQL 
encoding details consistent with CVE-2025-1094's UTF-8 handling behavior.

### 2 — JWT Secret Exposure → Token Forgery
The master JWT secret is stored in the database rather than in an environment variable
or secrets manager. Once extracted via SQLi, it allows forging an admin-role token
that unlocks the raw SQL execution endpoint.

### 3 — Unauthenticated Guest Access to Sensitive Endpoints
`/api/auth/guest` issues a valid JWT with no credentials. The guest token is sufficient
to reach the vulnerable search endpoint — no prior foothold required.

### 4 — PostgreSQL COPY TO PROGRAM (RCE)
The `/api/admin/query` endpoint executes raw SQL with no query restrictions. PostgreSQL's
`COPY TO PROGRAM` feature executes OS commands as the `postgres` service user, yielding
a reverse shell directly from SQL.

### 5 — Passwordless Sudo Misconfiguration (Privilege Escalation)
The `postgres` OS account is granted unrestricted passwordless sudo:

```
postgres ALL=(ALL) NOPASSWD: ALL
```

The misconfiguration is narratively justified by a legacy systemd override comment
referencing an incomplete hardware migration — realistic infrastructure debt that
players discover via database enumeration in `system_notes`.

---

## Exploitation Skills Covered

- API enumeration via Swagger/OpenAPI documentation
- JWT structure analysis and token forgery (HS256)
- UNION-based SQL injection for cross-table data extraction
- PostgreSQL `COPY TO PROGRAM` for OS command execution
- Privilege escalation via misconfigured passwordless sudo
- Realistic enumeration chaining (DB notes → sudo hint → root)

---

## Repository Structure

```
vitals-ugc/
├── README.md
├── app/
│   └── app.py              # Vulnerable Flask API
├── build/
│   ├── build.py            # Automated build script (run as root)
│   └── buildguide.md       # Step-by-step manual build guide
├── docs/
│   ├── walkthrough.md      # Full exploitation walkthrough
│   └── summary.md          # Attack chain overview
└── mitre/
    └── attack-map.md       # MITRE ATT&CK mapping with notes
```

---

## Build Requirements

| Component | Spec |
|---|---|
| Hypervisor | VMware Workstation Player / Pro |
| Base ISO | Ubuntu 22.04 Server |
| CPU / RAM / Disk | 1 vCPU · 1024 MB · 20 GB |
| Network | Internet access required during build |

See `build/buildguide.md` for the full step-by-step process,  
or run `build/build.py` as root on a fresh Ubuntu 22.04 install.

---

## Credentials (Build Reference)

| Service | Username | Password |
|---|---|---|
| OS | nurse | Vitals2024! |
| PostgreSQL | postgres | vitals_pg_2024 |
| App (guest JWT secret) | — | guest_static_key_2024 |

> These credentials are intentionally embedded in the VM as part of the challenge design.

---

## Notes

- The `.ova` machine image is not included in this repository
- Flags (`local.txt`, `proof.txt`) are dynamically generated at build time via MD5
- PostgreSQL 14.15 is pinned via `apt-mark hold` to preserve CVE-2025-1094 relevance
- The `vitals-api` systemd service runs as `root` — intentional design choice that
  means the Flask process itself also has elevated access, adding a secondary path
  for players who think laterally
