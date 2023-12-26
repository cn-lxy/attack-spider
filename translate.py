from hashlib import md5
import json
import random
import re
from time import sleep
import requests


# Generate salt and sign
def make_md5(s, encoding='utf-8'):
    return md5(s.encode(encoding)).hexdigest()

def baidu_fanyi(src):
    print(f"正在翻译: {src}")
    appid = '20210427000804843' 
    appkey = 'F1PSEmTGZQ_dcoUDh6ro'

    from_lang = 'en'
    to_lang =  'zh'

    endpoint = 'http://api.fanyi.baidu.com'
    path = '/api/trans/vip/translate'
    url = endpoint + path

    query = src

    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query + str(salt) + appkey)

    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

    # Send request
    r = requests.post(url, params=payload, headers=headers)
    result = r.json()

    dst = ""
    try:
        dst = result["trans_result"][0]["dst"]
        print(f"翻译结果: {dst}")
    except:
        dst = src
        print(json.dumps(result, indent=4, ensure_ascii=False))

    sleep(1)
    return dst

def translate_description(techniques):
    for technique in techniques:
        translate_desc = []
        for desc in technique["description"]:
            # list 类型直接翻译
            if desc[0]["type"] == "li":
                temp = []
                for li in desc:
                    res = baidu_fanyi(li["content"])
                    temp.append({ "type": "list", "content": res })
                translate_desc.append(temp)
            # code 和 text类型拼接成一段翻译后在拆分
            else:
                para = ""
                for item in desc:
                    if item["type"] == "text":
                        para += item["content"]
                    elif item["type"] == "code":
                        para += "<code>" + item["content"] + "</code>"
                # translate_para = translator.translate(para, dest='zh-CN').text
                translate_para = baidu_fanyi(para)
                '''
                    abcd ```A``` asdasda
                    ["abcd ", "A", " asdasda"]
                '''
                # 将translate_para根据符合正则表达式进行分割
                translate_para = re.split(r"(<code>.*?</code>)", translate_para)
                # 重新保存
                temp = []
                for item in translate_para:
                    # 判断item字符串是否符合正则表达式
                    if re.match(r"<code>.*?</code>", item):
                        temp.append({"type": "code", "content": item.replace("<code>", "").replace("</code>", "")})
                    else:
                        temp.append({"type": "text", "content": item})
                translate_desc.append(temp)
        technique["description"] = translate_desc

    # 将techniques保存为 `technique_description-zh.json`
    with open("technique_description-zh.json", "w", encoding="utf-8") as f:
        json.dump(techniques, f, ensure_ascii=False, indent=4)
    print("technique_description-zh.json 保存成功")

def translate_mitigation(techniques):
    """
    翻译 mitigation
    """
    # 翻译 mitigation
    for technique in techniques:
        for mitigation in technique["mitigations"]:
            translate_name = baidu_fanyi(mitigation["name"])
            translate_desc = []
            for desc in mitigation["description"]:
                para = ""
                for item in desc:
                    if item["type"] == "text":
                        para += item["content"]
                    elif item["type"] == "code":
                        para += "<code>" + item["content"] + "</code>"
                # translate_para = translator.translate(para, dest='zh-CN').text
                translate_para = baidu_fanyi(para)
                # 将translate_para根据符合正则表达式进行分割
                translate_para = re.split(r"(<code>.*?</code>)", translate_para)
                # 重新保存
                temp = []
                for item in translate_para:
                    # 判断item字符串是否符合正则表达式
                    if re.match(r"<code>.*?</code>", item):
                        temp.append({"type": "code", "content": item.replace("<code>", "").replace("</code>", "")})
                    else:
                        temp.append({"type": "text", "content": item})
                translate_desc.append(temp)   
            mitigation["name"] = translate_name
            mitigation["description"] = translate_desc
    
    # 将techniques保存为 `technique_description-zh.json`
    with open("technique_description-zh.json", "w", encoding="utf-8") as f:
        json.dump(techniques, f, ensure_ascii=False, indent=4)
    print("technique_description-zh.json 保存成功")

if __name__ == "__main__":
    # 读取 `technique_description-en.json`
    with open("technique_description-en.json", "r", encoding="utf-8") as f:
        techniques = json.load(f)
        # 翻译
        translate_description(techniques)
        translate_mitigation(techniques)
