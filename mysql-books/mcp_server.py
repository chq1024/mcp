import pymysql
from fastmcp import FastMCP
import db_config
from pymysql.cursors import DictCursor

# 全局持久数据库连接
conn = pymysql.connect(
    host=db_config.DB_HOST,
    port=db_config.DB_PORT,
    user=db_config.DB_USER,
    password=db_config.DB_PASSWORD,
    db=db_config.DB_NAME,
    charset=db_config.DB_CHARSET,
    cursorclass=DictCursor
)

mcp = FastMCP("MySQL Books MCP Server")

@mcp.tool()
def get_table_schema(table: str):
    """获取表结构 - 供LLM分析自然语言时使用"""
    try:
        conn.ping(reconnect=True)
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
            
        return {
            "table": table,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "description": f"表 {table} 的完整结构信息，包括字段名、类型、注释、主键、外键、索引等"
        }
    except Exception as e:
        return {"error": f"获取表结构失败: {str(e)}"}

@mcp.tool()
def execute_query(
    tables: list,
    fields: list,
    conditions: dict = {},
    joins: list = [],
    order_by: str = "",
    limit: str = ""
):
    """执行查询 - 根据LLM解析的自然语言执行数据库查询"""
    try:
        if not tables or not fields:
            return {"error": "缺少tables或fields参数"}
        
        conn.ping(reconnect=True)
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
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchall()
        return {
            "success": True,
            "result": result,
            "sql": sql,
            "row_count": len(result),
            "description": f"查询成功，返回 {len(result)} 条记录"
        }
    except Exception as e:
        return {"error": f"查询执行失败: {str(e)}"}

if __name__ == "__main__":
    mcp.run() 

