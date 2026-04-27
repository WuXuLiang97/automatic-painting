# -*- coding: utf-8 -*-
import json

from flask import Flask, request, jsonify
from pymysql import Connection
from datetime import datetime

edition_dnf = None
information_dnf = None
min_edition_dnf = None
app = Flask(__name__)


@app.route('/Information_dnf', methods=['POST'])
def Information():
    global edition_dnf, information_dnf, min_edition_dnf
    current_time = datetime.now()
    data = request.get_json()
    post_id = data.get('id')
    post_f_program_version = data.get('f_program_version')
    post_state = data.get('state')
    # 解析版本
    post_edition = data.get('edition')
    # 解析版本
    post_min_edition = data.get('min_edition')
    # 解析更新信息
    post_information = data.get('information')

    print(post_id)
    # 更改版本
    if post_edition:
        edition_dnf = post_edition
        min_edition_dnf = int(post_min_edition)
        information_dnf = post_information
        print('版本更新成功')
        return jsonify({'edition': edition_dnf, 'result': '版本更新成功。', 'timestamp': current_time.isoformat(), 'information': information_dnf}), 200
    if post_id is None:
        print('未提供身份标识码')
        return jsonify({'result': '未提供身份标识码', "information": ""}), 400

    cnx = None
    cursor = None
    try:
        # 创建数据库连接
        cnx = Connection(
            host="127.0.0.1",
            user="root",
            password="Wxl111222",
            database="registration_codes"
        )
        # 创建一个游标对象 cursor
        cursor = cnx.cursor()

        # 定义要执行的SQL查询，并使用参数化查询防止SQL注入
        query = "SELECT * FROM registration_table_dnf WHERE id = %s"
        cursor.execute(query, (post_id,))

        # 获取所有匹配记录的第一条（假设ID是唯一的）
        row = cursor.fetchone()
        print(row)
        if row[3] == 1:
            # 假设time是第二个字段，使用索引1来获取它
            time_expiry = row[1]
            if time_expiry is None:
                print('很抱歉，我们暂时未能获取到所需的时间信息。请尽快联系我们的客服团队。')
                return jsonify({'result': '很抱歉，我们暂时未能获取到所需的时间信息。请尽快联系我们的客服团队。', "information": ""}), 400
            elif current_time < time_expiry:

                # 准备执行UPDATE语句
                update_query = "UPDATE registration_table_dnf SET `state` = %s, `start_time` = %s WHERE id = %s"
                # 请注意，这里`字段名`需要替换成您实际想要更新的字段的名称
                # 执行UPDATE语句，使用参数化查询防止SQL注入
                cursor.execute(update_query, (post_state, current_time, post_id))

                # 提交事务，确保更改被保存到数据库
                cnx.commit()
                # 检查版本
                if post_f_program_version == edition_dnf:
                    print(f"到期时间: {time_expiry}")
                    return jsonify({'result': f"到期时间: {time_expiry}", "information": ""}), 200
                elif int(post_f_program_version) < min_edition_dnf:
                    print(f"版本过旧！请您更新辅助后再使用")
                    return jsonify({'result': "版本过旧！请您更新辅助后再使用", "information": "", }), 400
                else:
                    response = jsonify({
                        'result': f"到期时间: {time_expiry}",
                        "information": f"{information_dnf}",
                    })
                    response.status_code = 201  # 设置状态码为 201
                    print(f"到期时间: {time_expiry}")
                    return response
            else:
                print('您的激活码已经过期，如需继续使用脚本，请联系客服续费。')
                return jsonify({'result': "您的激活码已经过期，如需继续使用脚本，请联系客服续费。", "information": ""}), 400
        else:
            print('您的id已被禁用，如需使用请联系客服解封')
            return jsonify({'result': '您的id已被禁用，如需使用请联系客服解封', "information": ""}), 404

    except Connection.Error as e:
        print("数据库异常:", e)
        print('数据库查询出错，请稍后再试或联系客服')
        return jsonify({'result': '数据库查询出错，请稍后再试或联系客服', "information": ""}), 500
    except Exception as e:
        print("异常:", e)
        print('服务器内部错误，请稍后再试或联系客服')
        return jsonify({'result': '服务器内部错误，请稍后再试或联系客服', "information": ""}), 500
    finally:
        # 关闭游标和连接
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
