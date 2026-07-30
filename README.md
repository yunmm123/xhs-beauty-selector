# 小红书美妆个护选品库

AI 智能选品工具，自动搜索近期热门美妆个护产品，推荐 3 个最佳选品，并自动去重避免重复带货。

## 功能特点

- **AI 智能选品**：调用 DeepSeek API，根据近期市场热度推荐 3 个最适合小红书带货的产品
- **自动去重**：已选定的产品不会再被推荐，有效避免重复带货
- **前端配置 API Key**：在网页设置页面直接填写 API Key，无需后端环境变量，Key 仅保存在浏览器本地
- **选品历史**：记录所有已选产品，支持查看和清空
- **数据看板**：展示累计选品数、今日选品数等统计信息

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python3 app.py
```

或使用启动脚本：

```bash
bash start.sh
```

### 3. 配置 API Key

1. 打开浏览器访问 `http://localhost:5000`
2. 点击右上角 **⚙️** 设置按钮
3. 在 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 创建 API Key
4. 将 API Key 粘贴到设置页面并保存

> API Key 仅保存在浏览器的 localStorage 中，不会上传到服务器。

### 4. 开始选品

点击「开始选品」按钮，AI 将自动搜索并推荐 3 个产品，选定后该产品不会再重复出现。

## 技术栈

- **后端**：Python + Flask
- **前端**：HTML + CSS + JavaScript（原生，无框架）
- **AI**：DeepSeek API（deepseek-v4-flash）
- **数据存储**：JSON 文件（本地持久化）

## 项目结构

```
xiaohongshu-selector/
├── app.py                 # 后端主程序
├── requirements.txt       # Python 依赖
├── start.sh              # 启动脚本
├── .gitignore
├── data/
│   └── selected_products.json  # 选品记录（自动生成）
└── templates/
    └── index.html        # 前端页面
```

## 选品标准

1. 退货率低（预估 < 20%）
2. 复购率高（预估 > 50%）
3. 种草内容潜力大
4. 具有差异化卖点
5. 价格适合小红书用户消费力（50-500 元为主）
6. 符合当季消费需求
7. 品牌有知名度或口碑
