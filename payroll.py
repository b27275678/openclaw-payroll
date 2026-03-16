import csv
import os
import json
from datetime import datetime

# Tax brackets (federal)
def federal_tax(gross):
    if gross <= 500:
        return gross * 0.10
    elif gross <= 1500:
        return gross * 0.12
    elif gross <= 3000:
        return gross * 0.1077
    else:
        return gross * 0.107729

# Kansas state tax
def state_tax(gross):
    if gross <= 1500:
        return gross * 0.0427
import csv
import os
import json
from datetime import datetime

# Tax brackets (federal)
def federal_tax(gross):
    if gross <= 500:
        return gross * 0.10
    elif gross <= 1500:
        return gross * 0.12
    elif gross <= 3000:
        return gross * 0.1077
    else:
        return gross * 0.107729

# Kansas state tax
def state_tax(gross):
    if gross <= 1500:
        return gross * 0.0427
    else:
        return gross * 0.0444

SOCIAL_SECURITY = 0.062
MEDICARE = 0.0145
YTD_FILE = "ytd_data.json"

def load_ytd():
    if os.path.exists(YTD_FILE):
        with open(YTD_FILE) as f:
            return json.load(f)
    return {}

def save_ytd(ytd):
    with open(YTD_FILE, "w") as f:
        json.dump(ytd, f, indent=2)

def ask_money(prompt):
    while True:
        val = input(prompt).strip()
        if not val:
            return 0.0
        try:
            return float(val)
        except:
            print("  Please enter a number.")

def ask_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except:
            print("  Please enter a number.")

def calculate_pay(regular_hours, overtime_hours, holiday_hours, bonus_travel_hours, bonus_travel_rate, hourly_rate, deductions):
    regular_pay = regular_hours * hourly_rate
    overtime_pay = overtime_hours * (hourly_rate * 1.5)
    holiday_pay = holiday_hours * hourly_rate
    bonus_travel_pay = bonus_travel_hours * bonus_travel_rate
    gross = regular_pay + overtime_pay + holiday_pay + bonus_travel_pay

    fed = federal_tax(gross)
    state = state_tax(gross)
    ss = gross * SOCIAL_SECURITY
    medicare = gross * MEDICARE

    tools = deductions.get("tools_purch", 0)
    levy = deductions.get("levy_garn", 0)
    insurance = deductions.get("insurance", 0)

    total_deductions = fed + state + ss + medicare + tools + levy + insurance
    net = gross - total_deductions

    return {
        "regular_hours": regular_hours,
        "overtime_hours": overtime_hours,
        "holiday_hours": holiday_hours,
        "bonus_travel_hours": bonus_travel_hours,
        "bonus_travel_rate": bonus_travel_rate,
        "hourly_rate": hourly_rate,
        "regular_pay": round(regular_pay, 2),
        "overtime_pay": round(overtime_pay, 2),
        "holiday_pay": round(holiday_pay, 2),
        "bonus_travel_pay": round(bonus_travel_pay, 2),
        "gross": round(gross, 2),
        "federal": round(fed, 2),
        "state": round(state, 2),
        "social_security": round(ss, 2),
        "medicare": round(medicare, 2),
        "tools_purch": round(tools, 2),
        "levy_garn": round(levy, 2),
        "insurance": round(insurance, 2),
        "net": round(net, 2)
    }

def get_deductions(name):
    print(f"\n  Deductions for {name} (press Enter for $0):")
    return {
        "tools_purch": ask_money("  ToolsPurch: $"),
        "levy_garn":   ask_money("  LevyGarn:   $"),
        "insurance":   ask_money("  Insurance:  $")
    }

def update_ytd(ytd_data, name, pay):
    if name not in ytd_data:
        ytd_data[name] = {
            "gross": 0, "federal": 0, "social_security": 0,
            "medicare": 0, "state": 0, "tools_purch": 0,
            "levy_garn": 0, "insurance": 0, "net": 0
        }
    for key in ytd_data[name]:
        ytd_data[name][key] = round(ytd_data[name][key] + pay.get(key, 0), 2)
    return ytd_data[name]

def print_stub(name, emp_id, check_num, pay, ytd):
    print(f"""
==================================
  Electrical Systems Inc.  #{check_num}
==================================
  {name}
  Employee ID: {emp_id}
  Check Date:  {datetime.now().strftime('%m/%d/%y')}
----------------------------------
                 This Check       YTD
Gross           ${pay['gross']:>8.2f}   ${ytd['gross']:>10.2f}
Fed Income      -${pay['federal']:>7.2f}   -${ytd['federal']:>9.2f}
Soc Sec         -${pay['social_security']:>7.2f}   -${ytd['social_security']:>9.2f}
Medicare        -${pay['medicare']:>7.2f}   -${ytd['medicare']:>9.2f}
State           -${pay['state']:>7.2f}   -${ytd['state']:>9.2f}
ToolsPurch      -${pay['tools_purch']:>7.2f}   -${ytd['tools_purch']:>9.2f}
LevyGarn        -${pay['levy_garn']:>7.2f}   -${ytd['levy_garn']:>9.2f}
Insurance       -${pay['insurance']:>7.2f}   -${ytd['insurance']:>9.2f}
----------------------------------
                  Hours   Rate    Total
Regular        {pay['regular_hours']:>7.2f} {pay['hourly_rate']:>6.2f} {pay['regular_pay']:>8.2f}
Overtime       {pay['overtime_hours']:>7.2f} {pay['hourly_rate']*1.5:>6.2f} {pay['overtime_pay']:>8.2f}
Holiday        {pay['holiday_hours']:>7.2f} {pay['hourly_rate']:>6.2f} {pay['holiday_pay']:>8.2f}
BonusTravel    {pay['bonus_travel_hours']:>7.2f} {pay['bonus_travel_rate']:>6.2f} {pay['bonus_travel_pay']:>8.2f}
----------------------------------
Net Check:      ${pay['net']:.2f}
==================================
""")

check_num_file = "check_number.txt"
if os.path.exists(check_num_file):
    with open(check_num_file) as f:
        check_num = int(f.read().strip())
else:
    check_num = int(input("Starting check number: "))

ytd_data = load_ytd()
employees = []

print("\n=== OPENCLAW PAYROLL - Electrical Systems Inc. ===")
print("Type 'done' when all employees are entered.\n")

while True:
    name = input("\nEmployee name (or 'done'): ").strip()
    if name.lower() == "done":
        break
    if len(name) < 2:
        print("  Please enter full name.")
        continue

    emp_id = input(f"Employee ID for {name}: ").strip()
    hourly_rate = ask_float("Hourly rate: $")
    regular_hours = ask_float("Regular hours: ")
    overtime_hours = ask_float("Overtime hours (0 if none): ")
    holiday_hours = ask_float("Holiday hours (0 if none): ")
    bonus_travel_hours = ask_float("BonusTravel hours (0 if none): ")
    bonus_travel_rate = ask_float("BonusTravel rate (0 if none): $") if bonus_travel_hours > 0 else 0
    deductions = get_deductions(name)

    pay = calculate_pay(regular_hours, overtime_hours, holiday_hours, bonus_travel_hours, bonus_travel_rate, hourly_rate, deductions)
    ytd = update_ytd(ytd_data, name, pay)
    print_stub(name, emp_id, check_num, pay, ytd)

    employees.append({"check": check_num, "name": name, "emp_id": emp_id, **pay})
    check_num += 1

if employees:
    save_ytd(ytd_data)
    with open(check_num_file, "w") as f:
        f.write(str(check_num))
    filename = f"payroll_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=employees[0].keys())
        writer.writeheader()
        writer.writerows(employees)
    print(f"\n✅ Payroll complete!")
    print(f"   Employees paid:  {len(employees)}")
    print(f"   Total gross:     ${sum(e['gross'] for e in employees):.2f}")
    print(f"   Total net:       ${sum(e['net'] for e in employees):.2f}")
    print(f"   Saved to:        {filename}")
