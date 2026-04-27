import time

from flask import Flask, jsonify, request, session, flash, redirect, url_for
import hashlib
from pymysql import Connection
import traceback
from datetime import datetime

app = Flask(__name__)
app.secret_key = '42a2c4e3f7a5b6d9c0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1'


def get_db_connection():
    """创建数据库连接"""
    try:
        return Connection(host="127.0.0.1", user="root", password="111222", database="dnf_script", autocommit=False)
    except Exception as e:
        return None


def hash_password(password):
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def initialize_database():
    """初始化数据库结构"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cursor:
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                  user_id INT AUTO_INCREMENT PRIMARY KEY,
                  username VARCHAR(50) UNIQUE NOT NULL,
                  password VARCHAR(255) NOT NULL,
                  role ENUM('admin', 'user') DEFAULT 'user',
                  expire_time DATETIME NOT NULL DEFAULT '2025-01-01 23:59:59'
                )
            """)

            cursor.execute("""
                INSERT IGNORE INTO users (username, password, role, expire_time)
                VALUES (%s, %s, %s, %s)
            """, ("admin", hash_password("123456"), "admin", "9999-12-31 23:59:59"))  # 使用哈希密码

            # 创建分组表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subgroup (
                  subgroup_id INT AUTO_INCREMENT PRIMARY KEY,
                  subgroup_name VARCHAR(50) NOT NULL,
                  username VARCHAR(50) NOT NULL,
                 UNIQUE KEY unique_user_subgroup (username, subgroup_name),
                  FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                )
            """)

            # 创建分组配置表 (修复外键约束)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subgroup_config (
                  subgroup_config_id INT AUTO_INCREMENT PRIMARY KEY,
                  username VARCHAR(50) NOT NULL,
                  subgroup_name VARCHAR(50) NOT NULL,
                  brush_order INT NOT NULL,
                  career VARCHAR(50) NOT NULL,
                  convert_career VARCHAR(50) NOT NULL,
                  height INT NOT NULL,
                  map VARCHAR(50) NOT NULL,
                  difficulty ENUM('1', '2','3','4','5') DEFAULT '1',
                  today_task_completed ENUM('是', '否') DEFAULT '是',
                  everyday_tasks ENUM('是', '否') DEFAULT '是',
                  leave_pl INT DEFAULT 0,
                  brush_map_expire_time DATETIME DEFAULT '2025-01-01 23:59:59',
                  UNIQUE KEY unique_user_subgroup_brush (username, subgroup_name, brush_order),
                  FOREIGN KEY (username, subgroup_name) 
                  REFERENCES subgroup(username, subgroup_name) 
                  ON DELETE CASCADE ON UPDATE CASCADE
                )
            """)

            conn.commit()
            print("数据库初始化完成")

    except Exception as e:
        print(f"初始化失败: {e}")
        traceback.print_exc()
        exit()


# ========================
# 路由处理函数（返回 JSON）
# ========================

@app.route('/')
def index():
    return jsonify({"message": "API 服务运行中"})


@app.route('/register', methods=['POST'])
def register():
    """注册路由"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "缺少必要参数"}), 400

    if len(username) < 3 or not username.isalnum():
        return jsonify({"error": "用户名格式错误"}), 400

    if len(password) < 6:
        return jsonify({"error": "密码至少6位"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"error": "用户名已存在"}), 400

            # 使用哈希密码
            hashed_password = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, 'user')
            """, (username, hashed_password))
            conn.commit()
            return jsonify({"message": "注册成功", "user": {"username": username}}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"注册失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "缺少必要参数"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 使用哈希密码比较
            hashed_password = hash_password(password)
            query = """
                SELECT user_id, username, role 
                FROM users 
                WHERE username = %s AND password = %s
            """
            cursor.execute(query, (username, hashed_password))
            result = cursor.fetchone()

            if result:
                session['user'] = {"user_id": result[0], "username": result[1], "role": result[2]}
                return jsonify({"message": "登录成功", "user": session['user']}), 200
            else:
                return jsonify({"error": "用户名或密码错误"}), 401

    except Exception as e:
        return jsonify({"error": f"登录失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/logout', methods=['GET'])
def logout():
    """
    用户退出登录
    清除会话中的用户信息，使当前会话失效

    返回值:
        JSON对象: 包含操作结果消息和HTTP状态码
        成功: {"message": "退出登录成功"}, 状态码 200
    """
    # 从会话中移除'user'键，清除登录状态
    session.pop('user', None)
    # 返回成功消息
    return jsonify({"message": "退出登录成功"}), 200


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """
    获取用户仪表盘信息
    返回当前登录用户的基本信息

    权限要求:
        用户必须已登录

    返回值:
        成功: 当前用户的JSON对象, 状态码 200
            示例: {"user_id": 1, "username": "testuser", "role": "user"}
        失败: 错误消息, 状态码 401 (未登录)
    """
    # 检查用户是否已登录
    if 'user' not in session:
        # 返回未登录错误
        return jsonify({"error": "未登录"}), 401

    # 返回会话中存储的用户信息
    return jsonify(session['user']), 200


@app.route('/change_password', methods=['POST'])
def change_password():
    """更改密码"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()
    old_pass = data.get('old_password')
    new_pass = data.get('new_password')

    if not all([old_pass, new_pass]):
        return jsonify({"error": "缺少必要参数"}), 400

    if len(new_pass) < 6:
        return jsonify({"error": "新密码至少6位"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 使用哈希密码比较
            hashed_old_pass = hash_password(old_pass)
            cursor.execute("""
                SELECT user_id FROM users 
                WHERE user_id = %s AND password = %s
            """, (session['user']['user_id'], hashed_old_pass))
            if not cursor.fetchone():
                return jsonify({"error": "原密码错误"}), 401

            # 使用哈希密码存储
            hashed_new_pass = hash_password(new_pass)
            cursor.execute("""
                UPDATE users SET password = %s 
                WHERE user_id = %s
            """, (hashed_new_pass, session['user']['user_id']))
            conn.commit()
            return jsonify({"message": "密码修改成功"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"修改失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups', methods=['GET'])
def list_subgroups():
    """查分组名称，返回用户名下所有分组名称"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT subgroup_name 
                FROM subgroup 
                WHERE username = %s
            """
            cursor.execute(query, (session['user']['username'],))
            subgroups = [row[0] for row in cursor.fetchall()]
            return jsonify({"subgroups": subgroups}), 200

    except Exception as e:
        return jsonify({"error": f"查询失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/copy', methods=['POST'])
def copy_subgroup():
    """
    复制分组及其所有配置

    请求体:
        {
            "source_subgroup_name": "原分组名称",
            "target_subgroup_name": "新分组名称"
        }

    返回值:
        成功: 201 状态码和成功消息
        失败: 相应的错误消息和状态码
    """
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()
    source_name = data.get('source_subgroup_name')
    target_name = data.get('target_subgroup_name')

    if not all([source_name, target_name]):
        return jsonify({"error": "缺少原分组名称或新分组名称"}), 400

    if source_name == target_name:
        return jsonify({"error": "新分组名称不能与原分组名称相同"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 验证原分组存在且属于当前用户
            cursor.execute("""
                SELECT subgroup_id 
                FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], source_name))
            if not cursor.fetchone():
                return jsonify({"error": "原分组不存在或不属于当前用户"}), 404

            # 2. 检查新分组名是否已存在
            cursor.execute("""
                SELECT subgroup_name 
                FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], target_name))
            if cursor.fetchone():
                return jsonify({"error": "新分组名称已存在"}), 409

            # 3. 创建新分组
            cursor.execute("""
                INSERT INTO subgroup (subgroup_name, username)
                VALUES (%s, %s)
            """, (target_name, session['user']['username']))

            # 4. 复制所有配置项
            cursor.execute("""
                INSERT INTO subgroup_config (
                    username, subgroup_name, brush_order, career, convert_career,
                    height, map, difficulty, today_task_completed, everyday_tasks,
                    leave_pl, brush_map_expire_time
                )
                SELECT 
                    username, %s, brush_order, career, convert_career,
                    height, map, difficulty, today_task_completed, everyday_tasks,
                    leave_pl, brush_map_expire_time
                FROM subgroup_config 
                WHERE username = %s AND subgroup_name = %s
            """, (target_name, session['user']['username'], source_name))

            conn.commit()
            return jsonify({
                "message": "分组复制成功",
                "source_subgroup": source_name,
                "target_subgroup": target_name,
                "copied_items": cursor.rowcount  # 返回复制的配置项数量
            }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"复制失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups', methods=['POST'])
def add_subgroup():
    """添加分组"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()
    subgroup_name = data.get('subgroup_name')

    if not subgroup_name:
        return jsonify({"error": "分组名称不能为空"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 先检查分组是否已存在
            cursor.execute("""
                SELECT subgroup_name FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], subgroup_name))
            if cursor.fetchone():
                return jsonify({"error": "分组已存在"}), 400

            # 插入新分组
            cursor.execute("""
                INSERT INTO subgroup (subgroup_name, username)
                VALUES (%s, %s)
            """, (subgroup_name, session['user']['username']))
            conn.commit()
            return jsonify({"message": "分组添加成功", "subgroup_name": subgroup_name}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"添加失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/<subgroup_name>/config', methods=['GET'])
def view_subgroup_config(subgroup_name):
    """查询指定名称的分组配置"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT * FROM subgroup_config 
                WHERE username = %s AND subgroup_name = %s
            """
            cursor.execute(query, (session['user']['username'], subgroup_name))
            configs = []
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                config = dict(zip(columns, row))
                config['brush_map_expire_time'] = config['brush_map_expire_time'].strftime("%Y-%m-%d %H:%M:%S")
                configs.append(config)
            return jsonify({"subgroup_name": subgroup_name, "configs": configs}), 200

    except Exception as e:
        return jsonify({"error": f"查询失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/<subgroup_name>/config', methods=['POST'])
def add_subgroup_config(subgroup_name):
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()
    required_fields = ['brush_order', 'career', 'convert_career', 'height', 'map', 'difficulty']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必要参数"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 验证用户是否拥有该分组
            cursor.execute("SELECT 1 FROM subgroup WHERE username = %s AND subgroup_name = %s", (session['user']['username'], subgroup_name))
            if not cursor.fetchone():
                return jsonify({"error": "分组不存在或不属于当前用户"}), 404

            # 2. 检查复合唯一约束 (username + subgroup_name + brush_order)
            cursor.execute("SELECT 1 FROM subgroup_config WHERE username = %s AND subgroup_name = %s AND brush_order = %s", (session['user']['username'], subgroup_name, data['brush_order']))
            if cursor.fetchone():
                return jsonify({"error": "当前用户在该分组中已存在相同刷图序号"}), 409

            # 3. 插入新配置
            query = """
                INSERT INTO subgroup_config (
                    username, subgroup_name, brush_order, career, convert_career,
                    height, map, difficulty, today_task_completed, everyday_tasks,
                    leave_pl, brush_map_expire_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (session['user']['username'], subgroup_name, data['brush_order'], data['career'], data['convert_career'], data['height'], data['map'], data['difficulty'], data.get('today_task_completed', '是'), data.get('everyday_tasks', '是'), data.get('leave_pl', 0), data.get('brush_map_expire_time', '2025-01-01 23:59:59'))
            cursor.execute(query, values)
            conn.commit()
            return jsonify({"message": "配置添加成功"}), 201

    except Exception as e:
        conn.rollback()
        # 兜底处理唯一约束冲突（如未提前检查到）
        if "unique_user_subgroup_brush" in str(e):
            return jsonify({"error": "当前用户在该分组中已存在相同刷图序号"}), 409
        return jsonify({"error": f"添加失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/admin/users', methods=['GET'])
def admin_users():
    """查询用户表"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "权限不足"}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM users"
            cursor.execute(query)
            users = []
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                user = dict(zip(columns, row))
                user['expire_time'] = user['expire_time'].strftime("%Y-%m-%d %H:%M:%S")
                users.append(user)
            return jsonify({"users": users}), 200

    except Exception as e:
        return jsonify({"error": f"查询失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/<subgroup_name>', methods=['DELETE'])
def delete_subgroup(subgroup_name):
    """删除分组及其所有配置"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证分组属于当前用户
            cursor.execute("""
                SELECT subgroup_id FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], subgroup_name))
            if not cursor.fetchone():
                return jsonify({"error": "分组不存在或不属于当前用户"}), 404

            # 删除分组（外键约束会自动删除关联的配置）
            cursor.execute("""
                DELETE FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], subgroup_name))

            conn.commit()
            return jsonify({"message": "分组删除成功", "deleted_subgroup": subgroup_name}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"删除失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/<old_subgroup_name>', methods=['PUT'])
def update_subgroup_name(old_subgroup_name):
    """修改分组名称"""
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()
    new_subgroup_name = data.get('new_subgroup_name')

    if not new_subgroup_name:
        return jsonify({"error": "新分组名称不能为空"}), 400

    if new_subgroup_name == old_subgroup_name:
        return jsonify({"error": "新分组名称与旧名称相同"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证旧分组属于当前用户
            cursor.execute("""
                SELECT subgroup_id FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], old_subgroup_name))
            if not cursor.fetchone():
                return jsonify({"error": "分组不存在或不属于当前用户"}), 404

            # 检查新分组名是否已存在
            cursor.execute("""
                SELECT subgroup_name FROM subgroup 
                WHERE username = %s AND subgroup_name = %s
            """, (session['user']['username'], new_subgroup_name))
            if cursor.fetchone():
                return jsonify({"error": "新分组名称已存在"}), 400

            # 开始事务
            conn.begin()

            # 更新分组名称
            cursor.execute("""
                UPDATE subgroup 
                SET subgroup_name = %s 
                WHERE username = %s AND subgroup_name = %s
            """, (new_subgroup_name, session['user']['username'], old_subgroup_name))

            # 更新分组配置中的分组名称
            cursor.execute("""
                UPDATE subgroup_config 
                SET subgroup_name = %s 
                WHERE username = %s AND subgroup_name = %s
            """, (new_subgroup_name, session['user']['username'], old_subgroup_name))

            conn.commit()
            return jsonify({"message": "分组名称修改成功", "old_name": old_subgroup_name, "new_name": new_subgroup_name}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"更新失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# ... 前面的代码保持不变 ...

@app.route('/subgroups/<subgroup_name>/config/<int:brush_order>', methods=['DELETE'])
def delete_subgroup_config(subgroup_name, brush_order):
    """
    删除指定分组中的配置项

    参数:
        subgroup_name: 分组名称
        brush_order: 刷图序号

    返回值:
        成功: 200 状态码和成功消息
        失败: 相应的错误消息和状态码
    """
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证配置项属于当前用户
            cursor.execute("""
                SELECT subgroup_config_id 
                FROM subgroup_config 
                WHERE username = %s 
                AND subgroup_name = %s 
                AND brush_order = %s
            """, (session['user']['username'], subgroup_name, brush_order))

            if not cursor.fetchone():
                return jsonify({"error": "配置项不存在或不属于当前用户"}), 404

            # 删除配置项
            cursor.execute("""
                DELETE FROM subgroup_config 
                WHERE username = %s 
                AND subgroup_name = %s 
                AND brush_order = %s
            """, (session['user']['username'], subgroup_name, brush_order))

            conn.commit()
            return jsonify({"message": "配置删除成功", "subgroup_name": subgroup_name, "brush_order": brush_order}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"删除失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/subgroups/<subgroup_name>/config/<int:brush_order>', methods=['PUT'])
def update_subgroup_config(subgroup_name, brush_order):
    """
    修改指定分组中的配置项

    参数:
        subgroup_name: 分组名称
        brush_order: 刷图序号

    返回值:
        成功: 200 状态码和成功消息
        失败: 相应的错误消息和状态码
    """
    if 'user' not in session:
        return jsonify({"error": "未登录"}), 401

    data = request.get_json()

    # 检查必填字段
    required_fields = ['career', 'convert_career', 'height', 'map', 'difficulty']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必要参数"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查新刷图序号是否已存在（如果提供了新的刷图序号）
            new_brush_order = data.get('brush_order', brush_order)
            if new_brush_order != brush_order:
                cursor.execute("""
                    SELECT 1 FROM subgroup_config 
                    WHERE username = %s 
                    AND subgroup_name = %s 
                    AND brush_order = %s
                """, (session['user']['username'], subgroup_name, new_brush_order))

                if cursor.fetchone():
                    return jsonify({"error": "新刷图序号在该分组中已存在", "new_brush_order": new_brush_order}), 409

            # 更新配置项
            update_query = """
                UPDATE subgroup_config 
                SET 
                    career = %s,
                    convert_career = %s,
                    height = %s,
                    map = %s,
                    difficulty = %s,
                    today_task_completed = %s,
                    everyday_tasks = %s,
                    leave_pl = %s,
                    brush_map_expire_time = %s,
                    brush_order = %s  -- 更新刷图序号
                WHERE 
                    username = %s 
                    AND subgroup_name = %s 
                    AND brush_order = %s
            """

            # 处理时间字段
            expire_time = data.get('brush_map_expire_time')
            if expire_time:
                try:
                    expire_time = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return jsonify({"error": "时间格式错误，应为 YYYY-MM-DD HH:MM:SS"}), 400

            cursor.execute(update_query, (data['career'], data['convert_career'], data['height'], data['map'], data['difficulty'], data.get('today_task_completed', '是'), data.get('everyday_tasks', '是'), data.get('leave_pl', 0), expire_time or '2025-01-01 23:59:59', new_brush_order,  # 新的刷图序号
                                          session['user']['username'], subgroup_name, brush_order  # 原刷图序号
                                          ))

            if cursor.rowcount == 0:
                return jsonify({"error": "配置项不存在或未修改"}), 404

            conn.commit()
            return jsonify({"message": "配置更新成功", "subgroup_name": subgroup_name, "original_brush_order": brush_order, "new_brush_order": new_brush_order}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"更新失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# ... 后面的代码保持不变 ...

# ========================
# 错误处理
# ========================

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "资源未找到"}), 404


@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "服务器内部错误"}), 500


@app.route('/test_db')
def test_db():
    start = time.time()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        # 创建游标对象
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("数据库连接测试成功:", result)
            else:
                print("数据库连接测试失败")
    except Exception as e:
        print(f"数据库测试错误: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"数据库错误: {str(e)}"}), 500
    finally:
        # 关闭连接
        if conn:
            conn.close()

    duration = time.time() - start
    return jsonify({"duration": duration}), 200




if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
