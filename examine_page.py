#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中药详情页面分析工具
"""

import requests
from bs4 import BeautifulSoup
import re
import chardet
import json

def get_page(url):
    """获取页面内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 尝试不同编码
        encodings = ['gb2312', 'gbk', 'gb18030', 'utf-8']
        content = None
        
        for encoding in encodings:
            try:
                content = response.content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            # 如果所有编码都失败，使用chardet检测
            detected_encoding = chardet.detect(response.content)
            if detected_encoding['encoding']:
                try:
                    content = response.content.decode(detected_encoding['encoding'])
                except UnicodeDecodeError:
                    # 如果依然失败，使用忽略错误的方式解码
                    content = response.content.decode('gb2312', errors='ignore')
            else:
                content = response.content.decode('gb2312', errors='ignore')
        
        return content
    except Exception as e:
        print(f"获取页面失败: {url}, 错误: {e}")
        return None

def clean_html_tags(text):
    """清理HTML标签和实体"""
    if not text:
        return ""
    # 使用BeautifulSoup清理HTML标签
    clean_text = BeautifulSoup(text, 'lxml').get_text()
    # 替换多个空白字符为单个空格
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip()

def analyze_herb_page(url, output_file):
    """分析药材详情页面结构并输出到文件"""
    html = get_page(url)
    if not html:
        print(f"无法获取页面内容: {url}")
        return
    
    # 保存完整HTML内容
    with open("full_page.html", 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"已将完整页面保存到 full_page.html")
    
    soup = BeautifulSoup(html, 'lxml')
    
    # 找出所有可能的主要内容区域，并打印它们的类名和ID
    all_divs = soup.find_all('div')
    print(f"\n找到 {len(all_divs)} 个div元素")
    main_content_candidates = []
    
    for i, div in enumerate(all_divs):
        class_str = ' '.join(div.get('class', []))
        id_str = div.get('id', '')
        text_length = len(div.get_text(strip=True))
        
        # 只考虑包含足够文本的div
        if text_length > 100:
            info = {
                'index': i,
                'class': class_str,
                'id': id_str,
                'text_length': text_length,
                'element': div
            }
            main_content_candidates.append(info)
            print(f"候选内容区域 #{i}: class='{class_str}', id='{id_str}', 文本长度={text_length}")
    
    # 查找主要内容区域
    content_div = None
    
    # 首先尝试使用class='text'
    content_div = soup.find('div', class_='text')
    if not content_div or len(content_div.get_text(strip=True)) < 200:
        # 如果未找到或内容太少，尝试使用class='content'
        content_div = soup.find('div', class_='content')
    
    # 如果依然未找到，使用文本最长的div
    if not content_div or len(content_div.get_text(strip=True)) < 200:
        if main_content_candidates:
            # 按文本长度排序
            main_content_candidates.sort(key=lambda x: x['text_length'], reverse=True)
            content_div = main_content_candidates[0]['element']
            print(f"使用文本最长的div作为主要内容区域: class='{main_content_candidates[0]['class']}', id='{main_content_candidates[0]['id']}'")
    
    if not content_div:
        print(f"未找到主要内容区域: {url}")
        return
    else:
        # 找到主要内容区域的类名和ID
        content_class = ' '.join(content_div.get('class', []))
        content_id = content_div.get('id', '')
        print(f"\n找到主要内容区域: class='{content_class}', id='{content_id}'")
    
    # 保存主要内容区域到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(content_div))
    
    print(f"已将主要内容保存到 {output_file}")
    
    # 提取所有文本段落，帮助识别结构
    paragraphs = content_div.find_all(['p', 'div'])
    print(f"\n找到 {len(paragraphs)} 个段落")
    
    # 查找所有可能的节标题
    section_titles = []
    for para in paragraphs:
        strong_tags = para.find_all('strong')
        for strong in strong_tags:
            title_text = strong.get_text(strip=True)
            if title_text and len(title_text) < 30:  # 标题通常较短
                section_titles.append(title_text)
    
    print("\n找到的可能节标题:")
    for i, title in enumerate(section_titles):
        print(f"{i+1}. {title}")
    
    # 查找所有可能的中药名和栏目名
    all_names = []
    herb_name_pattern = re.compile(r'【.*?】')
    for para in paragraphs:
        text = para.get_text(strip=True)
        matches = herb_name_pattern.findall(text)
        for match in matches:
            if match not in all_names:
                all_names.append(match)
    
    print("\n找到的栏目名:")
    for name in all_names:
        print(name)
    
    # 直接搜索原始HTML内容，不使用BeautifulSoup解析后的内容
    html_content = str(content_div)
    
    # 检查HTML结构
    print("\nHTML标签结构分析:")
    
    # 查找所有【<strong>...</strong>】格式的标题
    strong_titles = re.findall(r'【<strong>(.*?)</strong>】', html_content)
    print("\n【<strong>...</strong>】格式的标题:")
    for title in strong_titles:
        print(title)
    
    # 提取关键节点内容
    sections = {}
    
    # 使用找到的节标题构建正则表达式
    for title in strong_titles:
        pattern = f'【<strong>{title}</strong>】(.*?)(?:【<strong>|<div class="pagead">|$)'
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            content = match.group(1).strip()
            sections[title] = clean_html_tags(content)
    
    # 输出提取的内容
    print("\n提取的内容:")
    for title, content in sections.items():
        print(f"\n--- {title} ---")
        print(content[:200] + "..." if len(content) > 200 else content)
    
    # 保存提取的内容到JSON
    json_file = output_file.replace('.html', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    
    print(f"\n已将提取的内容保存到 {json_file}")

if __name__ == "__main__":
    # 分析乌蔹莓页面
    analyze_herb_page("http://www.zhongyoo.com/name/wulianmei_1022.html", "sample_page.html") 