#!/usr/bin/env python3
"""
IRONLOG Gym Management System - REST API Server
Version: 1.0
Port: 5000 (Default)
"""

import json
import re
import sys
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import db
import threading
import time

BASE_DIR = Path(__file__).parent.resolve()

# Force UTF-8 encoding for console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class JSONRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP handler with REST route dispatching and CORS support."""
    
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _read_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode('utf-8')
        return json.loads(body)

    def _respond(self, data, status=200):
        self._set_headers(status)
        response_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.wfile.write(response_bytes)

    def _error(self, message, status=400):
        self._respond({"error": message, "status": "Error"}, status=status)

    def _get_current_user(self):
        """Extracts and validates the JWT token from the Authorization header."""
        import auth
        auth_header = self.headers.get("Authorization")
        if not auth_header:
            return None
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        token = parts[1]
        return auth.decode_access_token(token)

    def _require_roles(self, allowed_roles):
        """Verifies current user is logged in and belongs to one of allowed_roles."""
        user = self._get_current_user()
        if not user:
            raise PermissionError("Authentication required.")
        if user["role"] not in allowed_roles:
            raise PermissionError("Access forbidden: insufficient permissions.")
        return user

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self._set_headers(204)

    def do_GET(self):
        """Route handler for GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')
        query_params = parse_qs(parsed_url.query)
        
        # Helper to get single query parameter
        def get_param(key, default=None):
            return query_params.get(key, [default])[0]

        try:
            # Serve Static index.html website at root
            if path in ("", "/"):
                index_path = BASE_DIR / "index.html"
                if index_path.exists():
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    with open(index_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return

            # Serve Static CSS and JS Assets
            if path.endswith(".css") or path.endswith(".js"):
                file_name = os.path.basename(path)
                file_path = BASE_DIR / file_name
                if file_path.exists() and file_path.is_file():
                    self.send_response(200)
                    content_type = 'text/css' if path.endswith('.css') else 'application/javascript; charset=utf-8'
                    self.send_header('Content-Type', content_type)
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return

            # Health check
            if path == "/api/health":
                return self._respond({"status": "Healthy", "service": "IRONLOG REST API", "version": "1.0"})

            # Dashboard Operational Stats
            if path == "/api/dashboard":
                self._require_roles(['Admin'])
                return self._respond({"status": "Success", "data": db.get_dashboard_stats()})

            # Members List & Search
            if path == "/api/members":
                self._require_roles(['Admin', 'Trainer'])
                q = get_param("q")
                status = get_param("status")
                plan_id = get_param("plan_id")
                trainer_id = get_param("trainer_id")
                members = db.get_members(query=q, status=status, plan_id=plan_id, trainer_id=trainer_id)
                return self._respond({"status": "Success", "count": len(members), "data": members})

            # Get Member Profile by ID
            match_member = re.match(r"^/api/members/(\d+)$", path)
            if match_member:
                member_id = int(match_member.group(1))
                user = self._require_roles(['Admin', 'Trainer', 'Member'])
                if user["role"] == "Member" and user["reference_id"] != member_id:
                    raise PermissionError("Access forbidden: cannot view other member profiles.")
                member = db.get_member_by_id(member_id)
                if not member:
                    return self._error(f"Member ID {member_id} not found", status=404)
                return self._respond({"status": "Success", "data": member})

            # Attendance: Live Occupancy
            if path == "/api/attendance/current":
                self._require_roles(['Admin', 'Trainer'])
                occupancy = db.get_current_occupancy()
                return self._respond({"status": "Success", "inside_count": len(occupancy), "data": occupancy})

            # Attendance: Today's Attendance Log
            if path == "/api/attendance/today":
                self._require_roles(['Admin', 'Trainer'])
                attendance = db.get_today_attendance()
                return self._respond({"status": "Success", "count": len(attendance), "data": attendance})

            # Plans List
            if path == "/api/plans":
                self._require_roles(['Admin', 'Trainer', 'Member'])
                plans = db.get_plans()
                return self._respond({"status": "Success", "count": len(plans), "data": plans})

            # Trainers List
            if path == "/api/trainers":
                self._require_roles(['Admin', 'Trainer', 'Member'])
                trainers = db.get_trainers()
                return self._respond({"status": "Success", "count": len(trainers), "data": trainers})

            # Reports: Daily
            if path == "/api/reports/daily":
                self._require_roles(['Admin'])
                report = db.get_daily_report()
                return self._respond({"status": "Success", "data": report})

            # Reports: Monthly
            if path == "/api/reports/monthly":
                self._require_roles(['Admin'])
                report = db.get_monthly_report()
                return self._respond({"status": "Success", "data": report})

            # Reports: Peak Hours
            if path == "/api/reports/peak-hours":
                self._require_roles(['Admin'])
                report = db.get_peak_hours_report()
                return self._respond({"status": "Success", "data": report})

            # Reports: Attendance Per Member
            if path == "/api/reports/attendance-per-member":
                self._require_roles(['Admin'])
                report = db.get_attendance_per_member()
                return self._respond({"status": "Success", "data": report})

            # Reports: Weekly
            if path == "/api/reports/weekly":
                self._require_roles(['Admin'])
                report = db.get_weekly_attendance()
                return self._respond({"status": "Success", "data": report})

            # Reports: Most Active Members
            if path == "/api/reports/most-active":
                self._require_roles(['Admin'])
                top_n = get_param("top_n", 10)
                report = db.get_most_active_members(top_n=int(top_n))
                return self._respond({"status": "Success", "data": report})

            # Reports: Low Attendance
            if path == "/api/reports/low-attendance":
                self._require_roles(['Admin'])
                threshold = get_param("threshold", 4)
                days = get_param("days", 30)
                report = db.get_low_attendance(threshold=int(threshold), days=int(days))
                return self._respond({"status": "Success", "data": report})

            # Reports: Inactive Members
            if path == "/api/reports/inactive":
                self._require_roles(['Admin'])
                days = get_param("days", 14)
                report = db.get_inactive_members(days=int(days))
                return self._respond({"status": "Success", "data": report})

            # Reports: Average Visit Duration
            if path == "/api/reports/average-duration":
                self._require_roles(['Admin'])
                report = db.get_average_visit_duration()
                return self._respond({"status": "Success", "data": report})

            # Reports: Attendance By Plan
            if path == "/api/reports/attendance-by-plan":
                self._require_roles(['Admin'])
                report = db.get_attendance_by_plan()
                return self._respond({"status": "Success", "data": report})

            # Reports: Attendance By Trainer
            if path == "/api/reports/attendance-by-trainer":
                self._require_roles(['Admin'])
                report = db.get_attendance_by_trainer()
                return self._respond({"status": "Success", "data": report})

            # Expiry Alerts
            if path == "/api/alerts":
                self._require_roles(['Admin'])
                alerts = db.get_alerts()
                return self._respond({"status": "Success", "count": len(alerts), "data": alerts})

            return self._error(f"Route '{path}' not found", status=404)

        except PermissionError as pe:
            status = 401 if "required" in str(pe) else 403
            return self._error(str(pe), status=status)
        except Exception as e:
            return self._error(str(e), status=500)

    def do_POST(self):
        """Route handler for POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')

        try:
            body = self._read_json_body()

            # User Login (Public)
            if path == "/api/auth/login":
                email = body.get("email")
                password = body.get("password")
                if not email or not password:
                    return self._error("Email and password are required.")
                
                user = db.authenticate_user(email, password)
                if not user:
                    return self._error("Invalid email or password.", status=401)
                
                import auth
                token = auth.create_access_token(user)
                return self._respond({
                    "status": "Success",
                    "message": "Login successful",
                    "token": token,
                    "role": user["role"],
                    "reference_id": user["reference_id"]
                })

            # Member Registration via Stored Procedure (Admin Only)
            if path == "/api/members/register":
                self._require_roles(['Admin'])
                required = ["full_name", "phone", "plan_id"]
                for f in required:
                    if f not in body or not body[f]:
                        return self._error(f"Missing required field: '{f}'")
                        
                res = db.register_member_sp(
                    full_name=body.get("full_name"),
                    phone=body.get("phone"),
                    email=body.get("email"),
                    date_of_birth=body.get("date_of_birth"),
                    gender=body.get("gender"),
                    address=body.get("address"),
                    plan_id=int(body.get("plan_id")),
                    trainer_id=int(body["trainer_id"]) if body.get("trainer_id") else None
                )
                return self._respond({"status": "Success", "message": "Member registered successfully", "data": res}, status=201)

            # Subscription Renewal via Stored Procedure (Admin Only)
            if path == "/api/subscriptions/renew":
                self._require_roles(['Admin'])
                member_id = body.get("member_id")
                if not member_id:
                    return self._error("Field 'member_id' is required.")
                res = db.renew_subscription_sp(
                    member_id=int(member_id),
                    plan_id=int(body["plan_id"]) if body.get("plan_id") else None,
                    trainer_id=int(body["trainer_id"]) if body.get("trainer_id") else None
                )
                return self._respond({"status": "Success", "message": "Subscription renewed successfully", "data": res}, status=200)

            # Attendance Check-In (Authenticated Users; Self only if Member)
            if path == "/api/attendance/check-in":
                user = self._require_roles(['Admin', 'Trainer', 'Member'])
                member_id = body.get("member_id")
                if not member_id:
                    return self._error("Field 'member_id' is required.")
                if user["role"] == "Member" and int(member_id) != user["reference_id"]:
                    raise PermissionError("Access forbidden: members cannot check-in other accounts.")
                res = db.record_check_in(int(member_id))
                return self._respond({"status": "Success", "message": "Check-in recorded", "data": res}, status=201)

            # Attendance Check-Out (Authenticated Users; Self only if Member)
            if path == "/api/attendance/check-out":
                user = self._require_roles(['Admin', 'Trainer', 'Member'])
                attendance_id = body.get("attendance_id")
                member_id = body.get("member_id")
                if user["role"] == "Member":
                    if member_id and int(member_id) != user["reference_id"]:
                        raise PermissionError("Access forbidden: members cannot check-out other accounts.")
                res = db.record_check_out(
                    attendance_id=int(attendance_id) if attendance_id else None,
                    member_id=int(member_id) if member_id else None
                )
                return self._respond({"status": "Success", "message": "Check-out recorded successfully"})

            # Create Plan (Admin Only)
            if path == "/api/plans":
                self._require_roles(['Admin'])
                plan_id = db.create_plan(
                    name=body["name"],
                    duration_months=int(body["duration_months"]),
                    price=float(body["price"]),
                    description=body.get("description", "")
                )
                return self._respond({"status": "Success", "plan_id": plan_id}, status=201)

            # Create Trainer (Admin Only)
            if path == "/api/trainers":
                self._require_roles(['Admin'])
                trainer_id = db.create_trainer(
                    full_name=body["full_name"],
                    phone=body.get("phone"),
                    email=body.get("email"),
                    specialization=body.get("specialization")
                )
                return self._respond({"status": "Success", "trainer_id": trainer_id}, status=201)

            # Trigger Scheduler Run manually (Admin Only)
            if path == "/api/scheduler/run":
                self._require_roles(['Admin'])
                count = db.process_subscription_expiries()
                return self._respond({
                    "status": "Success",
                    "message": f"Scheduler run complete. Processed {count} membership transitions."
                })

            return self._error(f"Route '{path}' not found", status=404)

        except PermissionError as pe:
            status = 401 if "required" in str(pe) else 403
            return self._error(str(pe), status=status)
        except ValueError as ve:
            return self._error(str(ve), status=400)
        except Exception as e:
            return self._error(str(e), status=500)

    def do_PUT(self):
        """Route handler for PUT requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')

        try:
            body = self._read_json_body()

            # Update Member Profile (Admin, Trainer, or Self Member)
            match_member = re.match(r"^/api/members/(\d+)$", path)
            if match_member:
                member_id = int(match_member.group(1))
                user = self._require_roles(['Admin', 'Trainer', 'Member'])
                if user["role"] == "Member" and user["reference_id"] != member_id:
                    raise PermissionError("Access forbidden: cannot edit other members' details.")
                success = db.update_member(
                    member_id=member_id,
                    full_name=body.get("full_name"),
                    phone=body.get("phone"),
                    email=body.get("email"),
                    address=body.get("address"),
                    gender=body.get("gender")
                )
                if not success:
                    return self._error(f"Member ID {member_id} not found", status=404)
                return self._respond({"status": "Success", "message": "Member details updated"})

            # Update Plan (Admin Only)
            match_plan = re.match(r"^/api/plans/(\d+)$", path)
            if match_plan:
                self._require_roles(['Admin'])
                plan_id = int(match_plan.group(1))
                required = ["name", "duration_months", "price", "status"]
                for r in required:
                    if r not in body:
                        return self._error(f"Field '{r}' is required for plan update.")
                db.update_plan(
                    plan_id=plan_id,
                    name=body.get("name"),
                    duration_months=int(body.get("duration_months")),
                    price=float(body.get("price")),
                    description=body.get("description", ""),
                    status=body.get("status")
                )
                return self._respond({"status": "Success", "message": "Plan details updated"})

            # Update Trainer (Admin Only)
            match_trainer = re.match(r"^/api/trainers/(\d+)$", path)
            if match_trainer:
                self._require_roles(['Admin'])
                trainer_id = int(match_trainer.group(1))
                required = ["full_name", "status"]
                for r in required:
                    if r not in body:
                        return self._error(f"Field '{r}' is required for trainer update.")
                success = db.update_trainer(
                    trainer_id=trainer_id,
                    full_name=body.get("full_name"),
                    phone=body.get("phone"),
                    email=body.get("email"),
                    specialization=body.get("specialization"),
                    status=body.get("status")
                )
                if not success:
                    return self._error(f"Trainer ID {trainer_id} not found", status=404)
                return self._respond({"status": "Success", "message": "Trainer details updated"})

            return self._error(f"Route '{path}' not found", status=404)
        except PermissionError as pe:
            status = 401 if "required" in str(pe) else 403
            return self._error(str(pe), status=status)
        except Exception as e:
            return self._error(str(e), status=500)

    def do_PATCH(self):
        """Route handler for PATCH requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')

        try:
            body = self._read_json_body()

            # Update Member Status (Admin Only)
            match_status = re.match(r"^/api/members/(\d+)/status$", path)
            if match_status:
                self._require_roles(['Admin'])
                member_id = int(match_status.group(1))
                status = body.get("status")
                if not status:
                    return self._error("Field 'status' is required.")
                success = db.set_member_status(member_id, status)
                if not success:
                    return self._error(f"Member ID {member_id} not found", status=404)
                return self._respond({"status": "Success", "message": f"Member status updated to '{status}'"})

            return self._error(f"Route '{path}' not found", status=404)
        except PermissionError as pe:
            status = 401 if "required" in str(pe) else 403
            return self._error(str(pe), status=status)
        except Exception as e:
            return self._error(str(e), status=500)

def start_expiry_scheduler(interval_seconds=3600):
    """Launches a daemon thread to periodically process subscription status changes and log alerts."""
    def run_scheduler():
        print("[SCHEDULER] Background expiry check thread started.", flush=True)
        # Run immediately on start, then loop
        try:
            count = db.process_subscription_expiries()
            if count > 0:
                print(f"[SCHEDULER] Startup check run complete. Processed {count} transitions.", flush=True)
        except Exception as e:
            print(f"[SCHEDULER ERROR] Startup check failed: {e}", flush=True)
            
        while True:
            time.sleep(interval_seconds)
            try:
                count = db.process_subscription_expiries()
                if count > 0:
                    print(f"[SCHEDULER] Periodic check run complete. Processed {count} transitions.", flush=True)
            except Exception as e:
                print(f"[SCHEDULER ERROR] Periodic check failed: {e}", flush=True)

    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()

def run_server(port=5000):
    """Starts the REST API server."""
    # Start background scheduler to check every hour
    start_expiry_scheduler(interval_seconds=3600)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, JSONRequestHandler)
    print(f"==================================================", flush=True)
    print(f"IRONLOG REST API Server active on http://localhost:{port}", flush=True)
    print(f"==================================================", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", flush=True)
        httpd.server_close()

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
