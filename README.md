# Vitals — OffSec Proving Grounds UGC Candidate

> A realistic vulnerable healthcare infrastructure VM simulating 
> a misconfigured hospital patient monitoring environment.

## Overview

| Field        | Value                          |
|--------------|-------------------------------|
| OS           | Ubuntu 22.04 LTS               |
| Difficulty   | Intermediate                   |
| CVE          | CVE-2025-1094 (inspired)       |
| Stack        | Flask · PostgreSQL 14.15 · JWT |

## Attack Chain (spoiler-light)

Port scan → Swagger API recon → Guest JWT → SQL injection → 
JWT secret extraction → Admin token forgery → COPY TO PROGRAM RCE → 
sudo misconfiguration → root

## MITRE ATT&CK Coverage

| Technique | ID |
|-----------|----|
| Network Service Discovery | T1046 |
| Exploit Public-Facing Application | T1190 |
| ... | ... |

## What's in this repo

- `app/` — Vulnerable Flask API source
- `build/` — Automated build script + manual build guide
- `docs/` — Full walkthrough and exploit path summary

## Skills Demonstrated

- Offensive: SQL injection, JWT forgery, PostgreSQL COPY TO PROGRAM RCE
- Defensive awareness: MITRE mapping, realistic misconfiguration modeling
- Infrastructure: Ubuntu server hardening (intentionally misconfigured), 
  systemd, UFW, PostgreSQL administration
