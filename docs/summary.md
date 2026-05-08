# Vitals — Exploit Path Summary

## Attack Chain Overview

1. **Port scan** reveals port 8080 running a Flask REST API
2. **API recon** via `/api/docs` Swagger UI exposes all endpoints
3. **Guest JWT** obtained from `/api/auth/guest` with no credentials
4. **SQL injection** via `/api/patients/search?name=` using UNION-based payload extracts `jwt_master_secret` from `system_config` table
5. **JWT forgery** using extracted secret to create admin-role token
6. **RCE** via `/api/admin/query` using PostgreSQL `COPY TO PROGRAM` — executes OS commands as `postgres` user
7. **Privilege escalation** via misconfigured passwordless sudo on `postgres` account — `sudo su` yields root shell
8. **Flags** read from `/home/nurse/local.txt` and `/root/proof.txt`
