import json
import re
import requests
from bs4 import BeautifulSoup
from itertools import zip_longest
from googletrans import Translator

def request_html(url):
    # print("正在请求: %s" % (url))
    response = requests.get(url)
    return response.text


def parse_attack_html(html):
    # 使用 BeautifulSoup库解析html，获取其中class名为"matrix side"的table
    soup = BeautifulSoup(html, "html.parser")
    matrix = soup.find("table", class_="matrix side")
    # 查找 `matrix` 中class名为 "tactic name"的td标签下的a标签中的文本
    tactics_names_ids = []
    for tactic_tag in matrix.find_all("td", class_="tactic name"):
        tactics_names_ids.append(
            {"id": tactic_tag.a.get("title").strip(), "name": tactic_tag.a.text}
        )
    # print(tactics_names)
    # print("tactics len: ")
    # print(len(tactics_names))

    # 查找 `matrix`中class="tactic"的td标签
    cols = []
    for col in matrix.find("tbody").find("tr").find_all("td", class_="tactic"):  # 一数列
        cols.append(col)

    tactic_techniques = []
    for col in cols:
        techniques = []
        for tech in col.find_all("tr", class_="technique-row"):
            # 获取tech中a标签的 "data-original-title"属性值
            a = tech.find("td").find("a")
            id = a.get("title").strip()
            name = re.sub(r"\(\d+\)", "", a.text).strip()
            sub = []
            for sub_items in tech.find("td", class_="subtechniques-td").find_all(
                "div", class_="subtechnique"
            ):
                sub.append(
                    {
                        "id": sub_items.find("a").get("title").strip(),
                        "name": sub_items.find("a").text.strip(),
                    }
                )
            technique = {"id": id, "name": name, "subs": sub}
            techniques.append(technique)
        tactic_techniques.append(techniques)

    return (tactics_names_ids, tactic_techniques)


def build_attack_res(tactics_names, tactic_techniques):
    res = []
    for tactic, technique in zip_longest(
        tactics_names, tactic_techniques, fillvalue=""
    ):
        # print(tactic.id)
        res.append(
            {"id": tactic.get("id"), "name": tactic.get("name"), "technique": technique}
        )
    return res


def debug_print(res):
    # 输出
    for r in res:
        print("title: %s" % r["title"])
        print("sub title: %s" % r["sub"])
        print("item len: %d" % len(r["items"]))
        for i, item in enumerate(r["items"]):
            print("#################### %d ####################" % (i + 1))
            print("id: %s" % item["id"])
            print("title: %s" % item["title"])
            print("sub: %s" % item["sub"])


# 翻译attack
def translate_attack(res):
    # 将res中的值翻译成中文
    translator = Translator()
    for r in res:
        r["title"] = translator.translate(r["title"], dest="zh-CN").text
        r["sub"] = translator.translate(r["sub"], dest="zh-CN").text
        for i, item in enumerate(r["items"]):
            item["title"] = translator.translate(item["title"], dest="zh-CN").text
            for i, s in enumerate(item["sub"]):
                item["sub"][i] = translator.translate(s, dest="zh-CN").text
    return res

# 翻译详情
def translate_description(data):
    # 将res中的值翻译成中文
    translator = Translator()
    for technique_descriptions in data:
        for description in technique_descriptions["description"]:
            if isinstance(description["content"], list):
                for i, li in enumerate(description["content"]):
                    description["content"][i] = translator.translate(li, dest="zh-CN").text
            else:
                description["content"] = translator.translate(description["content"], dest="zh-CN").text

    return data


def save_to_file(file_name, data):
    # 保存为json文件
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def parse_tactic_description_html(html):
    soup = BeautifulSoup(html, "html.parser")
    description_body = soup.find("div", class_="description-body")
    # 找到 description_body 下的所有直接子标签
    tactic_description = []
    for child in description_body.children:
        if child.name == "p":
            tactic_description.append({ "type": "text", "content": child.text })
        if child.name == "ul":
            lis = []
            for li in child.children:
               lis.append(li.text)
            tactic_description.append({ "type": "list", "content": lis })
    return tactic_description


def parse_technique_description_html(html, mitigation: bool = False):
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    # 描述
    description_body = soup.find("div", class_="description-body")
    children = description_body.children
    technique_description_list = []
    for child in children:
        if child.name == "p":
            item_list = []
            p_content = ""
            p_type = "" # "code" | "text"
            for item in child:
                if isinstance(item, str):
                    p_type = "text"
                    p_content += item
                elif item.name == "code":
                    if p_type == "text":
                        item_list.append({ "type": "text", "content": p_content })
                    p_type = "code"
                    p_content = ""
                    item_list.append({ "type": "code", "content": item.text })
                else:
                    p_type = "text"
                    p_content += re.sub(r"\[\d+\]", "", item.text ).strip()
            if p_type == "text" and p_content != "":
                item_list.append({ "type": "text", "content": p_content })
            technique_description_list.append(item_list)
        elif child.name == "ul":
            lis = child.find_all("li")
            item_list = []
            for li in lis:
                item_list.append({ "type": "li", "content": re.sub(r"\[\d+\]", "", li.text ).strip() })
            technique_description_list.append(item_list)
    data["description"] = technique_description_list

    # 缓解措施
    if mitigation:
        mitigations = []
        mitigation_tag = soup.find("h2", id="mitigations").find_next_siblings()[0]
        if mitigation_tag.name == "div":
            mitigation_trs = mitigation_tag.find("tbody").find_all("tr")
            for tr in mitigation_trs:
                tds = tr.find_all("td")
                if len(tds) == 3:
                    description = []
                    for p in tds[2]:
                        item_list = []
                        p_content = ""
                        p_type = "" # "code" | "text"
                        for item in p:
                            if isinstance(item, str):
                                p_type = "text"
                                p_content += re.sub(r"\n", "", item)
                            elif item.name == "code":
                                if p_type == "text":
                                    item_list.append({ "type": "text", "content": p_content })
                                p_type = "code"
                                p_content = ""
                                item_list.append({ "type": "code", "content": item.text })
                            else:
                                p_type = "text"
                                pre1 = re.sub(r"\[\d+\]", "", item.text )
                                pre2 = re.sub(r"\n", "", pre1)
                                p_content += pre2
                        if p_type == "text" and p_content != "":
                            item_list.append({ "type": "text", "content": p_content })
                        if len(item_list):
                            description.append(item_list)
                    mitigations.append({ 
                        "id": tds[0].text.strip(), 
                        "name": tds[1].text.strip(), 
                        "description": description
                    })
        elif mitigation_tag.name == "p":
            mitigations.append({ "type": "text", "content": re.sub(r"\s+", ' ', mitigation_tag.text.strip()) })
        data["mitigations"] = mitigations

    return data


def parse_sub_technique_description_html(html, mitigation: bool = False):
    soup = BeautifulSoup(html, "html.parser")
    # 描述
    description_body = soup.find("div", class_="description-body")
    ps = description_body.find_all("p")
    sub_technique_description_list = []
    for p in ps:
        sub_technique_description_list.append({ "type": "text", "content": re.sub(r"\[\d+\]", "", p.text.strip()) })
    
    return sub_technique_description_list


#! 调用1: 获取ATT&CK框架
def get_attack_framwork(translate: bool = False, save: bool = False):
    url = "https://attack.mitre.org/"
    html_str = request_html(url)
    (tactics_names_ids, tactic_techniques) = parse_attack_html(html_str)
    res = build_attack_res(tactics_names_ids, tactic_techniques)
    
    if translate: 
        res = translate(res)
    if save:
        save_to_file("attack.json", res)

    tactic_ids = []
    for id_name in res:
        tactic_ids.append(id_name["id"])
    
    technique_ids = []
    sub_technique_ids = []
    for tactic_technique in tactic_techniques:
        for technique in tactic_technique:
            technique_ids.append(technique["id"])
            for sub_technique in technique["subs"]:
                sub_technique_ids.append(sub_technique["id"])

    return (tactic_ids, technique_ids, sub_technique_ids)

#! 调用2: 获取tactic描述
def get_tactic_description(tactic_ids: list, save: bool = False, translate: bool = False):
    list_len = len(tactic_ids)
    print("正在抓取 `%d` 个阶段" % (list_len))
    data = []
    console_msg = ""
    for index, tactic_id in enumerate(tactic_ids):
        url = "https://attack.mitre.org/tactics/" + tactic_id
        console_msg = f"阶段详情抓取中: {url} [{index+1:>3}/{list_len}]"
        print(console_msg, end='\r')
        tactic_html = request_html(url)
        tactic_description = parse_tactic_description_html(tactic_html)
        data.append({ "id": tactic_id, "description": tactic_description })
    print(console_msg)
    print("`%d` 个阶段, 抓取完成" % (list_len))
    if save:
        print("正在保存...")
        save_to_file("tactic_description-en.json", data)
    if translate:
        print("正在翻译...")
        data = translate_description(data)
        save_to_file("tactic_description-zh.json", data)


#! 调用3: 获取technique描述
def get_technique_description(technique_ids: list, mitigation: bool = False, save: bool = False, translate: bool = False):
    list_len = len(technique_ids)
    print("正在抓取 `%d` 个技术" % (list_len))
    data = []
    console_msg = ""
    for index, technique_id in enumerate(technique_ids):
        url = "https://attack.mitre.org/techniques/" + technique_id
        console_msg = f"技术详情抓取中: {url} [{index+1:>3}/{list_len}]"
        print(console_msg, end='\r')
        technique_html = request_html(url)
        parse_data = parse_technique_description_html(technique_html, mitigation)
        if mitigation:
            data.append({ "id": technique_id, "description": parse_data["description"], "mitigations": parse_data["mitigations"] })
        else:
            data.append({ "id": technique_id, "description": parse_data["description"] })
    print(console_msg)
    print("`%d` 个技术, 抓取完成!" % (list_len))
    if save:
        print("正在保存...")
        save_to_file("technique_description-en.json", data)
    if translate:
        print("正在翻译...")
        data = translate_description(data)
        save_to_file("technique_description-zh.json", data)


#! 调用4: 获取sub-technique描述
def get_sub_technique_description(sub_technique_ids: list, mitigation: bool = False, save: bool = False, translate: bool = False):
    list_len = len(sub_technique_ids)
    print("正在抓取 `%d` 个子技术" % (list_len))
    data = []
    console_msg = ""
    data = []
    for index, sub_technique_id in enumerate(sub_technique_ids):
        id = sub_technique_id.replace('.', '/')
        url = "https://attack.mitre.org/techniques/" + id
        console_msg = f"子技术详情抓取中: {url} [{index+1:>3}/{list_len}]"
        print(console_msg, end='\r')
        sub_technique_html = request_html(url)
        sub_technique_description = parse_sub_technique_description_html(sub_technique_html)
        data.append({ "id": sub_technique_id, "description": sub_technique_description })
    print(console_msg)
    print("`%d` 个技术, 抓取完成!" % (list_len))
    if save:
        print("正在保存...")
        save_to_file("sub_technique_description-en.json", data)
    if translate:
        print("正在翻译...")
        data = translate_description(data)
        save_to_file("sub_technique_description-zh.json", data)


if __name__ == "__main__":
    (tactic_ids, technique_ids, sub_technique_ids) = get_attack_framwork(translate=False, save=True)
    print("阶段: `%d` 个, 技术: `%d` 个, 子技术: `%d` 个" % (len(tactic_ids), len(technique_ids), len(sub_technique_ids)))
    # get_tactic_description(tactic_ids, save=True, translate=True)
    
    # technique_ids = ["T1556", "T1608", "T1137", "T1547", "T1574"]
    # technique_ids = ["T1608"]
    get_technique_description(technique_ids, mitigation=True, save=True, translate=False)
    # get_sub_technique_description(sub_technique_ids, mitigation=True, save=True, translate=True)
