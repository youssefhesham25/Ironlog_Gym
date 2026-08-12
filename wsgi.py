#!/usr/bin/env python3
"""
IRONLOG Gym Management System - WSGI Application Entry Point
Supports deployment on standard WSGI environments like PythonAnywhere.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs

# Add current directory to path so we can import local modules
sys.path.append(str(Path(__file__).resolve().parent))
import db
import auth

def application(environ, start_response):
    path = environ.get('PATH_INFO', '').rstrip('/')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # 1. Handle CORS Preflight (OPTIONS)
    if method == 'OPTIONS':
        start_response('204 No Content', [
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        ])
        return [b'']

    # JSON helper response
    def respond_json(data, status='200 OK'):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        start_response(status, [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
            ('Content-Length', str(len(body)))
        ])
        return [body]

    # File helper response (MIME mapping)
    def respond_file(file_name, content_type, status='200 OK'):
        file_path = Path(__file__).parent / file_name
        try:
            with open(file_path, 'rb') as f:
                body = f.read()
            start_response(status, [
                ('Content-Type', content_type),
                ('Access-Control-Allow-Origin', '*'),
                ('Content-Length', str(len(body)))
            ])
            return [body]
        except Exception:
            return respond_json({"error": "File not found", "status": "Error"}, '404 Not Found')

    # Token auth helpers
    def get_current_user():
        auth_header = environ.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return auth.decode_access_token(parts[1])

    def require_roles(allowed_roles):
        user = get_current_user()
        if not user:
            raise PermissionError("Authentication required.")
        if user["role"] not in allowed_roles:
            raise PermissionError("Access forbidden: insufficient permissions.")
        return user

    try:
        # Route static web pages
        if path in ("", "/"):
            return respond_file('index.html', 'text/html; charset=utf-8')
        if path == "/index.css":
            return respond_file('index.css', 'text/css')
        if path == "/app.js":
            return respond_file('app.js', 'application/javascript; charset=utf-8')
        if path == "/api.js":
            return respond_file('api.js', 'application/javascript; charset=utf-8')
        if path == "/views.js":
            return respond_file('views.js', 'application/javascript; charset=utf-8')

        # Read JSON body for POST/PUT/PATCH
        body = {}
        content_length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        if content_length > 0:
            body_bytes = environ['wsgi.input'].read(content_length)
            body = json.loads(body_bytes.decode('utf-8'))

        # Parse query string parameters
        query_string = environ.get('QUERY_STRING', '')
        query_params = parse_qs(query_string)
        def get_param(key, default=None):
            return query_params.get(key, [default])[0]

        # 2. ROUTING LOGIC (API ENDPOINTS)
        if method == 'GET':
            if path == "/api/health":
                return respond_json({"status": "Healthy", "service": "IRONLOG REST API", "version": "1.0"})
            
            if path == "/api/dashboard":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_dashboard_stats()})
                
            if path == "/api/members":
                require_roles(['Admin', 'Trainer'])
                members = db.get_members(
                    query=get_param("q"), status=get_param("status"),
                    plan_id=get_param("plan_id"), trainer_id=get_param("trainer_id")
                )
                return respond_json({"status": "Success", "count": len(members), "data": members})
                
            match_member = re.match(r"^/api/members/(\d+)$", path)
            if match_member:
                member_id = int(match_member.group(1))
                user = require_roles(['Admin', 'Trainer', 'Member'])
                if user["role"] == "Member" and user["reference_id"] != member_id:
                    raise PermissionError("Access forbidden: cannot view other member profiles.")
                member = db.get_member_by_id(member_id)
                if not member:
                    return respond_json({"error": f"Member ID {member_id} not found", "status": "Error"}, '404 Not Found')
                return respond_json({"status": "Success", "data": member})
                
            if path == "/api/attendance/current":
                require_roles(['Admin', 'Trainer'])
                return respond_json({"status": "Success", "inside_count": len(db.get_current_occupancy()), "data": db.get_current_occupancy()})
                
            if path == "/api/attendance/today":
                require_roles(['Admin', 'Trainer'])
                return respond_json({"status": "Success", "data": db.get_today_attendance()})
                
            if path == "/api/plans":
                require_roles(['Admin', 'Trainer', 'Member'])
                return respond_json({"status": "Success", "data": db.get_plans()})
                
            if path == "/api/trainers":
                require_roles(['Admin', 'Trainer', 'Member'])
                return respond_json({"status": "Success", "data": db.get_trainers()})
                
            # Reports
            if path == "/api/reports/daily":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_daily_report()})
            if path == "/api/reports/monthly":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_monthly_report()})
            if path == "/api/reports/peak-hours":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_peak_hours_report()})
            if path == "/api/reports/attendance-per-member":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_attendance_per_member()})
            if path == "/api/reports/weekly":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_weekly_attendance()})
            if path == "/api/reports/most-active":
                require_roles(['Admin'])
                top_n = get_param("top_n", 10)
                return respond_json({"status": "Success", "data": db.get_most_active_members(top_n=int(top_n))})
            if path == "/api/reports/low-attendance":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_low_attendance(threshold=int(get_param("threshold", 4)), days=int(get_param("days", 30)))})
            if path == "/api/reports/inactive":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_inactive_members(days=int(get_param("days", 14)))})
            if path == "/api/reports/average-duration":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_average_visit_duration()})
            if path == "/api/reports/attendance-by-plan":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_attendance_by_plan()})
            if path == "/api/reports/attendance-by-trainer":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_attendance_by_trainer()})
                
            if path == "/api/alerts":
                require_roles(['Admin'])
                return respond_json({"status": "Success", "data": db.get_alerts()})

        elif method == 'POST':
            if path == "/api/auth/login":
                email = body.get("email")
                password = body.get("password")
                if not email or not password:
                    raise ValueError("Email and password are required.")
                user = db.authenticate_user(email, password)
                if not user:
                    return respond_json({"error": "Invalid email or password.", "status": "Error"}, '401 Unauthorized')
                token = auth.create_access_token(user)
                return respond_json({
                    "status": "Success", "message": "Login successful", "token": token,
                    "role": user["role"], "reference_id": user["reference_id"]
                })
                
            if path == "/api/members/register":
                require_roles(['Admin'])
                res = db.register_member_sp(
                    full_name=body["full_name"], phone=body["phone"], email=body.get("email"),
                    date_of_birth=body.get("date_of_birth"), gender=body.get("gender"),
                    address=body.get("address"), plan_id=int(body["plan_id"]),
                    trainer_id=int(body["trainer_id"]) if body.get("trainer_id") else None
                )
                return respond_json({"status": "Success", "message": "Member registered successfully", "data": res}, '201 Created')
                
            if path == "/api/subscriptions/renew":
                require_roles(['Admin'])
                res = db.renew_subscription_sp(
                    member_id=int(body["member_id"]),
                    plan_id=int(body["plan_id"]) if body.get("plan_id") else None,
                    trainer_id=int(body["trainer_id"]) if body.get("trainer_id") else None
                )
                return respond_json({"status": "Success", "message": "Subscription renewed successfully", "data": res})
                
            if path == "/api/attendance/check-in":
                user = require_roles(['Admin', 'Trainer', 'Member'])
                member_id = int(body["member_id"])
                if user["role"] == "Member" and member_id != user["reference_id"]:
                    raise PermissionError("Access forbidden: members cannot check-in other accounts.")
                res = db.record_check_in(member_id)
                return respond_json({"status": "Success", "message": "Check-in recorded", "data": res}, '201 Created')
                
            if path == "/api/attendance/check-out":
                user = require_roles(['Admin', 'Trainer', 'Member'])
                member_id = body.get("member_id")
                if user["role"] == "Member" and member_id and int(member_id) != user["reference_id"]:
                    raise PermissionError("Access forbidden: members cannot check-out other accounts.")
                res = db.record_check_out(
                    attendance_id=int(body["attendance_id"]) if body.get("attendance_id") else None,
                    member_id=int(member_id) if member_id else None
                )
                return respond_json({"status": "Success", "message": "Check-out recorded successfully"})
                
            if path == "/api/plans":
                require_roles(['Admin'])
                plan_id = db.create_plan(
                    name=body["name"], duration_months=int(body["duration_months"]),
                    price=float(body["price"]), description=body.get("description", "")
                )
                return respond_json({"status": "Success", "plan_id": plan_id}, '201 Created')
                
            if path == "/api/trainers":
                require_roles(['Admin'])
                trainer_id = db.create_trainer(
                    full_name=body["full_name"], phone=body.get("phone"),
                    email=body.get("email"), specialization=body.get("specialization")
                )
                return respond_json({"status": "Success", "trainer_id": trainer_id}, '201 Created')
                
            if path == "/api/scheduler/run":
                require_roles(['Admin'])
                count = db.process_subscription_expiries()
                return respond_json({"status": "Success", "message": f"Scheduler run complete. Processed {count} membership transitions."})

        elif method == 'PUT':
            match_member = re.match(r"^/api/members/(\d+)$", path)
            if match_member:
                member_id = int(match_member.group(1))
                user = require_roles(['Admin', 'Trainer', 'Member'])
                if user["role"] == "Member" and user["reference_id"] != member_id:
                    raise PermissionError("Access forbidden: cannot edit other members' details.")
                db.update_member(
                    member_id=member_id, full_name=body.get("full_name"), phone=body.get("phone"),
                    email=body.get("email"), address=body.get("address"), gender=body.get("gender")
                )
                return respond_json({"status": "Success", "message": "Member details updated"})
                
            match_plan = re.match(r"^/api/plans/(\d+)$", path)
            if match_plan:
                require_roles(['Admin'])
                plan_id = int(match_plan.group(1))
                db.update_plan(
                    plan_id=plan_id, name=body.get("name"), duration_months=int(body.get("duration_months")),
                    price=float(body.get("price")), description=body.get("description", ""), status=body.get("status")
                )
                return respond_json({"status": "Success", "message": "Plan details updated"})
                
            match_trainer = re.match(r"^/api/trainers/(\d+)$", path)
            if match_trainer:
                require_roles(['Admin'])
                trainer_id = int(match_trainer.group(1))
                db.update_trainer(
                    trainer_id=trainer_id, full_name=body.get("full_name"), phone=body.get("phone"),
                    email=body.get("email"), specialization=body.get("specialization"), status=body.get("status")
                )
                return respond_json({"status": "Success", "message": "Trainer details updated"})

        elif method == 'PATCH':
            match_status = re.match(r"^/api/members/(\d+)/status$", path)
            if match_status:
                require_roles(['Admin'])
                member_id = int(match_status.group(1))
                db.set_member_status(member_id, body["status"])
                return respond_json({"status": "Success", "message": f"Member status updated to '{body['status']}'"})

        return respond_json({"error": f"Route '{path}' not found", "status": "Error"}, '404 Not Found')

    except PermissionError as pe:
        status = '401 Unauthorized' if "required" in str(pe) else '403 Forbidden'
        return respond_json({"error": str(pe), "status": "Error"}, status)
    except ValueError as ve:
        return respond_json({"error": str(ve), "status": "Error"}, '400 Bad Request')
    except Exception as e:
        return respond_json({"error": str(e), "status": "Error"}, '500 Internal Server Error')
