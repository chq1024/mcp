#!/usr/bin/env python3
"""
MySQL MCP Server - 仅支持MCP服务启动
"""

import sys

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MySQL MCP Server (MCP only)')
    parser.add_argument('--mcp', action='store_true', help='启动MCP服务器模式')
    parser.add_argument('--mcpcli', action='store_true', help='以mcpcli兼容模式启动（标准输入输出）')
    args = parser.parse_args()

    if args.mcp or args.mcpcli:
        try:
            from mcp_server import mcp
            mcp.run()
        except ImportError:
            print("错误: 无法导入 mcp_server 模块", file=sys.stderr)
            print("请确保 mcp_server.py 文件存在且在同一目录下", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"启动MCP服务器时发生错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 