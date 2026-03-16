import subprocess
import urllib.request
import json
import re

def ask_ollama(task):
    data = json.dumps({
        "model": "llama3.2",
        "prompt": f"You are a Linux terminal. Reply with ONE raw command only, no explanation, no backticks, no markdown. Task: {task}",
        "stream": False
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        raw = json.loads(r.read())["response"].strip()
    command = re.sub(r'[`\n].*', '', raw).strip()
    return command

def run_task(task):
    print(f"\nThinking...")
    command = ask_ollama(task)
    print(f"Command: {command}")
    confirm = input("Run this? (yes/no): ")
    if confirm.lower() == "yes":
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Error:\n{result.stderr}")

while True:
    task = input("\nOpenClaw - what do you want to do? (or quit): ")
    if task.lower() == "quit":
        break
    run_task(task)
