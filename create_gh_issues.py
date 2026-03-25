import re
import subprocess
import sys

GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe"

def create_issues():
    with open("LYRA_BUGS.md", "r", encoding="utf-8") as f:
        content = f.read()

    # extract open section
    open_section_match = re.search(r"## Open.*?\n(.*?)\n---", content, re.DOTALL)
    if not open_section_match:
        print("Could not find Open bugs section")
        return

    open_lines = open_section_match.group(1).strip().split('\n')
    
    # parse table rows
    for line in open_lines:
        line = line.strip()
        if not line.startswith("|") or "ID | Priority" in line or "|----" in line:
            continue
        
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            bug_id = parts[1]
            priority = parts[2]
            tag = parts[3]
            title = parts[4]
            notes = parts[5]
            
            # Form issue details
            issue_title = f"[{bug_id}] {title}"
            issue_body = f"**Notes:** {notes}\n**Tag:** {tag}\n**Priority:** {priority}"
            
            labels = ["bug"]
            if "high" in priority.lower() or "🔴" in priority:
                labels.append("high-priority")
            
            # Execute gh issue create
            cmd = [GH_PATH, "issue", "create", "-R", "Holmesberg/lyra-secretary", "-t", issue_title, "-b", issue_body]
            for label in labels:
                cmd.extend(["-l", label])
                
            print(f"Creating issue: {issue_title} with labels {labels}")
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Failed to create {bug_id}: {res.stderr}")
            else:
                print(f"Success: {res.stdout.strip()}")

if __name__ == "__main__":
    create_issues()
