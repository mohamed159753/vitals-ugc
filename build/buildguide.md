# Vitals — Build Guide

## Overview
**Machine Name:** Vitals  
**OS:** Ubuntu 22.04 LTS (Jammy)  
**PostgreSQL:** 14.15  
**Application:** Flask REST API (Python 3.10)  
**Theme:** Hospital patient monitoring system

---

## Requirements
- VMware Workstation Player (free) or Workstation Pro
- Ubuntu 22.04 Server ISO
- Internet access during build
- 1 CPU, 1024MB RAM, 20GB disk

---

## Step 1 — Base System

Install Ubuntu 22.04 Server with the following settings:
- Hostname: `vitals`
- Username: `nurse`
- Password: `Vitals2024!`
- OpenSSH: enabled

After first login, switch to root and update:

```bash
sudo su
apt-get update && apt-get upgrade -y
apt-get install -y curl wget gnupg2 lsb-release ca-certificates \
    python3 python3-pip net-tools ufw openssl jq open-vm-tools
```

---

## Step 2 — PostgreSQL 14.15 Installation

Add the PGDG repository:

```bash
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg

echo "deb [signed-by=/etc/apt/trusted.gpg.d/postgresql.gpg] \
    https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list

apt-get update
```

Download and install PG 14.15 from archive:

```bash
cd /tmp
wget http://repo.nova.cu/nova/pool/principal/p/postgresql-14/postgresql-client-14_14.15-0ubuntu0.22.04.1_amd64.deb
wget http://repo.nova.cu/nova/pool/principal/p/postgresql-14/postgresql-14_14.15-0ubuntu0.22.04.1_amd64.deb

apt-get install -y libpq5 postgresql-client-common postgresql-common libllvm14
dpkg -i postgresql-client-14_14.15-0ubuntu0.22.04.1_amd64.deb
dpkg -i postgresql-14_14.15-0ubuntu0.22.04.1_amd64.deb
apt-get install -f -y

apt-mark hold postgresql-14 postgresql-client-14
```

Verify:
```bash
psql --version
# psql (PostgreSQL) 14.15
```

---

## Step 3 — PostgreSQL Configuration

Set postgres password and create database:

```bash
systemctl start postgresql@14-main

sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'vitals_pg_2024';"
sudo -u postgres psql -c "CREATE DATABASE vitals_db;"
```

Add sudoers misconfiguration (the intended privesc):

```bash
echo "postgres ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
```

Plant the systemd override narrative file:

```bash
mkdir -p /etc/systemd/system/postgresql@14-main.service.d/

cat > /etc/systemd/system/postgresql@14-main.service.d/override.conf << 'EOF'
[Service]
# Legacy override from embedded vitals hardware migration (2023)
# Original system ran with elevated privileges for hardware access
# Migration incomplete — sudo access temporarily granted to service account
# TODO: remove postgres sudo access before compliance audit (Q2 2025)
EOF

systemctl daemon-reload
```

---

## Step 4 — Database Schema

```bash
sudo -u postgres psql -d vitals_db << 'EOF'

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dob DATE,
    ward VARCHAR(50),
    condition VARCHAR(100),
    device_token VARCHAR(200)
);

CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    description TEXT
);

CREATE TABLE system_notes (
    id SERIAL PRIMARY KEY,
    note TEXT NOT NULL,
    created_by VARCHAR(50),
    date DATE
);

CREATE TABLE vitals (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    heart_rate INTEGER,
    blood_pressure VARCHAR(20),
    temperature NUMERIC(4,1),
    recorded_at TIMESTAMP DEFAULT NOW(),
    device_token VARCHAR(200)
);

INSERT INTO patients (name, dob, ward, condition, device_token) VALUES
('John Hartley', '1958-03-12', 'Cardiology', 'Stable', 'eyJkZXZpY2UiOiJDQVJELTAwMSIsIndhcmQiOiJDYXJkaW9sb2d5In0='),
('Sarah Okonkwo', '1972-07-24', 'Neurology', 'Monitoring', 'eyJkZXZpY2UiOiJORVVSLTAwMiIsIndhcmQiOiJOZXVyb2xvZ3kifQ=='),
('Mark Delvecchio', '1945-11-03', 'ICU', 'Critical', 'eyJkZXZpY2UiOiJJQ1UtMDAzIiwid2FyZCI6IklDVSJ9'),
('Linda Parrish', '1963-05-17', 'Oncology', 'Stable', 'eyJkZXZpY2UiOiJPTkNPLTAwNCIsIndhcmQiOiJPbmNvbG9neSJ9');

INSERT INTO system_config (key, value, description) VALUES
('api_version', '2.1.4', 'Current API version'),
('max_session_duration', '3600', 'Session timeout in seconds'),
('jwt_master_secret', 'Sup3rS3cr3tH0sp1talK3y!2024', 'Master key for JWT signing — do not expose'),
('db_backup_enabled', 'true', 'WAL archiving enabled for compliance'),
('api_rate_limit', '100', 'Requests per minute per token');

INSERT INTO system_notes (note, created_by, date) VALUES
('Backup archiving enabled for compliance. See postgresql.conf', 'dbadmin', '2024-11-03'),
('postgres account has temporary sudo access — not yet revoked before Q2 audit', 'dbadmin', '2024-11-03'),
('TODO: restrict guest JWT access to read-only endpoints before audit', 'dbadmin', '2025-01-14');

INSERT INTO vitals (patient_id, heart_rate, blood_pressure, temperature, device_token) VALUES
(1, 72, '120/80', 36.6, 'eyJkZXZpY2UiOiJDQVJELTAwMSIsIndhcmQiOiJDYXJkaW9sb2d5In0='),
(2, 88, '135/90', 37.1, 'eyJkZXZpY2UiOiJORVVSLTAwMiIsIndhcmQiOiJOZXVyb2xvZ3kifQ=='),
(3, 104, '155/95', 38.2, 'eyJkZXZpY2UiOiJJQ1UtMDAzIiwid2FyZCI6IklDVSJ9'),
(4, 68, '118/76', 36.4, 'eyJkZXZpY2UiOiJPTkNPLTAwNCIsIndhcmQiOiJPbmNvbG9neSJ9');

EOF
```

---

## Step 5 — Flask API

Install dependencies:

```bash
pip3 install flask flask-swagger-ui pyjwt psycopg2-binary requests
```

Create the application directory and copy `app.py` to `/opt/vitals-api/app.py`.

Create the systemd service:

```bash
cat > /etc/systemd/system/vitals-api.service << 'EOF'
[Unit]
Description=Vitals Hospital Patient Monitoring API
After=network.target postgresql@14-main.service

[Service]
User=root
WorkingDirectory=/opt/vitals-api
ExecStart=/usr/bin/python3 /opt/vitals-api/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vitals-api
systemctl start vitals-api
```

---

## Step 6 — Flags

```bash
echo -n "$(date +%Y%m%d%H%M%S)" | md5sum | awk '{print $1}' > /home/nurse/local.txt
chown nurse:nurse /home/nurse/local.txt
chmod 0644 /home/nurse/local.txt

echo -n "$(date +%Y%m%d%H%M%S)vitalsroot" | md5sum | awk '{print $1}' > /root/proof.txt
chown root:root /root/proof.txt
chmod 0700 /root/proof.txt
```

---

## Step 7 — Firewall

```bash
ufw allow 22/tcp
ufw allow 8080/tcp
ufw deny 5432/tcp
ufw --force enable
```

---

## Step 8 — Cleanup and Export

```bash
sudo -u postgres truncate -s 0 /var/log/postgresql/postgresql-14-main.log
cat /dev/null > /var/log/syslog
rm -f /tmp/*.deb /tmp/*.py
cat /dev/null > /home/nurse/.bash_history
cat /dev/null > /root/.bash_history
history -c && init 0
```

Export VM as OVA from VMware after shutdown.
