from PIL import Image
import pytesseract


def recognize_verify_code(image_path, broker='ht'):
    """识别验证码，返回识别后的字符串，使用 tesseract 实现
    :param image_path: 图片路径
    :param broker: 券商 ['ht', 'yjb', 'gf', 'yh']
    :return recognized: verify code string"""

    if broker == 'yh_client':
        return detect_yh_client_result(image_path)

    # 调用 tesseract 识别
    return default_verify_code_detect(image_path)

def detect_yh_client_result(image_path):
    """封装了tesseract的识别，部署在阿里云上，服务端源码地址为： https://github.com/shidenggui/yh_verify_code_docker"""
    
    image = Image.open(image_path)
    code = pytesseract.image_to_string(image, config='-psm 7')
    return code.replace(' ', '')
