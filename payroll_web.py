import json
import csv
import os
import io
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import openpyxl

# ===== TAX SETTINGS =====
FEDERAL_TAX = 0.1077
STATE_TAX = 0.0444
SOCIAL_SECURITY = 0.062
MEDICARE = 0.0145

YTD_FILE = "ytd_data.json"
EMPLOYEES_FILE = "employees.json"


# ===== FILE STORAGE =====
def load_ytd():
    if os.path.exists(YTD_FILE):
        with open(YTD_FILE) as f:
            return json.load(f)
    return {}

def save_ytd(ytd):
    with open(YTD_FILE, "w") as f:
        json.dump(ytd, f, indent=2)

def load_employees():
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE) as f:
            return json.load(f)
    return []

def save_employees(emps):
    with open(EMPLOYEES_FILE, "w") as f:
        json.dump(emps, f, indent=2)


# ===== PAYROLL CALC =====
def calculate(data):
    r = float(data.get("regular_hours", 0))
    o = float(data.get("overtime_hours", 0))
    h = float(data.get("holiday_hours", 0))
    rate = float(data.get("hourly_rate", 0))

    regular_pay = r * rate
    overtime_pay = o * (rate * 1.5)
    holiday_pay = h * rate

    gross = regular_pay + overtime_pay + holiday_pay

    federal = gross * FEDERAL_TAX
    state = gross * STATE_TAX
    ss = gross * SOCIAL_SECURITY
    medicare = gross * MEDICARE

    net = gross - federal - state - ss - medicare

    return {
        "name": data.get("name"),
        "gross": round(gross, 2),
        "net": round(net, 2),
        "regular_hours": r,
        "overtime_hours": o
    }


# ===== 🔥 FIXED TIME PARSER =====
def parse_timecard_xlsx(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    records = []

    for row in ws.iter_rows(values_only=True):
        cells = [str(c).strip() if c else "" for c in row]

        if not any(cells):
            continue

        employee = cells[0]

        action = next((c for c in cells if c.lower() in ["in", "out"]), None)
        date = next((c for c in cells if "/" in c), None)
        time = next((c for c in cells if ":" in c), None)

        if employee and action and date and time:
            try:
                dt = datetime.strptime(f"{date} {time}", "%m/%d/%Y %I:%M:%S %p")
                records.append({
                    "emp": employee,
                    "action": action.lower(),
                    "time": dt
                })
            except:
                continue

    records.sort(key=lambda x: (x["emp"], x["time"]))

    hours = {}
    last_in = {}

    for r in records:
        emp = r["emp"]

        if r["action"] == "in":
            last_in[emp] = r["time"]

        elif r["action"] == "out" and emp in last_in:
            diff = (r["time"] - last_in[emp]).total_seconds() / 3600
            hours[emp] = hours.get(emp, 0) + round(diff, 2)

    return hours


# ===== WEB SERVER =====
class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/get-employees":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(load_employees()).encode())
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>OpenClaw Payroll Running</h1>")

    def do_POST(self):

        # ===== UPLOAD FILE =====
        if self.path == "/upload-timecard":
            import cgi
            ctype, pdict = cgi.parse_header(self.headers.get('Content-Type'))

            if ctype == 'multipart/form-data':
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                fields = cgi.parse_multipart(self.rfile, pdict)
                file_data = fields.get("file")[0]

                try:
                    hours = parse_timecard_xlsx(file_data)
                    result = {"success": True, "hours": hours}
                except Exception as e:
                    result = {"success": False, "error": str(e)}
            else:
                result = {"success": False}

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return

        # ===== CALCULATE =====
        length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(length))

        if self.path == "/calculate":
            result = calculate(data)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return


# ===== START SERVER =====
print("Running on port 8080...")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
