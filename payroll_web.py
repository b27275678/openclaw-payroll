import json
import csv
import os
import re
import io
try:
    import openpyxl
    HAS_OPENPYXL = True
except:
    HAS_OPENPYXL = False
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

FEDERAL_TAX = 0.1077
STATE_TAX = 0.0444
SOCIAL_SECURITY = 0.062
MEDICARE = 0.0145
YTD_FILE = "ytd_data.json"
EMPLOYEES_FILE = "employees.json"

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

def calculate(data):
    r = float(data.get("regular_hours", 0))
    o = float(data.get("overtime_hours", 0))
    h = float(data.get("holiday_hours", 0))
    bt_h = float(data.get("bonus_travel_hours", 0))
    bt_r = float(data.get("bonus_travel_rate", 0))
    rate = float(data.get("hourly_rate", 0))
    regular_pay = r * rate
    overtime_pay = o * (rate * 1.5)
    holiday_pay = h * rate
    bonus_pay = bt_h * bt_r
    gross = regular_pay + overtime_pay + holiday_pay + bonus_pay
    federal = gross * FEDERAL_TAX
    state = gross * STATE_TAX
    ss = gross * SOCIAL_SECURITY
    medicare = gross * MEDICARE
    tools = float(data.get("tools_purch", 0))
    levy = float(data.get("levy_garn", 0))
    insurance = float(data.get("insurance", 0))
    net = gross - federal - state - ss - medicare - tools - levy - insurance
    return {
        "name": data.get("name"),
        "emp_id": data.get("emp_id"),
        "hourly_rate": rate,
        "regular_hours": r, "regular_pay": round(regular_pay, 2),
        "overtime_hours": o, "overtime_pay": round(overtime_pay, 2),
        "holiday_hours": h, "holiday_pay": round(holiday_pay, 2),
        "bonus_travel_hours": bt_h, "bonus_travel_rate": bt_r, "bonus_pay": round(bonus_pay, 2),
        "gross": round(gross, 2),
        "federal": round(federal, 2),
        "state": round(state, 2),
        "social_security": round(ss, 2),
        "medicare": round(medicare, 2),
        "tools_purch": round(tools, 2),
        "levy_garn": round(levy, 2),
        "insurance": round(insurance, 2),
        "net": round(net, 2)
    }

def parse_duration(s):
    if not s: return 0
    s = str(s)
    total = 0
    h = re.search(r'(\d+)\s*hr', s)
    m = re.search(r'(\d+)\s*min', s)
    sc = re.search(r'(\d+)\s*sec', s)
    if h: total += int(h.group(1))
    if m: total += int(m.group(1)) / 60
    if sc: total += int(sc.group(1)) / 3600
    return round(total, 2)

def parse_timecard_xlsx(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    hours = {}
    current_employee = None

    for row in ws.iter_rows(values_only=True):
        cells = [str(c).strip() if c is not None else '' for c in row]
        row_text = " ".join(cells).upper()

        if "TOTAL" in row_text:
            name = row_text.replace("TOTAL", "").strip()
            if name:
                current_employee = name
                hours[current_employee] = 0

        duration_cell = next((c for c in cells if "HR" in c or "MIN" in c), None)

        if current_employee and duration_cell:
            hrs = parse_duration(duration_cell)
            hours[current_employee] += hrs

    return hours
def parse_timecard_csv(content):
    hours = {}
    current_emp = None
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line: continue
        parts = [p.strip().strip('"') for p in line.split(',')]
        full = ' '.join(parts)
        if 'TOTAL' in full:
            name = parts[0].replace('TOTAL', '').strip()
            dur = next((p for p in parts if 'min' in p or 'hr' in p), '')
            if name:
                current_emp = name
                hours[name] = parse_duration(dur) if dur and dur != '0 mins' else 0
        elif 'Out' in parts and current_emp:
            dur = next((p for p in parts if ('hr' in p or 'min' in p) and p), '')
            if dur:
                hours[current_emp] = hours.get(current_emp, 0) + parse_duration(dur)
    return hours

HTML = """<!DOCTYPE html>
<html>
<head>
<title>OpenClaw Payroll</title>
<style>
body{font-family:Arial;background:#1a1a2e;color:#eee;margin:0;padding:20px}
h1{color:#f5e642;text-align:center}
h2{color:#f5e642}
.card{background:#16213e;border-radius:10px;padding:20px;margin:20px auto;max-width:900px}
input,select{background:#0f3460;border:1px solid #f5e642;color:#fff;padding:8px;border-radius:5px;width:100%;box-sizing:border-box;margin:4px 0}
label{font-size:12px;color:#aaa}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
button{background:#f5e642;color:#000;border:none;padding:12px 24px;border-radius:5px;cursor:pointer;font-weight:bold;font-size:16px;margin:10px 5px}
button:hover{opacity:0.9}
.add-btn{background:#27ae60;color:#fff}
.remove-btn{background:#e74c3c;color:#fff;padding:6px 12px;font-size:12px}
.sync-btn{background:#1d9e75;color:#fff;width:100%;margin:8px 0;padding:14px;font-size:16px}
.stub{background:#0f3460;border-radius:8px;padding:15px;margin:10px 0;font-family:monospace}
.stub h3{color:#f5e642;margin:0 0 10px}
.row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #333}
.total{color:#f5e642;font-weight:bold;font-size:18px}
.summary{background:#27ae60;border-radius:8px;padding:15px;margin:10px 0;text-align:center}
.sync-box{background:#0a2a1a;border:1px solid #1d9e75;border-radius:8px;padding:15px;margin-bottom:15px}
.sync-box h3{color:#1d9e75;margin:0 0 10px}
.alert{padding:10px;border-radius:5px;margin:8px 0;font-size:13px}
.alert-info{background:#0f3460;border:1px solid #4a90d9;color:#adf}
.alert-success{background:#0a2a1a;border:1px solid #27ae60;color:#afd}
.alert-warn{background:#2a1a0a;border:1px solid #f5e642;color:#fda}
.tabs{display:flex;gap:5px;margin-bottom:15px;max-width:900px;margin:0 auto 15px}
.tab{padding:10px 20px;border-radius:5px;cursor:pointer;background:#0f3460;border:1px solid #333;color:#eee}
.tab.active{background:#f5e642;color:#000;font-weight:bold}
.tab-content{display:none;max-width:900px;margin:0 auto}
.tab-content.active{display:block}
</style>
</head>
<body>
<h1>&#9889; OpenClaw Payroll</h1>
<h2 style="text-align:center;color:#aaa">Electrical Systems Inc.</h2>
<div class="tabs">
  <div class="tab active" onclick="showTab('sync',this)">1. Import Hours</div>
  <div class="tab" onclick="showTab('employees',this)">2. Employees</div>
  <div class="tab" onclick="showTab('payroll',this)">3. Run Payroll</div>
</div>
<div id="tab-sync" class="tab-content active">
<div class="card">
  <h2>Import Hours from RazorSync</h2>
  <div class="sync-box">
    <h3>Step-by-step every payday:</h3>
    <div class="alert alert-info">
      1. Go to RazorSync &rarr; Reports &rarr; Time Card &rarr; Detailed Time Card<br>
      2. Set your pay period dates and click RUN<br>
      3. Click EXPORT TO EXCEL and save the file<br>
      4. Upload that file below &mdash; hours fill in automatically!
    </div>
    <label>Upload RazorSync Time Card File (Excel or CSV)</label>
    <input type="file" id="timecard-file" accept=".csv,.xlsx,.xls" style="margin:10px 0">
    <button class="sync-btn" onclick="uploadTimecard()">Upload &amp; Auto-Fill Hours</button>
    <div id="sync-result"></div>
  </div>
</div>
</div>
<div id="tab-employees" class="tab-content">
<div class="card">
  <h2>Employees</h2>
  <div id="employees"></div>
  <button class="add-btn" onclick="addEmployee()">+ Add Employee</button>
  <button onclick="saveEmployees()" style="background:#4a90d9;color:#fff;margin-left:10px">Save Employee List</button>
</div>
</div>
<div id="tab-payroll" class="tab-content">
<div class="card">
  <button onclick="runPayroll()" style="width:100%;font-size:20px;padding:16px">RUN PAYROLL</button>
</div>
<div class="card" id="results" style="display:none">
  <h2>Pay Stubs</h2>
  <div id="stubs"></div>
  <div class="summary" id="summary"></div>
  <button onclick="savePayroll()">&#128190; Save to CSV</button>
</div>
</div>
<script>
let empCount=0,payrollData=[];
function showTab(name,el){
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  el.classList.add('active');
}
async function uploadTimecard(){
  const file=document.getElementById('timecard-file').files[0];
  if(!file){alert('Please select a file first');return;}
  const res=document.getElementById('sync-result');
  res.innerHTML='<div class="alert alert-info">Reading file...</div>';
  const formData=new FormData();
  formData.append('file',file);
  try{
    const r=await fetch('/upload-timecard',{method:'POST',body:formData});
    const data=await r.json();
    if(data.success&&Object.keys(data.hours).length>0){
      let msg='<div class="alert alert-success">Hours updated:<br>';
      Object.entries(data.hours).forEach(([name,hrs])=>{
        const reg=Math.min(hrs,40),ot=Math.max(hrs-40,0);
        msg+=`&bull; ${name}: ${hrs} hrs`;
        if(ot>0)msg+=` (${reg} reg + ${ot} OT)`;
        msg+='<br>';
      });
      msg+='<br>Go to Employees tab to review, then Run Payroll!</div>';
      res.innerHTML=msg;
      updateEmployeeHours(data.hours);
    } else {
      res.innerHTML='<div class="alert alert-warn">No hours found in file. Make sure you exported the Detailed Time Card from RazorSync.</div>';
    }
  }catch(e){
    res.innerHTML='<div class="alert alert-warn">Upload failed: '+e.message+'</div>';
  }
}
function updateEmployeeHours(hours){
  for(let i=1;i<=empCount;i++){
    const el=document.getElementById('emp_'+i);
    if(!el)continue;
    const nameEl=document.getElementById('name_'+i);
    if(!nameEl)continue;
    const name=nameEl.value.toLowerCase().trim();
    for(const[empName,totalHrs]of Object.entries(hours)){
      const en=empName.toLowerCase();
      const firstName=en.split(' ')[0];
      const lastName=en.split(' ').slice(-1)[0];
      if(name&&(en.includes(name)||name.includes(firstName)||name.includes(lastName)||firstName.includes(name.split(' ')[0]))){
        document.getElementById('reg_'+i).value=Math.min(totalHrs,40).toFixed(2);
        document.getElementById('ot_'+i).value=Math.max(totalHrs-40,0).toFixed(2);
        break;
      }
    }
  }
}
function addEmployee(data){
  empCount++;
  const d=data||{};
  const div=document.createElement('div');
  div.id='emp_'+empCount;
  div.style='background:#0f3460;padding:15px;border-radius:8px;margin:10px 0';
  div.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center">
      <b>Employee #${empCount}</b>
      <button class="remove-btn" onclick="removeEmp(${empCount})">Remove</button>
    </div>
    <div class="grid2">
      <div><label>Full Name</label><input placeholder="JOHN SMITH" id="name_${empCount}" value="${d.name||''}"></div>
      <div><label>Employee ID</label><input placeholder="ID" id="emp_id_${empCount}" value="${d.emp_id||''}"></div>
    </div>
    <div class="grid">
      <div><label>Hourly Rate $</label><input type="number" id="rate_${empCount}" step="0.01" value="${d.rate||''}"></div>
      <div><label>Regular Hours</label><input type="number" id="reg_${empCount}" step="0.01" value="${d.reg||80}"></div>
      <div><label>Overtime Hours</label><input type="number" id="ot_${empCount}" step="0.01" value="${d.ot||0}"></div>
    </div>
    <div class="grid">
      <div><label>Holiday Hours</label><input type="number" id="hol_${empCount}" step="0.01" value="${d.holiday||0}"></div>
      <div><label>BonusTravel Hours</label><input type="number" id="bt_h_${empCount}" step="0.01" value="${d.travel||0}"></div>
      <div><label>BonusTravel Rate $</label><input type="number" id="bt_r_${empCount}" step="0.01" value="${d.travelRate||0}"></div>
    </div>
    <div class="grid">
      <div><label>ToolsPurch $</label><input type="number" id="tools_${empCount}" step="0.01" value="${d.tools||0}"></div>
      <div><label>LevyGarn $</label><input type="number" id="levy_${empCount}" step="0.01" value="${d.levy||0}"></div>
      <div><label>Insurance $</label><input type="number" id="ins_${empCount}" step="0.01" value="${d.insurance||0}"></div>
    </div>`;
  document.getElementById('employees').appendChild(div);
}
function removeEmp(n){document.getElementById('emp_'+n).remove();}
async function saveEmployees(){
  const emps=[];
  for(let i=1;i<=empCount;i++){
    const el=document.getElementById('emp_'+i);
    if(!el)continue;
    emps.push({name:document.getElementById('name_'+i).value,emp_id:document.getElementById('emp_id_'+i).value,rate:document.getElementById('rate_'+i).value,reg:document.getElementById('reg_'+i).value,ot:document.getElementById('ot_'+i).value,holiday:document.getElementById('hol_'+i).value,travel:document.getElementById('bt_h_'+i).value,travelRate:document.getElementById('bt_r_'+i).value,tools:document.getElementById('tools_'+i).value,levy:document.getElementById('levy_'+i).value,insurance:document.getElementById('ins_'+i).value});
  }
  await fetch('/save-employees',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(emps)});
  alert('Employees saved!');
}
async function runPayroll(){
  payrollData=[];
  for(let i=1;i<=empCount;i++){
    const el=document.getElementById('emp_'+i);
    if(!el)continue;
    const emp={name:document.getElementById('name_'+i).value,emp_id:document.getElementById('emp_id_'+i).value,hourly_rate:document.getElementById('rate_'+i).value,regular_hours:document.getElementById('reg_'+i).value,overtime_hours:document.getElementById('ot_'+i).value,holiday_hours:document.getElementById('hol_'+i).value,bonus_travel_hours:document.getElementById('bt_h_'+i).value,bonus_travel_rate:document.getElementById('bt_r_'+i).value,tools_purch:document.getElementById('tools_'+i).value,levy_garn:document.getElementById('levy_'+i).value,insurance:document.getElementById('ins_'+i).value};
    const res=await fetch('/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(emp)});
    payrollData.push(await res.json());
  }
  showResults();
}
function showResults(){
  document.getElementById('results').style.display='block';
  let html='',totalGross=0,totalNet=0;
  payrollData.forEach(p=>{
    totalGross+=p.gross;totalNet+=p.net;
    html+=`<div class="stub"><h3>${p.name} &mdash; Check Date: ${new Date().toLocaleDateString()}</h3>
      <div class="row"><span>Gross Pay</span><span>$${p.gross.toFixed(2)}</span></div>
      <div class="row"><span>Federal Income</span><span>-$${p.federal.toFixed(2)}</span></div>
      <div class="row"><span>Soc Sec</span><span>-$${p.social_security.toFixed(2)}</span></div>
      <div class="row"><span>Medicare</span><span>-$${p.medicare.toFixed(2)}</span></div>
      <div class="row"><span>State (KS)</span><span>-$${p.state.toFixed(2)}</span></div>
      <div class="row"><span>ToolsPurch</span><span>-$${p.tools_purch.toFixed(2)}</span></div>
      <div class="row"><span>LevyGarn</span><span>-$${p.levy_garn.toFixed(2)}</span></div>
      <div class="row"><span>Insurance</span><span>-$${p.insurance.toFixed(2)}</span></div>
      <div class="row"><span>Regular ${p.regular_hours}hrs @ $${p.hourly_rate}</span><span>$${p.regular_pay.toFixed(2)}</span></div>
      <div class="row"><span>Overtime ${p.overtime_hours}hrs @ $${(p.hourly_rate*1.5).toFixed(2)}</span><span>$${p.overtime_pay.toFixed(2)}</span></div>
      <div class="row"><span>Holiday ${p.holiday_hours}hrs</span><span>$${p.holiday_pay.toFixed(2)}</span></div>
      <div class="row total"><span>NET CHECK</span><span>$${p.net.toFixed(2)}</span></div></div>`;
  });
  document.getElementById('stubs').innerHTML=html;
  document.getElementById('summary').innerHTML=`Total Employees: ${payrollData.length} | Total Gross: $${totalGross.toFixed(2)} | Total Net: $${totalNet.toFixed(2)}`;
}
async function savePayroll(){
  await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payrollData)});
  alert('Payroll saved!');
}
fetch('/get-employees').then(r=>r.json()).then(emps=>{
  if(emps&&emps.length>0)emps.forEach(e=>addEmployee(e));
  else addEmployee();
});
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):pass
    def do_GET(self):
        if self.path=='/get-employees':
            emps=load_employees()
            self.send_response(200)
            self.send_header("Content-type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(emps).encode())
        else:
            self.send_response(200)
            self.send_header("Content-type","text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())
    def do_POST(self):
        if self.path=='/upload-timecard':
            import cgi
            ctype,pdict=cgi.parse_header(self.headers.get('Content-Type',''))
            if ctype=='multipart/form-data':
                pdict['boundary']=bytes(pdict['boundary'],'utf-8')
                fields=cgi.parse_multipart(self.rfile,pdict)
                file_data=fields.get('file',[b''])[0]
                if not isinstance(file_data,bytes):
                    file_data=str(file_data).encode()
                try:
                    if HAS_OPENPYXL:
                        try:
                            hours=parse_timecard_xlsx(file_data)
                            if not hours:
                                raise Exception("No hours in xlsx")
                        except:
                            hours=parse_timecard_csv(file_data.decode('utf-8',errors='ignore'))
                    else:
                        hours=parse_timecard_csv(file_data.decode('utf-8',errors='ignore'))
                    result={'success':True,'hours':hours}
                except Exception as e:
                    result={'success':False,'error':str(e)}
            else:
                result={'success':False,'error':'Invalid upload'}
            self.send_response(200)
            self.send_header("Content-type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
        length=int(self.headers["Content-Length"])
        data=json.loads(self.rfile.read(length))
        if self.path=="/calculate":
            result=calculate(data)
            ytd=load_ytd()
            name=result["name"]
            if name not in ytd:
                ytd[name]={k:0 for k in ["gross","federal","social_security","medicare","state","tools_purch","levy_garn","insurance","net"]}
            for k in ytd[name]:
                ytd[name][k]=round(ytd[name][k]+result.get(k,0),2)
            save_ytd(ytd)
            self.send_response(200)
            self.send_header("Content-type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        elif self.path=="/save":
            filename=f"payroll_{datetime.now().strftime('%Y%m%d')}.csv"
            with open(filename,"w",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            self.send_response(200)
            self.end_headers()
        elif self.path=="/save-employees":
            save_employees(data)
            self.send_response(200)
            self.end_headers()

print("OpenClaw Payroll running at http://localhost:8080")
HTTPServer(("0.0.0.0",8080),Handler).serve_forever()
