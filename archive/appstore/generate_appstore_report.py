import json, subprocess, sys, time

def run_mcp_query(method, params):
    proc = subprocess.Popen(['npx.cmd', '-y', 'appstore-rejections-mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    def send(m, p, i):
        proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': i, 'method': m, 'params': p}) + '\n')
        proc.stdin.flush()

    def read():
        while True:
            line = proc.stdout.readline()
            if not line: return None
            try: return json.loads(line)
            except json.JSONDecodeError: continue

    send('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1.0'}}, 1)
    read()

    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
    proc.stdin.flush()

    send('tools/call', {'name': method, 'arguments': params}, 2)
    resp = read()
    proc.terminate()
    return resp

queries = [
    "background behavioral data tracking",
    "predictive AI analysis without prompt",
    "background location and activity sensors"
]

results = []
for q in queries:
    resp = run_mcp_query('search_rejections', {'query': q})
    try:
        content = resp['result']['content'][0]['text']
        results.append(f"### Query: {q}\n{content}\n")
    except Exception as e:
        results.append(f"### Query: {q}\nError: {e}\n")

with open('appstore_rejection_report.md', 'w') as f:
    f.write("# App Store Rejection Risk Analysis for Lyra Secretary\n\n")
    f.write("\n".join(results))
