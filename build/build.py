#!/usr/bin/env python3
"""
Vitals — OffSec UGC Build Script
Automates full machine configuration on a fresh Ubuntu 22.04 install.
Run as root.
"""

import subprocess
import os
import sys

def run(cmd, shell=True, check=True):
    print(f"[*] {cmd}")
    subprocess.run(cmd, shell=shell, check=check)

def write_file(path, content, mode=None, owner=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    if mode:
        os.chmod(path, mode)
    if owner:
        run(f"chown {owner} {path}")
    print(f"[+] Written: {path}")

def main():
    if os.geteuid() != 0:
        print("[-] Must be run as root")
        sys.exit(1)

    print("\n=== Vitals Build Script ===\n")

    # 1. System packages
    print("[*] Installing system packages...")
    run("apt-get update -qq")
    run("apt-get install -y curl wget gnupg2 lsb-release ca-certificates "
        "python3 python3-pip net-tools ufw openssl jq open-vm-tools "
        "libllvm14 postgresql-common postgresql-client-common libpq5")

    # 2. Python packages
    print("[*] Installing Python packages...")
    run("pip3 install flask flask-swagger-ui pyjwt psycopg2-binary requests -q")

    # 3. PostgreSQL PGDG repo
    print("[*] Adding PostgreSQL repo...")
    run("curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc "
        "| gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg")
    run("echo 'deb [signed-by=/etc/apt/trusted.gpg.d/postgresql.gpg] "
        "https://apt.postgresql.org/pub/repos/apt jammy-pgdg main' "
        "> /etc/apt/sources.list.d/pgdg.list")
    run("apt-get update -qq")

    # 4. PostgreSQL 14.15 from archive
    print("[*] Installing PostgreSQL 14.15...")
    run("cd /tmp && wget -q http://repo.nova.cu/nova/pool/principal/p/postgresql-14/"
        "postgresql-client-14_14.15-0ubuntu0.22.04.1_amd64.deb")
    run("cd /tmp && wget -q http://repo.nova.cu/nova/pool/principal/p/postgresql-14/"
        "postgresql-14_14.15-0ubuntu0.22.04.1_amd64.deb")
    run("dpkg -i /tmp/postgresql-client-14_14.15-0ubuntu0.22.04.1_amd64.deb", check=False)
    run("dpkg -i /tmp/postgresql-14_14.15-0ubuntu0.22.04.1_amd64.deb", check=False)
    run("apt-get install -f -y")
    run("apt-mark hold postgresql-14 postgresql-client-14")

    # 5. Patch root checks in pg scripts
    print("[*] Patching PostgreSQL startup scripts...")
    run("sed -i '944,946s/^/#/' /usr/share/perl5/PgCommon.pm")
    run("sed -i '271s/^/#/' /usr/bin/pg_createcluster")

    # 6. Start PostgreSQL
    print("[*] Starting PostgreSQL...")
    run("chown -R postgres:postgres /var/lib/postgresql/")
    run("chown -R postgres:postgres /etc/postgresql/")
    run("chown -R postgres:postgres /var/log/postgresql/")
    run("chown -R postgres:postgres /run/postgresql/")
    run("chmod 775 /run/postgresql/")
    run("systemctl enable postgresql@14-main")
    run("systemctl start postgresql@14-main")

    # 7. Postgres password and database
    print("[*] Configuring database...")
    run("sudo -u postgres psql -c \"ALTER USER postgres WITH PASSWORD 'vitals_pg_2024';\"")
    run("sudo -u postgres psql -c \"CREATE DATABASE vitals_db;\"")

    # 8. Schema and data
    print("[*] Creating schema and inserting data...")
    sql = """
CREATE TABLE patients (
    id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
    dob DATE, ward VARCHAR(50), condition VARCHAR(100), device_token VARCHAR(200)
);
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY, key VARCHAR(100) NOT NULL, value TEXT NOT NULL, description TEXT
);
CREATE TABLE system_notes (
    id SERIAL PRIMARY KEY, note TEXT NOT NULL, created_by VARCHAR(50), date DATE
);
CREATE TABLE vitals (
    id SERIAL PRIMARY KEY, patient_id INTEGER REFERENCES patients(id),
    heart_rate INTEGER, blood_pressure VARCHAR(20), temperature NUMERIC(4,1),
    recorded_at TIMESTAMP DEFAULT NOW(), device_token VARCHAR(200)
);
INSERT INTO patients (name, dob, ward, condition, device_token) VALUES
('John Hartley','1958-03-12','Cardiology','Stable','eyJkZXZpY2UiOiJDQVJELTAwMSIsIndhcmQiOiJDYXJkaW9sb2d5In0='),
('Sarah Okonkwo','1972-07-24','Neurology','Monitoring','eyJkZXZpY2UiOiJORVVSLTAwMiIsIndhcmQiOiJOZXVyb2xvZ3kifQ=='),
('Mark Delvecchio','1945-11-03','ICU','Critical','eyJkZXZpY2UiOiJJQ1UtMDAzIiwid2FyZCI6IklDVSJ9'),
('Linda Parrish','1963-05-17','Oncology','Stable','eyJkZXZpY2UiOiJPTkNPLTAwNCIsIndhcmQiOiJPbmNvbG9neSJ9');
INSERT INTO system_config (key, value, description) VALUES
('api_version','2.1.4','Current API version'),
('max_session_duration','3600','Session timeout in seconds'),
('jwt_master_secret','Sup3rS3cr3tH0sp1talK3y!2024','Master key for JWT signing — do not expose'),
('db_backup_enabled','true','WAL archiving enabled for compliance'),
('api_rate_limit','100','Requests per minute per token');
INSERT INTO system_notes (note, created_by, date) VALUES
('Backup archiving enabled for compliance. See postgresql.conf','dbadmin','2024-11-03'),
('postgres account has temporary sudo access — not yet revoked before Q2 audit','dbadmin','2024-11-03'),
('TODO: restrict guest JWT access to read-only endpoints before audit','dbadmin','2025-01-14');
INSERT INTO vitals (patient_id, heart_rate, blood_pressure, temperature, device_token) VALUES
(1,72,'120/80',36.6,'eyJkZXZpY2UiOiJDQVJELTAwMSIsIndhcmQiOiJDYXJkaW9sb2d5In0='),
(2,88,'135/90',37.1,'eyJkZXZpY2UiOiJORVVSLTAwMiIsIndhcmQiOiJOZXVyb2xvZ3kifQ=='),
(3,104,'155/95',38.2,'eyJkZXZpY2UiOiJJQ1UtMDAzIiwid2FyZCI6IklDVSJ9'),
(4,68,'118/76',36.4,'eyJkZXZpY2UiOiJPTkNPLTAwNCIsIndhcmQiOiJPbmNvbG9neSJ9');
"""
    with open("/tmp/schema.sql", "w") as f:
        f.write(sql)
    run("sudo -u postgres psql -d vitals_db -f /tmp/schema.sql")

    # 9. Sudoers misconfiguration
    print("[*] Planting sudoers misconfiguration...")
    run("echo 'postgres ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers")

    # 10. systemd override narrative
    print("[*] Writing systemd override...")
    write_file(
        "/etc/systemd/system/postgresql@14-main.service.d/override.conf",
        "[Service]\n"
        "# Legacy override from embedded vitals hardware migration (2023)\n"
        "# Original system ran with elevated privileges for hardware access\n"
        "# Migration incomplete — sudo access temporarily granted to service account\n"
        "# TODO: remove postgres sudo access before compliance audit (Q2 2025)\n"
    )
    run("systemctl daemon-reload")

    # 11. Flask API
    print("[*] Installing Flask API...")
    os.makedirs("/opt/vitals-api", exist_ok=True)
    # app.py should be copied separately — see build guide
    write_file("/etc/systemd/system/vitals-api.service",
        "[Unit]\n"
        "Description=Vitals Hospital Patient Monitoring API\n"
        "After=network.target postgresql@14-main.service\n\n"
        "[Service]\n"
        "User=root\n"
        "WorkingDirectory=/opt/vitals-api\n"
        "ExecStart=/usr/bin/python3 /opt/vitals-api/app.py\n"
        "Restart=always\n"
        "RestartSec=3\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    run("systemctl daemon-reload")
    run("systemctl enable vitals-api")
    run("systemctl start vitals-api")

    # 12. Flags
    print("[*] Planting flags...")
    import hashlib, datetime
    local_hash = hashlib.md5(datetime.datetime.now().strftime("%Y%m%d%H%M%S").encode()).hexdigest()
    root_hash = hashlib.md5((datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "vitalsroot").encode()).hexdigest()
    write_file("/home/nurse/local.txt", local_hash + "\n", mode=0o644, owner="nurse:nurse")
    write_file("/root/proof.txt", root_hash + "\n", mode=0o700, owner="root:root")

    # 13. Firewall
    print("[*] Configuring firewall...")
    run("ufw allow 22/tcp")
    run("ufw allow 8080/tcp")
    run("ufw deny 5432/tcp")
    run("ufw --force enable")

    # 14. Cleanup
    print("[*] Cleaning up...")
    run("rm -f /tmp/*.deb /tmp/schema.sql")
    run("cat /dev/null > /var/log/syslog", check=False)

    print("\n[+] Build complete. Shut down and export as OVA.")
    print("[+] Remember to clear bash history before shutdown:")
    print("    cat /dev/null > /root/.bash_history && history -c && init 0")

if __name__ == "__main__":
    main()
