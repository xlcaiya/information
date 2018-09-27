import random, re

from flask import request, abort, current_app, make_response, Response, jsonify
from info import sr
from info.lib.yuntongxun.sms import CCP
from info.modules.passport import passport_blu
from info.unils.captcha.pic_captcha import captcha
from info.unils.response_code import RET, error_map


@passport_blu.route('/get_img_code')
def get_img_code():
    # 获取参数
    img_code_id = request.args.get('img_code_id')

    # 校验参数
    if not img_code_id:
        return abort(403)

    # 生成图片验证码
    img_name, img_text, img_bytes = captcha.generate_captcha()

    # 保存图片key和验证码文字 redis 方便设置过期时间
    try:
        # 创建redis连接
        # sr = StrictRedis(host=config_class.REDIS_HOST, port=config_class.REDIS_PORT)
        # mg_code_id session 设置 img 的 id
        # img_text 返回随机字符串
        # ex 设置session180秒有效期
        sr.set('img_code_id' + img_code_id, img_text, ex=180)
    except BaseException as e:
        current_app.logger.error(e)
        # 500, 服务器错误
        return abort(500)

    # 返回验证码图片
    response = make_response(img_bytes)  # type: Response
    response.content_type = 'image/jpeg'
    return response


# 获取短信验证码
@passport_blu.route('/get_sms_code', methods=['POST'])
def get_sms_code():
    # 获取参数
    mobile = request.json.get('mobile')  # 手机号
    img_code = request.json.get('img_code')  # 图片验证码
    img_code_id = request.json.get('img_code_id')  # 图片key

    # 校验参数
    if not all([mobile, img_code, img_code_id]):
        return jsonify(error=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])
    pass

    # 校验手机号格式
    if not re.match(r'^1[345678]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])

    # 根据图片key取出验证码文字
    try:
        real_img_code = sr.get('img_code_id' + img_code_id)
    except BaseException as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg=error_map[RET.DBERR])

    # 验证码是否过期
    if not real_img_code:
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])

    # 校验验证码
    if real_img_code != img_code.upper():  # 不一致
        return jsonify(errno=RET.PARAMERR, errmsg='验证码错误')

    # 生成随机短信验证码
    sms_code = "%04d" % random.randint(0, 9999)
    current_app.logger.info('短信验证码为: %s' % sms_code)
    # 发送短信
    # 注意： 测试的短信模板编号为1
    # response_code = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    # if response_code != 0:
    #     return jsonify(errno=RET.THIRDERR, errmsg=error_map[RET.THIRDERR])

    # 保存短信验证码
    try:
        sr.set('sms_code_id' + mobile, sms_code, ex=60)
    except BaseException as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmag=error_map[RET.DBERR])

    # json返回发送结果
    return jsonify(errno=RET.OK, errmsg=error_map[RET.OK])
