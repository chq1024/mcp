import subprocess
import json
import sys
import time

def test_mcp_server():
    # 启动 MCP 服务
    proc = subprocess.Popen(
        [sys.executable, 'mcp_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 发送 tools/list 请求
    req1 = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    proc.stdin.write(json.dumps(req1) + "\n")
    proc.stdin.flush()
    resp1 = proc.stdout.readline()
    print("tools/list 响应:", resp1)

    # 发送 tools/call 请求（假设有 user 表）
    req2 = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_table_schema",
            "arguments": {"table": "user"}
        }
    }
    proc.stdin.write(json.dumps(req2) + "\n")
    proc.stdin.flush()
    resp2 = proc.stdout.readline()
    print("get_table_schema 响应:", resp2)

    # 关闭进程
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

if __name__ == "__main__":
    test_mcp_server() 