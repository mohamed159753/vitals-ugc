import os
import jwt
import psycopg2
import datetime
from flask import Flask, request, jsonify, g
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

DB_CONFIG = {
    "dbname": "vitals_db",
    "user": "postgres",
    "password": "vitals_pg_2024",
    "host": "127.0.0.1",
    "port": 5432
}

GUEST_SECRET = "guest_static_key_2024"

def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def get_jwt_master_secret():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_config WHERE key = 'jwt_master_secret'")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def verify_token(token, require_admin=False):
    try:
        payload = jwt.decode(token, GUEST_SECRET, algorithms=["HS256"])
        if require_admin:
            return None, "Admin token required"
        return payload, None
    except jwt.InvalidTokenError:
        pass
    try:
        secret = get_jwt_master_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("role") != "admin":
            return None, "Admin role required"
        return payload, None
    except jwt.InvalidTokenError:
        return None, "Invalid token"

SWAGGER_URL = "/api/docs"
API_URL = "/api/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route("/api/swagger.json")
def swagger_spec():
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Vitals Hospital Patient Monitoring API",
            "version": "2.1.4",
            "description": "REST API for patient vitals monitoring — Vitals Hospital IT"
        },
        "paths": {
            "/api/auth/guest": {
                "post": {
                    "summary": "Get guest access token",
                    "responses": {"200": {"description": "Guest JWT token"}}
                }
            },
            "/api/patients/search": {
                "get": {
                    "summary": "Search patients by name",
                    "parameters": [{"name": "name", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Patient list"}}
                }
            },
            "/api/vitals/{patient_id}": {
                "get": {
                    "summary": "Get vitals for a patient",
                    "responses": {"200": {"description": "Vitals data"}}
                }
            },
            "/api/admin/query": {
                "post": {
                    "summary": "Admin raw query endpoint",
                    "responses": {"200": {"description": "Query results"}}
                }
            }
        }
    })

@app.route("/api/auth/guest", methods=["POST"])
def guest_auth():
    token = jwt.encode(
        {
            "role": "guest",
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        },
        GUEST_SECRET,
        algorithm="HS256"
    )
    return jsonify({"token": token, "role": "guest", "expires_in": 86400})

@app.route("/api/vitals/<int:patient_id>", methods=["GET"])
def get_vitals(patient_id):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    payload, err = verify_token(token)
    if err:
        return jsonify({"error": "Unauthorized", "detail": err}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.heart_rate, v.blood_pressure, v.temperature, v.recorded_at, v.device_token
        FROM vitals v WHERE v.patient_id = %s ORDER BY v.recorded_at DESC LIMIT 1
    """, (patient_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Patient not found"}), 404

    return jsonify({
        "patient_id": patient_id,
        "heart_rate": row[0],
        "blood_pressure": row[1],
        "temperature": float(row[2]),
        "recorded_at": row[3].isoformat(),
        "device_token": row[4]
    })

@app.route("/api/patients/search", methods=["GET"])
def search_patients():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    payload, err = verify_token(token)
    if err:
        return jsonify({"error": "Unauthorized", "detail": err}), 401

    name = request.args.get("name", "")

    try:
        conn = get_db()
        cur = conn.cursor()
        query = "SELECT id, name, ward, condition FROM patients WHERE name ILIKE '%%%s%%'" % name
        cur.execute(query)
        rows = cur.fetchall()
        results = [
            {"id": r[0], "name": r[1], "ward": r[2], "condition": r[3]}
            for r in rows
        ]
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        err_str = str(e)
        if "UTF" in err_str or "byte sequence" in err_str or "encoding" in err_str:
            return jsonify({
                "error": "Database error",
                "detail": "invalid byte sequence for encoding UTF8: 0x00",
                "hint": "Patient name fields expect UTF-8 encoded input"
            }), 400
        return jsonify({"error": "Database error", "detail": err_str}), 400

@app.route("/api/admin/query", methods=["POST"])
def admin_query():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    payload, err = verify_token(token, require_admin=True)
    if err:
        return jsonify({"error": "Unauthorized", "detail": err}), 401

    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing query field"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(data["query"])
        conn.commit()
        try:
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return jsonify({"results": [dict(zip(cols, r)) for r in rows]})
        except Exception:
            return jsonify({"results": [], "status": "ok"})
    except Exception as e:
        return jsonify({"error": "Query error", "detail": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
