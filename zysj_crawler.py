#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中药学爬虫脚本 - 中医世家网站版本
作者: Claude
功能: 爬取中医世家网站(zysj.com.cn)的中药材数据
网站结构:
1. 索引页面: https://www.zysj.com.cn/lilunshuji/zhongyaoxue/index.html
2. 药材详情页面: https://www.zysj.com.cn/lilunshuji/zhongyaoxue/{id}.html

生成的JSON数据字段说明:
- name: 药材名称，如"黄芪"、"人参"等
- category: 药材分类，如"补虚药"、"解表药"等
- url: 药材详情页URL
- medicinal_part: 药用部位，指药材入药使用的部分
- taste_meridian: 性味归经，描述药材的性质(寒热温凉)、味道及归属经络
- effects: 功效，描述药材的主要治疗作用
- clinical_application: 临床应用，描述具体临床使用场景和适应症
- prescription_name: 处方用名，药材在处方中的正式名称
- usage_dosage: 用法用量，描述使用方法和剂量
- notes: 按语，解释药材使用的注意事项或补充说明
- formulas: 方剂举例，包含此药的经典方剂
- literature: 文献摘录，古代医学文献中关于此药材的记载
- affiliated_herbs: 附药，与主药相关的其他药材或变种
- images: 图片链接，药材相关图片的URL
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import logging
import os
import chardet
import shutil
from datetime import datetime
from urllib.parse import urljoin
from fake_useragent import UserAgent
from retrying import retry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zysj_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ZYSJHerbalCrawler:
    def __init__(self):
        self.base_url = "https://www.zysj.com.cn"
        self.index_url = "https://www.zysj.com.cn/lilunshuji/zhongyaoxue/index.html"
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.herbal_data = []
        # 爬取间隔设置 (秒)
        self.request_interval = (2, 4)
        self.default_filename = "zysj_herbal_data.json"
        
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=3000)
    def get_page(self, url):
        """获取页面内容，包含重试机制和编码检测"""
        try:
            # 每次请求前更新User-Agent
            self.session.headers.update({
                'User-Agent': self.ua.random,
            })
            
            response = self.session.get(url, timeout=10)
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
            
            # 随机等待，避免请求过于频繁
            sleep_time = max(1, min(self.request_interval))
            time.sleep(sleep_time)
            
            return content
            
        except Exception as e:
            logging.error(f"获取页面失败: {url}, 错误: {e}")
            raise
    
    def parse_index_page(self):
        """解析索引页面，提取中药分类和药材链接"""
        logging.info(f"正在解析索引页面: {self.index_url}")
        
        try:
            html = self.get_page(self.index_url)
            soup = BeautifulSoup(html, 'lxml')
            
            herbs_data = []
            
            # 寻找主要的目录结构 - 通常是一个含有多个 li 的 ul 列表
            # 尝试找到所有可能包含药材列表的 ul 元素
            ul_elements = soup.find_all('ul')
            main_ul = None
            
            # 根据 li 数量找到最可能是主目录的 ul
            for ul in ul_elements:
                li_count = len(ul.find_all('li', recursive=False))
                if li_count > 10:  # 假设主目录至少有10个条目
                    main_ul = ul
                    break
            
            if main_ul:
                # 基于 ul-li 结构进行解析
                logging.info("使用 ul-li 结构解析药材分类和详情")
                
                # 遍历顶级 li 元素 (通常是章节)
                for chapter_li in main_ul.find_all('li', recursive=False):
                    # 提取章节信息
                    chapter_title = None
                    chapter_links = chapter_li.find_all('a')
                    
                    for a in chapter_links:
                        text = a.text.strip()
                        href = a.get('href', '')
                        
                        # 寻找章节标题，通常包含"章"字
                        chapter_match = re.search(r'第(.+?)章\s+(.+?)(?=\s|$)', text)
                        if chapter_match:
                            chapter_title = chapter_match.group(2).strip()
                            logging.info(f"找到分类: {chapter_title}")
                            break
                    
                    if not chapter_title:
                        # 如果没有找到明确的章节标题，尝试其他方式提取
                        text = chapter_li.text.strip()
                        chapter_match = re.search(r'第(.+?)章\s+(.+?)(?=\s|$)', text)
                        if chapter_match:
                            chapter_title = chapter_match.group(2).strip()
                            logging.info(f"找到分类: {chapter_title}")
                    
                    # 检查此章节是否有子分类 (通常是嵌套的 ul-li 结构)
                    sub_ul = chapter_li.find('ul')
                    if sub_ul:
                        # 有子分类，遍历每个子分类
                        for section_li in sub_ul.find_all('li', recursive=False):
                            section_title = None
                            section_links = section_li.find_all('a')
                            
                            for a in section_links:
                                text = a.text.strip()
                                href = a.get('href', '')
                                
                                # 寻找节标题，通常包含"节"字
                                section_match = re.search(r'第(.+?)节\s+(.+?)(?=\s|$)', text)
                                if section_match:
                                    section_title = section_match.group(2).strip()
                                    logging.info(f"找到子分类: {section_title}")
                                    break
                            
                            if not section_title:
                                # 如果没有找到明确的节标题，尝试其他方式提取
                                text = section_li.text.strip()
                                section_match = re.search(r'第(.+?)节\s+(.+?)(?=\s|$)', text)
                                if section_match:
                                    section_title = section_match.group(2).strip()
                                    logging.info(f"找到子分类: {section_title}")
                            
                            # 提取该节下的所有药材
                            # 可能直接在 section_li 下，也可能在嵌套的 ul-li 结构中
                            herb_links = []
                            
                            # 直接查找该节下的链接
                            for a in section_li.find_all('a'):
                                # 跳过节标题链接
                                if section_title and section_title in a.text:
                                    continue
                                herb_links.append(a)
                            
                            # 查找嵌套的 ul-li 结构中的链接
                            herbs_ul = section_li.find('ul')
                            if herbs_ul:
                                for herb_li in herbs_ul.find_all('li'):
                                    for a in herb_li.find_all('a'):
                                        herb_links.append(a)
                            
                            # 处理所有找到的药材链接
                            for a in herb_links:
                                href = a.get('href', '')
                                herb_name = a.text.strip()
                                
                                # 检查是否是药材链接
                                if (re.search(r'/\d+\.html$', href) or ('zhongyaoxue' in href and href.endswith('.html'))) and herb_name:
                                    # 跳过章节标题，只提取实际药材
                                    if re.search(r'第(.+?)([章节])', herb_name) or '应用注意事项' in herb_name or '其它' in herb_name:
                                        continue
                                    
                                    # 跳过一些常见的非药材内容
                                    if re.search(r'(概述|分类|简介|总论|前言|附录|索引|目录|凡例|方剂|制剂|炮制|附方|附表)', herb_name):
                                        continue
                                        
                                    # 检查药材名称的合理性（通常中药名比较短）
                                    if len(herb_name) > 10:
                                        continue
                                    
                                    herb_url = urljoin(self.base_url, href)
                                    
                                    # 确保名称有效且有分类信息
                                    if herb_name and len(herb_name) > 1 and (section_title or chapter_title):
                                        effective_category = section_title if section_title else chapter_title
                                        herbs_data.append({
                                            'name': herb_name,
                                            'url': herb_url,
                                            'category': effective_category,
                                            'subcategory': None
                                        })
                                        logging.info(f"找到药材: {herb_name}, 分类: {effective_category}, URL: {herb_url}")
                    else:
                        # 没有子分类，直接提取章节下的药材
                        herb_links = []
                        
                        # 查找该章节下的直接链接
                        for a in chapter_li.find_all('a'):
                            # 跳过章节标题链接
                            if chapter_title and chapter_title in a.text:
                                continue
                            herb_links.append(a)
                        
                        # 处理所有找到的药材链接
                        for a in herb_links:
                            href = a.get('href', '')
                            herb_name = a.text.strip()
                            
                            # 检查是否是药材链接
                            if (re.search(r'/\d+\.html$', href) or ('zhongyaoxue' in href and href.endswith('.html'))) and herb_name:
                                # 跳过章节标题，只提取实际药材
                                if re.search(r'第(.+?)([章节])', herb_name) or '应用注意事项' in herb_name or '其它' in herb_name:
                                    continue
                                
                                # 跳过一些常见的非药材内容
                                if re.search(r'(概述|分类|简介|总论|前言|附录|索引|目录|凡例|方剂|制剂|炮制|附方|附表)', herb_name):
                                    continue
                                    
                                # 检查药材名称的合理性（通常中药名比较短）
                                if len(herb_name) > 10:
                                    continue
                                
                                herb_url = urljoin(self.base_url, href)
                                
                                # 确保名称有效且有分类信息
                                if herb_name and len(herb_name) > 1 and chapter_title:
                                    herbs_data.append({
                                        'name': herb_name,
                                        'url': herb_url,
                                        'category': chapter_title,
                                        'subcategory': None
                                    })
                                    logging.info(f"找到药材: {herb_name}, 分类: {chapter_title}, URL: {herb_url}")
            
            # 如果前面的方法未找到足够的药材，尝试使用更直接的方法
            if len(herbs_data) < 10:
                logging.info("使用直接解析方法查找药材...")
                
                # 尝试直接查找所有药材链接元素
                for li in soup.find_all('li', {'class': 'catalog_group'}):
                    # 查找分类信息 - 通常在同一个 li 或相邻元素中
                    category = None
                    
                    # 在当前 li 中查找分类信息
                    links = li.find_all('a')
                    if len(links) >= 2:
                        # 如果有多个链接，第二个通常是分类链接
                        category_link = links[1]
                        category_match = re.search(r'title="(.+?)"', str(category_link))
                        if category_match:
                            category = category_match.group(1)
                    
                    # 如果没找到分类，尝试从 li 的父元素或 id 中提取
                    if not category:
                        li_id = li.get('id', '')
                        li_class = li.get('class', [])
                        if 'catalog_group' in li_class and li.parent:
                            # 尝试从父元素中找
                            parent_text = li.parent.get_text()
                            for pattern in [r'第(.+?)章\s+(.+?)(?=\s|$)', r'第(.+?)节\s+(.+?)(?=\s|$)']:
                                match = re.search(pattern, parent_text)
                                if match:
                                    category = match.group(2).strip()
                                    break
                    
                    # 提取药材名称和链接
                    herb_link = links[0] if links else None
                    if herb_link:
                        href = herb_link.get('href', '')
                        title_match = re.search(r'title="(.+?)"', str(herb_link))
                        
                        if title_match:
                            herb_name = title_match.group(1)
                            
                            # 检查是否是药材链接
                            if herb_name and (re.search(r'/\d+\.html$', href) or ('zhongyaoxue' in href and href.endswith('.html'))):
                                # 各种过滤条件
                                if (not re.search(r'第(.+?)([章节])', herb_name) and 
                                    '应用注意事项' not in herb_name and 
                                    '其它' not in herb_name and
                                    not re.search(r'(概述|分类|简介|总论|前言|附录|索引|目录|凡例|方剂|制剂|炮制|附方|附表)', herb_name) and
                                    len(herb_name) <= 10):
                                    
                                    herb_url = urljoin(self.base_url, href)
                                    
                                    # 如果没有找到分类，使用默认分类
                                    if not category:
                                        category = "未分类药材"
                                    
                                    herbs_data.append({
                                        'name': herb_name,
                                        'url': herb_url,
                                        'category': category,
                                        'subcategory': None
                                    })
                                    logging.info(f"使用直接解析找到药材: {herb_name}, 分类: {category}, URL: {herb_url}")
            
            # 移除可能的重复药材
            unique_herbs = []
            seen_names = set()
            
            for herb in herbs_data:
                # 对药材名称进行简单清理
                clean_name = re.sub(r'[\s\*\(\)（）\[\]【】]', '', herb['name'])
                
                # 检查是否是常见的非药材内容（如页码、索引等）
                if re.match(r'^\d+$', clean_name) or len(clean_name) <= 1:
                    logging.info(f"跳过无效药材名: {herb['name']}")
                    continue
                
                # 检查是否存在重复
                if clean_name not in seen_names:
                    seen_names.add(clean_name)
                    unique_herbs.append(herb)
                else:
                    logging.info(f"跳过重复药材: {herb['name']}")
            
            logging.info(f"共找到 {len(unique_herbs)} 个药材")
            return unique_herbs
        
        except Exception as e:
            logging.error(f"解析索引页面失败: {e}")
            return []
    
    def parse_herb_detail(self, herb_data):
        """解析药材详情页面"""
        url = herb_data['url']
        logging.info(f"正在解析药材详情: {herb_data['name']}, URL: {url}")
        
        try:
            html = self.get_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            # 获取主要内容区域 - 尝试多种可能的选择器
            content_div = soup.find('div', class_='content')
            if not content_div:
                content_div = soup.find('div', class_='article')
            if not content_div:
                content_div = soup.find('div', id='content')
            if not content_div:
                # 如果仍找不到，尝试用body作为内容区域
                content_div = soup.body
            
            if not content_div:
                logging.warning(f"无法找到内容区域: {url}")
                return None
                
            # 提取页面内容进行验证
            content_text = content_div.get_text()
            
            # 验证页面是否可能是一个药材页面
            # 检查是否包含药材相关的关键词
            herb_indicators = ['性味', '归经', '功效', '主治', '用法', '用量', '药用', '入药', '中药']
            indicator_count = sum(1 for indicator in herb_indicators if indicator in content_text)
            
            # 如果关键词出现次数太少，可能不是药材页面
            if indicator_count < 2:
                logging.warning(f"页面似乎不是药材页面 (关键词匹配: {indicator_count}): {url}")
                # 尝试查找是否有明确的错误提示
                if '找不到' in content_text or '不存在' in content_text or '已删除' in content_text:
                    logging.error(f"页面明确表示内容不存在: {url}")
                    return None
            
            # 初始化数据结构
            herb_detail = {
                "name": herb_data['name'],          # 药材名称
                "category": herb_data['category'],  # 药材分类，如"补虚药"等
                "url": url,                         # 药材详情页URL
                "medicinal_part": "",               # 药用部位，如"干燥根"等
                "taste_meridian": "",               # 性味归经，如"甘温，归肺、脾经"
                "effects": "",                      # 功效，如"补气升阳，固表止汗"
                "clinical_application": [],         # 临床应用，具体临床使用场景
                "prescription_name": "",            # 处方用名，如"炙黄芪"等
                "usage_dosage": "",                 # 用法用量，如"煎服，9-30g"
                "notes": [],                        # 按语，使用注意事项
                "formulas": [],                     # 方剂举例，包含此药的经典方剂
                "literature": [],                   # 文献摘录，古代医学文献中关于此药材的记载
                "affiliated_herbs": [],             # 附药，与主药相关的药材
                "images": []                        # 药材图片URL
            }
            
            # 使用基于HTML标签的解析方式提取所有内容
            # 当前解析状态
            current_section = None
            last_section_title = None
            
            # 查找所有段落标签和标题标签
            all_elements = content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for element in all_elements:
                element_text = element.get_text(strip=True)
                
                # 跳过空段落
                if not element_text:
                    continue
                
                # 检查是否是新的节标题
                is_title = False
                section_key = None
                
                # 查找匹配的部分标题
                title_patterns = {
                    "medicinal_part": [r"【药用】", r"【药用部位】", r"药用[：:]"],
                    "taste_meridian": [r"【性味与归经】", r"【性味归经】", r"性味[与]?归经[：:]"],
                    "effects": [r"【功效】", r"功效[：:]"],
                    "clinical_application": [r"【临床应用】", r"临床应用[：:]", r"应用[：:]"],
                    "prescription_name": [r"【处方用名】", r"处方用名[：:]"],
                    "usage_dosage": [r"【一般用量与用法】", r"【用法用量】", r"用法[与]?用量[：:]"],
                    "notes": [r"【按语】", r"按语[：:]"],
                    "formulas": [r"【方剂举例】", r"方剂举例[：:]"],
                    "literature": [r"【文献摘录】", r"文献摘录[：:]"],
                    "affiliated_herbs": [r"【附药】", r"附药[：:]"]
                }
                
                for key, patterns in title_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, element_text):
                            is_title = True
                            section_key = key
                            # 提取标题后的内容
                            match = re.search(f"{pattern}(.*)", element_text)
                            if match and match.group(1).strip():
                                content = match.group(1).strip()
                                # 处理直接在标题行后的内容
                                if key in ["medicinal_part", "taste_meridian", "effects", "prescription_name", "usage_dosage"]:
                                    herb_detail[key] = content
                                elif key in ["clinical_application", "notes", "formulas", "literature", "affiliated_herbs"]:
                                    herb_detail[key].append(content)
                            current_section = key
                            last_section_title = element_text
                            break
                    if is_title:
                        break
                
                # 如果不是标题，而是内容的一部分
                if not is_title and current_section:
                    # 排除不需要的内容
                    if (re.search(r'^各论$|^第.+?[章节]|^[一二三四五六七八九十]+、', element_text) or 
                        element_text == last_section_title):
                        continue
                    
                    # 根据当前节处理内容
                    if current_section in ["medicinal_part", "taste_meridian", "effects", "prescription_name", "usage_dosage"]:
                        # 对于这些单值字段，如果还是空的，则设置；否则追加内容
                        if not herb_detail[current_section]:
                            herb_detail[current_section] = element_text
                        else:
                            herb_detail[current_section] += "\n" + element_text
                    elif current_section in ["clinical_application", "notes", "formulas", "literature", "affiliated_herbs"]:
                        # 对于列表字段，直接添加到列表中
                        herb_detail[current_section].append(element_text)
            
            # 对列表字段进行处理，解析可能的序号格式
            for field in ["clinical_application", "notes", "affiliated_herbs"]:
                if herb_detail[field]:
                    # 检查是否有序号分割的内容
                    numbered_items = []
                    non_numbered_items = []
                    
                    for item in herb_detail[field]:
                        # 检查是否以序号开头
                        if re.match(r'^\s*(?:\d+\.|[一二三四五六七八九十]+、|\(\d+\)|\d+）)', item):
                            # 这是一个序号项，可能包含多个序号
                            subitems = re.findall(r'(?:^|\n)\s*(?:\d+\.|[一二三四五六七八九十]+、|\(\d+\)|\d+）).*?(?=(?:\n\s*(?:\d+\.|[一二三四五六七八九十]+、|\(\d+\)|\d+）))|$)', item, re.DOTALL)
                            if subitems:
                                numbered_items.extend([subitem.strip() for subitem in subitems])
                            else:
                                numbered_items.append(item.strip())
                        else:
                            # 非序号项
                            non_numbered_items.append(item.strip())
                    
                    # 如果有序号项，优先使用
                    if numbered_items:
                        herb_detail[field] = numbered_items
                    else:
                        # 检查是否有以逗号分隔的列表（特别是对于附药）
                        if field == "affiliated_herbs" and len(non_numbered_items) == 1:
                            # 薄荷案例表明不应该额外截断内容，因此直接保留完整内容
                            # 只有在明确需要分割的情况下才进行分割
                            text = non_numbered_items[0]
                            if "，" in text and not re.search(r'。|；', text):  # 只有当内容中包含逗号且没有句号或分号时才分割
                                comma_items = [i.strip() for i in text.split('，') if i.strip()]
                                if len(comma_items) > 1:
                                    herb_detail[field] = comma_items
                                else:
                                    herb_detail[field] = non_numbered_items
                            else:
                                herb_detail[field] = non_numbered_items
                        else:
                            herb_detail[field] = non_numbered_items
            
            # 特殊处理方剂举例和文献摘录
            for field in ["formulas", "literature"]:
                # 清理并合并相关段落
                cleaned_items = []
                current_item = ""
                
                for item in herb_detail[field]:
                    item = item.strip()
                    
                    # 跳过无效内容
                    if not item or re.search(r'^各论$|^第.+?[章节]', item):
                        continue
                    
                    # 检查是否是新条目的开始（通常以方名或文献名开始）
                    if (field == "formulas" and re.match(r'^[【\[（(].+?[】\]）)][：:]', item)) or \
                       (field == "literature" and re.match(r'^[《【\[].+?[》】\]][：:]', item)):
                        # 保存之前的条目
                        if current_item:
                            cleaned_items.append(current_item)
                        current_item = item
                    else:
                        # 追加到当前条目
                        if current_item:
                            current_item += "\n" + item
                        else:
                            current_item = item
                
                # 添加最后一个条目
                if current_item:
                    cleaned_items.append(current_item)
                
                herb_detail[field] = cleaned_items
            
            # 提取图片
            for img in content_div.find_all('img'):
                img_url = img.get('src')
                if img_url:
                    full_img_url = urljoin(self.base_url, img_url)
                    herb_detail["images"].append(full_img_url)
            
            # 药材解析完成后，打印详细日志
            self.log_herb_detail(herb_detail)
            
            return herb_detail
            
        except Exception as e:
            logging.error(f"解析药材详情失败: {url}, 错误: {e}")
            return None
    
    def log_herb_detail(self, herb_detail):
        """详细打印药材解析结果"""
        if not herb_detail:
            return
            
        logging.info(f"成功解析药材: {herb_detail['name']} ({herb_detail['category']})")
        logging.info(f"  - 药用部位: {herb_detail['medicinal_part'][:30]}{'...' if len(herb_detail['medicinal_part']) > 30 else ''}")
        logging.info(f"  - 性味归经: {herb_detail['taste_meridian'][:30]}{'...' if len(herb_detail['taste_meridian']) > 30 else ''}")
        logging.info(f"  - 功效: {herb_detail['effects'][:30]}{'...' if len(herb_detail['effects']) > 30 else ''}")
        logging.info(f"  - 临床应用: {len(herb_detail['clinical_application'])} 条")
        logging.info(f"  - 处方用名: {herb_detail['prescription_name']}")
        logging.info(f"  - 用法用量: {herb_detail['usage_dosage']}")
        logging.info(f"  - 按语: {len(herb_detail['notes'])} 条")
        logging.info(f"  - 方剂举例: {len(herb_detail['formulas'])} 条")
        logging.info(f"  - 文献摘录: {len(herb_detail['literature'])} 条")
        logging.info(f"  - 附药: {len(herb_detail['affiliated_herbs'])} 条")
        logging.info(f"  - 图片: {len(herb_detail['images'])} 张")
    
    def backup_json_file(self, filename):
        """备份JSON文件"""
        if not os.path.exists(filename):
            logging.info(f"无需备份，文件不存在: {filename}")
            return
            
        # 创建备份文件名: 原文件名_YYYYMMDD_HHMMSS.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.json"
        
        try:
            shutil.copy2(filename, backup_filename)
            logging.info(f"已备份文件: {filename} -> {backup_filename}")
        except Exception as e:
            logging.error(f"备份文件失败: {e}")
    
    def crawl_all_herbs(self):
        """爬取所有药材信息"""
        # 打印字段说明
        self.print_field_description()
        
        # 先备份JSON文件，然后清空数据
        self.backup_json_file(self.default_filename)
        # 清空数据列表
        self.herbal_data = []
        # 写入空数据，确保文件存在且为空列表
        self.save_data()
        
        herbs_data = self.parse_index_page()
        total_herbs = len(herbs_data)
        
        success_count = 0
        fail_count = 0
        
        for i, herb_data in enumerate(herbs_data, 1):
            try:
                logging.info(f"正在处理 [{i}/{total_herbs}] {herb_data['name']} ({herb_data['category']})")
                
                herb_detail = self.parse_herb_detail(herb_data)
                if herb_detail:
                    # 检查爬取的数据是否有效
                    valid_data = False
                    for key in ["medicinal_part", "taste_meridian", "effects"]:
                        if herb_detail[key]:
                            valid_data = True
                            break
                    
                    if valid_data:
                        self.herbal_data.append(herb_detail)
                        success_count += 1
                        logging.info(f"成功添加药材: {herb_detail['name']}")
                    else:
                        logging.warning(f"药材 {herb_data['name']} 未获取到有效内容，跳过")
                        fail_count += 1
                else:
                    logging.warning(f"药材 {herb_data['name']} 解析失败，跳过")
                    fail_count += 1
                
                # 每爬取一个药材就保存一次数据
                if success_count % 5 == 0:  # 每成功爬取5个才保存一次，减少IO操作
                    self.save_data()
                
            except Exception as e:
                logging.error(f"处理药材 {herb_data['name']} 时发生错误: {e}")
                fail_count += 1
                # 发生错误后仍保存已爬取数据
                self.save_data()
            
            # 随机等待，避免请求过于频繁
            sleep_time = max(1, min(self.request_interval))
            time.sleep(sleep_time)
        
        # 最后保存一次数据
        self.save_data()
        
        logging.info(f"爬取完成，共成功爬取 {success_count} 个药材，失败 {fail_count} 个，总共 {total_herbs} 个")
    
    def print_field_description(self):
        """打印数据字段含义说明"""
        field_descriptions = {
            "name": "药材名称，如'黄芪'、'人参'等",
            "category": "药材分类，如'补虚药'、'解表药'等",
            "url": "药材详情页URL",
            "medicinal_part": "药用部位，指药材入药使用的部分",
            "taste_meridian": "性味归经，描述药材的性质(寒热温凉)、味道及归属经络",
            "effects": "功效，描述药材的主要治疗作用",
            "clinical_application": "临床应用，描述具体临床使用场景和适应症",
            "prescription_name": "处方用名，药材在处方中的正式名称",
            "usage_dosage": "用法用量，描述使用方法和剂量",
            "notes": "按语，解释药材使用的注意事项或补充说明",
            "formulas": "方剂举例，常见包含此药材的方剂",
            "literature": "文献摘录，古代医学文献中关于此药材的记载",
            "affiliated_herbs": "附药，与主药相关的其他药材或变种",
            "images": "图片链接，药材相关图片的URL"
        }
        
        print("\n" + "="*80)
        print("中药学爬虫 - 数据字段说明:")
        print("="*80)
        for field, desc in field_descriptions.items():
            print(f"{field:20s}: {desc}")
        print("="*80 + "\n")
    
    def save_data(self, filename=None):
        """保存爬取的数据到JSON文件"""
        if filename is None:
            filename = self.default_filename
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.herbal_data, f, ensure_ascii=False, indent=2)
            logging.info(f"数据已保存到 {filename}，当前共 {len(self.herbal_data)} 条记录")
        except Exception as e:
            logging.error(f"保存数据失败: {e}")

def main():
    crawler = ZYSJHerbalCrawler()
    crawler.crawl_all_herbs()

if __name__ == "__main__":
    main() 