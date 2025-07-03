import asyncio
import json
import sys
import pymysql
from pymysql.cursors import DictCursor

# 写死的数据库连接参数
def get_db_conn():
    return pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        db='docker_product',
        charset='utf8mb4',
        cursorclass=DictCursor
    )

def get_table_schema(table):
    """获取表结构 - 供LLM分析自然语言时使用"""
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 获取字段信息
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
            
            # 获取外键信息
            cursor.execute("""
                SELECT 
                    COLUMN_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, ('docker_it48_product', table))
            foreign_keys = cursor.fetchall()
            
            # 获取索引信息
            cursor.execute("""
                SELECT 
                    INDEX_NAME,
                    COLUMN_NAME,
                    NON_UNIQUE,
                    SEQ_IN_INDEX
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, ('docker_it48_product', table))
            indexes = cursor.fetchall()
            
        conn.close()
        
        return {
            "table": table,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "description": f"表 {table} 的完整结构信息，包括字段名、类型、注释、主键、外键、索引等"
        }
    except Exception as e:
        return {"error": f"获取表结构失败: {str(e)}"}

def execute_query(query_params):
    """执行查询 - 根据LLM解析的自然语言执行数据库查询"""
    try:
        tables = query_params.get("tables", [])
        fields = query_params.get("fields", [])
        conditions = query_params.get("conditions", {})
        joins = query_params.get("joins", [])
        order_by = query_params.get("order_by", "")
        limit = query_params.get("limit", "")
        
        if not tables or not fields:
            return {"error": "缺少tables或fields参数"}
        
        # 生成SQL
        select_fields = ', '.join(fields)
        from_clause = tables[0]
        
        # 处理JOIN
        join_clauses = []
        for join in joins:
            left = join.get('left', '')
            right = join.get('right', '')
            join_type = join.get('type', 'JOIN')
            if left and right:
                right_table = right.split('.')[0]
                join_clauses.append(f"{join_type} {right_table} ON {left} = {right}")
        
        # 处理WHERE条件
        where_clauses = []
        params = []
        for k, v in conditions.items():
            if isinstance(v, dict):
                # 支持复杂条件：{"operator": "LIKE", "value": "%test%"}
                operator = v.get("operator", "=")
                value = v.get("value", "")
                where_clauses.append(f"{k} {operator} %s")
                params.append(value)
            else:
                where_clauses.append(f"{k}=%s")
                params.append(v)
        
        # 构建完整SQL
        sql = f"SELECT {select_fields} FROM {from_clause}"
        if join_clauses:
            sql += " " + " ".join(join_clauses)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        
        # 执行查询
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "result": result,
            "sql": sql,
            "row_count": len(result),
            "description": f"查询成功，返回 {len(result)} 条记录"
        }
    except Exception as e:
        return {"error": f"查询执行失败: {str(e)}"}

async def handle_mcp_message():
    """处理MCP消息"""
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            data = json.loads(line.strip())
            method = data.get("method")
            params = data.get("params", {})
            id = data.get("id")
            
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "tools": [
                            {
                                "name": "get_table_schema",
                                "description": "获取指定表的完整结构信息，供LLM分析自然语言时使用。返回字段名、类型、注释、主键、外键、索引等信息。",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {
                                            "type": "string",
                                            "description": "要查询的表名"
                                        }
                                    },
                                    "required": ["table"]
                                }
                            },
                            {
                                "name": "execute_query",
                                "description": "根据LLM解析的自然语言执行数据库查询，支持多表关联、复杂条件、排序、分页等。",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "tables": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "要查询的表名列表，第一个为主表"
                                        },
                                        "fields": {
                                            "type": "array", 
                                            "items": {"type": "string"},
                                            "description": "要查询的字段列表，格式为table.column"
                                        },
                                        "conditions": {
                                            "type": "object",
                                            "description": "查询条件，支持简单条件(字段=值)和复杂条件(字段={operator: 'LIKE', value: '%test%'})"
                                        },
                                        "joins": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "left": {"type": "string", "description": "左表字段"},
                                                    "right": {"type": "string", "description": "右表字段"},
                                                    "type": {"type": "string", "description": "JOIN类型，默认JOIN"}
                                                }
                                            },
                                            "description": "表关联条件"
                                        },
                                        "order_by": {
                                            "type": "string",
                                            "description": "排序字段，如'id DESC'"
                                        },
                                        "limit": {
                                            "type": "string",
                                            "description": "限制返回记录数，如'10'"
                                        }
                                    },
                                    "required": ["tables", "fields"]
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "get_table_schema":
                    table = arguments.get("table")
                    result = get_table_schema(table)
                elif tool_name == "execute_query":
                    result = execute_query(arguments)
                else:
                    result = {"error": f"未知工具: {tool_name}"}
                
                response = {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
                            }
                        ]
                    }
                }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": id,
                    "error": {
                        "code": -32601,
                        "message": f"方法未找到: {method}"
                    }
                }
            
            # 发送响应
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: sys.stdout.write(json.dumps(response) + "\n")
            )
            await asyncio.get_event_loop().run_in_executor(None, sys.stdout.flush)
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": id if 'id' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                }
            }
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: sys.stdout.write(json.dumps(error_response) + "\n")
            )
            await asyncio.get_event_loop().run_in_executor(None, sys.stdout.flush)

async def main():
    await handle_mcp_message()

if __name__ == "__main__":
    asyncio.run(main()) 
