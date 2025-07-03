#!/usr/bin/env python3
"""
MySQL MCP Server - 支持命令行直接查询
用法: python mysql_mcp.py --query "SELECT * FROM table_name"
"""

import argparse
import json
import sys
import pymysql
from pymysql.cursors import DictCursor

# 写死的数据库连接参数
def get_db_conn():
    return pymysql.connect(
        host='192.168.223.11',
        port=3306,
        user='tms',
        password='tms',
        db='docker_it48_product',
        charset='utf8mb4',
        cursorclass=DictCursor
    )

def execute_direct_query(sql):
    """直接执行SQL查询"""
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "result": result,
            "sql": sql,
            "row_count": len(result)
        }
    except Exception as e:
        return {"error": f"查询执行失败: {str(e)}"}

def get_table_schema(table):
    """获取表结构"""
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COLUMN_NAME, 
                    COLUMN_TYPE, 
                    COLUMN_COMMENT, 
                    COLUMN_KEY,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                ORDER BY ORDINAL_POSITION
            """, ('docker_it48_product', table))
            columns = cursor.fetchall()
        conn.close()
        
        return {
            "table": table,
            "columns": columns
        }
    except Exception as e:
        return {"error": f"获取表结构失败: {str(e)}"}

def main():
    parser = argparse.ArgumentParser(description='MySQL MCP Server')
    parser.add_argument('--query', help='直接执行SQL查询')
    parser.add_argument('--schema', help='获取表结构')
    parser.add_argument('--mcp', action='store_true', help='启动MCP服务器模式')
    parser.add_argument('--mcpcli', action='store_true', help='以mcpcli兼容模式启动（标准输入输出）')
    
    args = parser.parse_args()
    
    if args.query:
        # 直接查询模式
        result = execute_direct_query(args.query)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    
    elif args.schema:
        # 获取表结构模式
        result = get_table_schema(args.schema)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    
    elif args.mcp:
        # MCP服务器模式
        print("启动MCP服务器模式...", file=sys.stderr)
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import asyncio
            import mcp_server
            asyncio.run(mcp_server.main())
        except ImportError:
            print("错误: 无法导入 mcp_server 模块", file=sys.stderr)
            print("请确保 mcp_server.py 文件存在且在同一目录下", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"启动MCP服务器时发生错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    elif args.mcpcli:
        # MCP CLI兼容模式（直接运行mcp_server主循环，标准输入输出）
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import asyncio
            import mcp_server
            asyncio.run(mcp_server.main())
        except ImportError:
            print("错误: 无法导入 mcp_server 模块", file=sys.stderr)
            print("请确保 mcp_server.py 文件存在且在同一目录下", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"启动MCP服务器时发生错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    else:
        # 默认显示帮助
        parser.print_help()

if __name__ == "__main__":
    main() 