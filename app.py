#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书美妆个护选品库 - 后端服务
功能：调用 DeepSeek API 搜索热门产品，支持选品去重（已选产品不会二次出现）
"""

import json
import os
import re
import threading
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ─── 路径配置 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SELECTED_FILE = os.path.join(DATA_DIR, 'selected_products.json')

os.makedirs(DATA_DIR, exist_ok=True)

# ─── DeepSeek API 配置 ───
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"

# 文件读写锁（防止并发写入冲突）
_file_lock = threading.Lock()


# ─── 数据持久化 ───

def load_selected_products():
    """读取已选产品列表"""
    try:
        with open(SELECTED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_selected_product(product):
    """追加一条已选产品记录"""
    with _file_lock:
        products = load_selected_products()
        product['confirmed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        products.append(product)
        with open(SELECTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
    return product


def clear_selected_products():
    """清空已选产品记录"""
    with _file_lock:
        with open(SELECTED_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)


# ─── DeepSeek API 调用 ───

def get_season():
    """根据月份返回季节描述"""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "春季（防晒、抗敏、轻薄底妆需求旺盛）"
    elif month in (6, 7, 8):
        return "夏季（控油、防晒、清爽补水、晒后修复需求旺盛）"
    elif month in (9, 10, 11):
        return "秋季（保湿修复、抗老、滋润底妆需求旺盛）"
    else:
        return "冬季（深层滋润、抗冻疮、唇部护理需求旺盛）"


def build_prompt(selected_names):
    """构建发送给 DeepSeek 的选品 prompt"""
    today = datetime.now().strftime('%Y年%m月%d日')
    season = get_season()
    exclude_text = '\n'.join(
        f'  {i+1}. {name}' for i, name in enumerate(selected_names)
    ) if selected_names else '  （暂无已选产品）'

    system_prompt = (
        "你是一位资深的小红书美妆个护选品顾问，拥有10年+电商选品经验，"
        "精通小红书种草逻辑、用户画像分析和美妆市场趋势。"
        "你熟悉各品牌产品线、成分功效、价格定位和用户口碑。"
    )

    user_prompt = f"""今天是{today}，当前季节：{season}。

任务：请根据最近3天的小红书美妆个护市场热度趋势，搜索并推荐3个最适合在小红书平台带货的美妆个护产品。

选品标准（按重要性排序）：
1. 退货率低（预估 < 20%），优先选择标品或功效明确的产品
2. 复购率高（预估 > 50%），适合长期带货
3. 种草内容潜力大，适合图文/视频笔记，有话题性
4. 具有差异化卖点，非同质化产品
5. 价格区间适合小红书用户消费力（50-500元为主，可包含少量高端线）
6. 符合当季消费需求
7. 品牌有一定知名度或口碑，避免三无产品

以下产品已经被选定过，请勿再次推荐（避免重复带货）：
{exclude_text}

请确保3个产品来自不同的细分品类，覆盖不同价格带和不同目标人群。

请严格按以下JSON格式返回（只返回JSON，不要任何其他文字）：
{{
  "products": [
    {{
      "name": "品牌+产品全名",
      "brand": "品牌名",
      "category": "细分品类（如：精华、面膜、口红、洁面、防晒等）",
      "price_range": "XX-XX元",
      "selling_points": ["核心卖点1", "核心卖点2", "核心卖点3"],
      "target_audience": "目标人群描述（年龄段+肤质/需求）",
      "xhs_angle": "小红书种草内容方向（建议笔记选题和拍摄角度）",
      "return_rate": "约XX%",
      "repurchase_rate": "约XX%",
      "trend_reason": "近期热度上升原因（结合季节/节日/热点）",
      "reason": "综合推荐理由（50-100字，说明为什么选这个产品）"
    }}
  ]
}}"""

    return system_prompt, user_prompt


def extract_json(content):
    """从模型返回文本中稳健提取 JSON 产品列表"""
    # 1. 直接解析
    try:
        data = json.loads(content)
        return _extract_products_from_data(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 从 markdown 代码块提取
    code_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
    if code_match:
        try:
            data = json.loads(code_match.group(1))
            return _extract_products_from_data(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 从文本中提取 JSON 对象
    obj_match = re.search(r'\{.*\}', content, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group())
            return _extract_products_from_data(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # 4. 从文本中提取 JSON 数组
    arr_match = re.search(r'\[.*\]', content, re.DOTALL)
    if arr_match:
        try:
            data = json.loads(arr_match.group())
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(f"无法解析AI返回的JSON数据，原始内容前500字符: {content[:500]}")


def _extract_products_from_data(data):
    """从解析后的 JSON 数据中提取产品列表"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('products', 'data', 'items', 'results', 'recommendations'):
            if key in data and isinstance(data[key], list):
                return data[key]
        # 可能是单个产品对象
        if 'name' in data:
            return [data]
    raise ValueError("JSON数据中未找到产品列表")


def search_products_via_ai(api_key, model=None):
    """调用 DeepSeek API 搜索推荐3个产品"""
    if not api_key:
        raise ValueError("请先在设置页面填写 DeepSeek API Key")

    selected = load_selected_products()
    selected_names = [p.get('name', '') for p in selected]

    system_prompt, user_prompt = build_prompt(selected_names)
    use_model = model or DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": use_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 3000,
    }

    resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=90)
    resp.raise_for_status()
    result = resp.json()

    content = result['choices'][0]['message']['content']
    products = extract_json(content)

    # 二次过滤：确保不包含已选产品（按名称模糊匹配）
    selected_lower = [name.lower().strip() for name in selected_names]
    filtered = []
    for p in products:
        pname = p.get('name', '').lower().strip()
        if not any(sname in pname or pname in sname for sname in selected_lower if sname):
            filtered.append(p)

    # 最多返回3个
    return filtered[:3]


# ─── 路由 ───

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索推荐产品"""
    try:
        api_key = request.headers.get('X-API-Key', '').strip()
        model = request.headers.get('X-Model', '').strip() or None
        products = search_products_via_ai(api_key, model)
        if not products:
            return jsonify({
                'success': False,
                'error': 'AI未能返回有效的产品推荐，请稍后重试。'
            }), 200
        return jsonify({'success': True, 'products': products})
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'AI请求超时，请稍后重试。'}), 200
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': '无法连接AI服务，请检查网络。'}), 200
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else '未知'
        return jsonify({
            'success': False,
            'error': f'AI服务返回错误（HTTP {status_code}），请检查API Key和模型名称是否正确。'
        }), 200
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'搜索失败：{str(e)}'}), 200


@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    """确认选定一个产品"""
    try:
        product = request.get_json()
        if not product or 'name' not in product:
            return jsonify({'success': False, 'error': '产品数据不完整'}), 400
        saved = save_selected_product(product)
        return jsonify({'success': True, 'product': saved})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def api_history():
    """获取已选产品历史"""
    return jsonify({'success': True, 'products': load_selected_products()})


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """清空已选产品历史"""
    try:
        clear_selected_products()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("  小红书美妆个护选品库")
    print("  访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
