#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中药材数据爬取脚本 - 中医药网版本
作者: AI Assistant
功能: 爬取中医药网(zhongyoo.com)的中药材数据
网站结构:
1. 功效分类页面: http://www.zhongyoo.com/gx/
2. 分类药材列表: http://www.zhongyoo.com/gx/{category}/
3. 药材详情页面: http://www.zhongyoo.com/name/{name}_{id}.html
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from fake_useragent import UserAgent
from retrying import retry
import os
from urllib.parse import urljoin, urlparse
import logging
import chardet

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zhongyoo_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ZhongYooHerbalCrawler:
    def __init__(self):
        self.base_url = "http://www.zhongyoo.com"
        self.category_url = "http://www.zhongyoo.com/gx/"
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.herbal_data = []
        self.current_id = 1
        self.categories = []
        
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=3000)
    def get_page(self, url):
        """获取页面内容，包含重试机制和编码检测"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # 直接从bytes解码，按优先级尝试编码
            content_bytes = response.content
            
            # 网站检测到使用GBK/GB2312编码，优先尝试
            encodings_to_try = ['gbk', 'gb2312', 'gb18030', 'utf-8']
            
            for encoding in encodings_to_try:
                try:
                    decoded_text = content_bytes.decode(encoding)
                    # 检查是否包含有效的中文字符
                    if self._is_valid_chinese_text(decoded_text):
                        return decoded_text
                except UnicodeDecodeError:
                    continue
            
            # 如果都失败了，使用chardet检测
            detected_encoding = chardet.detect(content_bytes)
            if detected_encoding['encoding'] and detected_encoding['confidence'] > 0.5:
                try:
                    return content_bytes.decode(detected_encoding['encoding'])
                except:
                    pass
            
            # 最后的兜底方案
            return content_bytes.decode('gbk', errors='ignore')
            
        except Exception as e:
            logging.error(f"获取页面失败: {url}, 错误: {e}")
            raise
    
    def _is_valid_chinese_text(self, text):
        """检查文本是否包含有效的中文字符"""
        # 检查是否包含中文字符
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        has_chinese = chinese_pattern.search(text)
        
        # 检查是否包含明显的乱码字符
        garbled_pattern = re.compile(r'[?]{3,}')
        has_garbled = garbled_pattern.search(text)
        
        return has_chinese and not has_garbled
    
    def parse_category_page(self):
        """解析功效分类页面，获取所有药材分类"""
        logging.info(f"正在爬取分类页面: {self.category_url}")
        
        try:
            html = self.get_page(self.category_url)
            soup = BeautifulSoup(html, 'lxml')
            
            categories = []
            
            # 查找所有分类链接
            # 根据网站结构，寻找指向分类页面的链接
            category_links = soup.find_all('a', href=re.compile(r'/gx/[^/]+/$'))
            
            for link in category_links:
                category_name = link.get_text(strip=True)
                category_url = urljoin(self.base_url, link.get('href'))
                
                if category_name and category_name not in ['首页', '更多']:
                    categories.append({
                        'name': category_name,
                        'url': category_url
                    })
            
            # 如果没有找到链接，尝试其他选择器
            if not categories:
                # 尝试查找包含分类信息的其他元素
                potential_links = soup.find_all('a')
                for link in potential_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/gx/' in href and href.endswith('/') and len(text) > 1 and len(text) < 10:
                        category_url = urljoin(self.base_url, href)
                        if category_url not in [cat['url'] for cat in categories]:
                            categories.append({
                                'name': text,
                                'url': category_url
                            })
            
            self.categories = categories
            logging.info(f"找到 {len(categories)} 个药材分类")
            
            for category in categories[:5]:  # 显示前5个分类作为示例
                logging.info(f"分类: {category['name']} - {category['url']}")
            
            return categories
            
        except Exception as e:
            logging.error(f"解析分类页面失败: {e}")
            return []
    
    def parse_category_list_page(self, category):
        """解析某个分类下的药材列表页面"""
        category_name = category['name']
        category_url = category['url']
        
        logging.info(f"正在爬取分类 '{category_name}' 的药材列表: {category_url}")
        
        try:
            html = self.get_page(category_url)
            soup = BeautifulSoup(html, 'lxml')
            
            herbal_items = []
            
            # 查找药材链接
            # 根据网站结构，寻找指向药材详情页面的链接
            herbal_links = soup.find_all('a', href=re.compile(r'/name/[^/]+\.html'))
            
            for link in herbal_links:
                herb_name = link.get_text(strip=True)
                herb_url = urljoin(self.base_url, link.get('href'))
                
                if herb_name and len(herb_name) > 0:
                    herbal_items.append({
                        'name': herb_name,
                        'url': herb_url,
                        'category': category_name
                    })
            
            # 如果没有找到，尝试其他方式
            if not herbal_items:
                # 查找所有可能的链接
                all_links = soup.find_all('a')
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/name/' in href and '.html' in href and text:
                        herb_url = urljoin(self.base_url, href)
                        herbal_items.append({
                            'name': text,
                            'url': herb_url,
                            'category': category_name
                        })
            
            logging.info(f"在分类 '{category_name}' 中找到 {len(herbal_items)} 个药材")
            return herbal_items
            
        except Exception as e:
            logging.error(f"解析分类 '{category_name}' 列表页面失败: {e}")
            return []
    
    def parse_herb_detail_page(self, herb_item):
        """解析药材详情页面"""
        name = herb_item['name']
        url = herb_item['url']
        category = herb_item.get('category', '')
        
        logging.info(f"正在爬取药材 '{name}' 的详细信息: {url}")
        
        try:
            html = self.get_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            # 初始化数据结构
            herbal_data = {
                "id": self.current_id,
                "name": name,
                "pinyin": "",
                "category": category,
                "properties": "",
                "taste": "",
                "meridians": [],
                "functions": [],
                "indications": [],
                "dosage": "",
                "commonPairings": [],
                "contraindications": "",
                "description": "",
                "images": [],
                "source_url": url
            }
            
            # 获取页面文本用于解析
            page_text = soup.get_text()
            
            # 提取各种信息
            self.extract_basic_info(herbal_data, page_text, soup)
            self.extract_effects_info(herbal_data, page_text, soup)
            self.extract_usage_info(herbal_data, page_text, soup)
            self.extract_cautions_info(herbal_data, page_text, soup)
            self.extract_description(herbal_data, page_text, soup)
            
            # 提取图片
            herbal_data['images'] = self.extract_images(soup, url)
            
            self.current_id += 1
            
            # 延时避免请求过快
            time.sleep(1)
            
            return herbal_data
            
        except Exception as e:
            logging.error(f"解析药材 '{name}' 详情页面失败: {e}")
            return None
    
    def extract_basic_info(self, herbal_data, page_text, soup):
        """提取基本信息：拼音、性味、归经等"""
        try:
            # 清理文本，去除多余空白
            cleaned_text = re.sub(r'\s+', ' ', page_text)
            
            # 提取拼音
            pinyin_patterns = [
                r'【中药名】.*?\s+([a-z\s]+)',
                r'拼音[：:\s]*([a-z\s]+)',
                r'【拼音】[：:\s]*([a-z\s]+)',
            ]
            
            for pattern in pinyin_patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE)
                if match:
                    pinyin = match.group(1).strip()
                    if len(pinyin) < 50 and re.match(r'^[a-z\s]+$', pinyin, re.IGNORECASE):
                        herbal_data['pinyin'] = pinyin
                        break
            
            # 提取性味归经（完整字段用于后续分析）
            taste_meridian_patterns = [
                r'【性味归经】([^【]+)',
                r'性味归经[：:\s]*([^【]+)',
            ]
            
            taste_meridian_text = ""
            for pattern in taste_meridian_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    taste_meridian_text = match.group(1).strip()
                    if len(taste_meridian_text) < 200:
                        break
            
            # 分离提取性味和归经
            self.extract_taste_and_meridians(herbal_data, taste_meridian_text, cleaned_text)
                    
        except Exception as e:
            logging.warning(f"提取基本信息失败: {e}")

    def extract_taste_and_meridians(self, herbal_data, taste_meridian_text, cleaned_text):
        """分离提取性味和归经信息"""
        try:
            # 首先尝试从性味归经字段中提取完整的性味信息
            if taste_meridian_text:
                # 提取完整的性味描述
                taste_match = re.search(r'([味性][甘苦辛咸酸涩寒热温凉平微]+[，、\s]*[性味][甘苦辛咸酸涩寒热温凉平微]*|味[甘苦辛咸酸涩]+[，、\s]*性[寒热温凉平微]+|性[寒热温凉平微]+[，、\s]*味[甘苦辛咸酸涩]+)', taste_meridian_text)
                
                if taste_match:
                    herbal_data['taste'] = taste_match.group(1).strip()
                else:
                    # 如果没有匹配到完整格式，尝试单独匹配
                    taste_parts = []
                    wei_match = re.search(r'味([甘苦辛咸酸涩]+)', taste_meridian_text)
                    if wei_match:
                        taste_parts.append(f"味{wei_match.group(1)}")
                    
                    xing_match = re.search(r'性([寒热温凉平微]+)', taste_meridian_text)
                    if xing_match:
                        taste_parts.append(f"性{xing_match.group(1)}")
                    
                    if taste_parts:
                        herbal_data['taste'] = "，".join(taste_parts)
                
                # 从性味归经字段中提取归经
                meridians = re.findall(r'[肺心肝脾肾胃肠膀胱胆]经', taste_meridian_text)
                if meridians:
                    herbal_data['meridians'] = list(set(meridians))
            
            # 如果性味归经字段没有提供完整信息，尝试其他位置
            if not herbal_data['taste']:
                # 单独查找性味
                taste_only_patterns = [
                    r'【性味】([^【]+)',
                    r'性味[：:\s]*([^【]+)',
                ]
                
                for pattern in taste_only_patterns:
                    match = re.search(pattern, cleaned_text)
                    if match:
                        taste_text = match.group(1).strip()
                        if len(taste_text) < 100:
                            herbal_data['taste'] = taste_text
                            break
            
            if not herbal_data['meridians']:
                # 单独查找归经
                meridian_patterns = [
                    r'【归经】([^【]+)',
                    r'归经[：:\s]*([^【]+)',
                    r'归([肺心肝脾肾胃肠膀胱胆经、，\s]+)',
                    r'入([肺心肝脾肾胃肠膀胱胆经、，\s]+)',
                ]
                
                for pattern in meridian_patterns:
                    match = re.search(pattern, cleaned_text)
                    if match:
                        meridians_text = match.group(1)
                        meridians = re.findall(r'[肺心肝脾肾胃肠膀胱胆]经', meridians_text)
                        if meridians:
                            herbal_data['meridians'] = list(set(meridians))
                            break
                    
        except Exception as e:
            logging.warning(f"分离性味归经失败: {e}")

    def extract_effects_info(self, herbal_data, page_text, soup):
        """提取功效和主治信息"""
        try:
            cleaned_text = re.sub(r'\s+', ' ', page_text)
            
            # 提取功效与作用
            function_patterns = [
                r'【功效与作用】([^【]+)',
                r'功效与作用[：:\s]*([^【]+)',
                r'功效[：:\s]*([^【]+)',
            ]
            
            for pattern in function_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    functions_text = match.group(1).strip()
                    if len(functions_text) < 300:  # 避免获取过长文本
                        # 清理无关的分类描述
                        functions_text = self.clean_functions_text(functions_text)
                        # 分割功效
                        functions = re.split(r'[，、；;]', functions_text)
                        # 清理每个功效项，去除末尾的句号和空白字符
                        herbal_data['functions'] = [f.strip().rstrip('。') for f in functions if f.strip() and len(f.strip()) < 50 and not self.is_classification_text(f.strip())]
                        break
            
            # 提取主治（排除用量信息）
            indication_patterns = [
                r'【主治】([^【]+)',
                r'主治[：:\s]*([^【]+)',
                r'【临床应用】([^【]+)',
            ]
            
            for pattern in indication_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    indications_text = match.group(1).strip()
                    if len(indications_text) < 300:
                        # 提取用量信息到dosage字段
                        dosage_info = self.extract_dosage_from_indications(indications_text)
                        if dosage_info and not herbal_data['dosage']:
                            herbal_data['dosage'] = dosage_info
                        
                        # 清理主治信息，移除用量相关内容
                        clean_indications_text = self.clean_indications_text(indications_text)
                        
                        # 分割主治
                        indications = re.split(r'[，、；;]', clean_indications_text)
                        # 清理每个主治项，去除末尾的句号和空白字符
                        herbal_data['indications'] = [i.strip().rstrip('。') for i in indications if i.strip() and len(i.strip()) < 50 and not self.is_dosage_text(i.strip())]
                        break
            
            # 提取更细化的分类信息
            self.extract_detailed_category(herbal_data, cleaned_text)
            
            # 提取配伍药方信息
            self.extract_common_pairings(herbal_data, cleaned_text)
                    
        except Exception as e:
            logging.warning(f"提取功效信息失败: {e}")

    def clean_functions_text(self, text):
        """清理功效文本中的无关信息"""
        # 移除分类描述
        patterns_to_remove = [
            r'属.*?药下属分类的.*?药[。，、\s]*',
            r'属.*?药[。，、\s]*',
            r'下属分类的.*?药[。，、\s]*',
        ]
        
        cleaned_text = text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text)
        
        return cleaned_text.strip()

    def is_classification_text(self, text):
        """判断是否为分类描述文本"""
        classification_keywords = ['属', '下属分类', '分类']
        return any(keyword in text for keyword in classification_keywords)

    def extract_dosage_from_indications(self, text):
        """从主治文本中提取用量信息"""
        dosage_patterns = [
            r'用量(\d+[-~～]\d+[克g])[，、\s]*([^。]+)',
            r'用量[：:\s]*([^。]{1,100})',
            r'(\d+[-~～]\d+[克g])[，、\s]*煎服',
            r'煎服[^。]*?(\d+[-~～]\d+[克g])',
        ]
        
        for pattern in dosage_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        
        return ""

    def clean_indications_text(self, text):
        """清理主治文本，移除用量相关信息"""
        # 移除用量相关的句子
        patterns_to_remove = [
            r'用量\d+[-~～]\d+[克g][^。]*',
            r'[，、\s]*煎服[^。]*',
            r'[，、\s]*外用适量[^。]*',
            r'[，、\s]*研末调敷[^。]*',
            r'[，、\s]*煎水浸渍患处[^。]*',
            r'用治[：\s]*',
            r'^[。，、\s]+',  # 移除开头的标点符号
        ]
        
        cleaned_text = text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text)
        
        return cleaned_text.strip()

    def is_dosage_text(self, text):
        """判断是否为用量相关文本"""
        dosage_keywords = ['用量', '煎服', '外用', '研末', '浸渍']
        return any(keyword in text for keyword in dosage_keywords)

    def extract_detailed_category(self, herbal_data, cleaned_text):
        """提取更详细的分类信息"""
        try:
            # 查找更具体的分类描述
            detailed_category_patterns = [
                r'属([^。]*?)药下属分类的([^。]*?药)',
                r'属([^。]*?药)下属分类的([^。]*?药)',
                r'([清热泻火解毒凉血燥湿温里理气活血化瘀止血补气血阴阳安神开窍祛风湿化痰止咳平喘消食驱虫外用]+药)',
            ]
            
            for pattern in detailed_category_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    if len(match.groups()) >= 2:
                        # 如果有两个分组，取更具体的分类
                        detailed_category = match.group(2).strip()
                        if detailed_category and len(detailed_category) < 20:
                            herbal_data['category'] = detailed_category
                            break
                    else:
                        # 只有一个分组
                        detailed_category = match.group(1).strip()
                        if detailed_category and len(detailed_category) < 20:
                            herbal_data['category'] = detailed_category
                            break
        except Exception as e:
            logging.warning(f"提取详细分类失败: {e}")

    def extract_usage_info(self, herbal_data, page_text, soup):
        """提取用法用量信息 - 优化版：提取完整的临床应用内容"""
        try:
            cleaned_text = re.sub(r'\s+', ' ', page_text)
            
            # 尝试提取完整的临床应用信息（无论dosage是否已有内容）
            dosage_patterns = [
                # 模式3效果最好：匹配临床应用到下一个【】标记
                r'临床应用[：:\s]*([^【]*?)(?=【|$)',
                # 备用模式：匹配【临床应用】到下一个【】标记之间的内容
                r'【临床应用】([^【]+?)(?=【|$)',
                # 备用模式：匹配【用法用量】段落
                r'【用法用量】([^【]+?)(?=【|$)',
                r'用法用量[：:\s]*([^【]+?)(?=【|$)',
                # 最后备用：匹配包含"用量"的完整段落
                r'(用量\d+[-~～]\d+[克g][^【]*?)(?=【|$)',
            ]
            
            for pattern in dosage_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    dosage_text = match.group(1).strip()
                    
                    # 清理HTML标签
                    dosage_text = re.sub(r'<[^>]+>', '', dosage_text)
                    # 清理多余的空白
                    dosage_text = re.sub(r'\s+', ' ', dosage_text)
                    
                    # 移除明显的页面元素和链接
                    dosage_text = re.sub(r'最近更新时间[：:].*', '', dosage_text)
                    dosage_text = re.sub(r'更多相关文章.*', '', dosage_text)
                    dosage_text = re.sub(r'中药常见偏方.*', '', dosage_text)
                    
                    # 去除开头和结尾的特殊字符（包括】）
                    dosage_text = dosage_text.strip('。，；：】')
                    
                    # 验证内容质量：必须包含关键信息
                    key_parts = ['用量', '克']
                    has_key_info = any(part in dosage_text for part in key_parts)
                    
                    # 检查是否比现有dosage更完整
                    current_dosage = herbal_data.get('dosage', '')
                    is_more_complete = len(dosage_text) > len(current_dosage)
                    
                    if has_key_info and len(dosage_text) > 10 and len(dosage_text) < 500:
                        # 如果新提取的内容更完整，则替换
                        if is_more_complete:
                            herbal_data['dosage'] = dosage_text
                        break
                    
        except Exception as e:
            logging.warning(f"提取用法用量信息失败: {e}")

    def extract_common_pairings(self, herbal_data, cleaned_text):
        """提取配伍药方信息（简化为字符串数组）"""
        try:
            # 查找配伍药方部分
            pairing_patterns = [
                r'【配伍药方】([^【]+)',
                r'【相关药方】([^【]+)', 
                r'配伍药方[：:\s]*([^【]+)',
                r'相关药方[：:\s]*([^【]+)',
            ]
            
            pairings = []
            
            for pattern in pairing_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    pairings_text = match.group(1).strip()
                    
                    # 提取具体的药方名称和组成
                    # 匹配形如：①治xxx：药方名称、组成。的格式
                    pairing_items = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩]\s*治([^：]+)[：:]\s*([^。①②③④⑤⑥⑦⑧⑨⑩]+)', pairings_text)
                    
                    for indication, formula in pairing_items:
                        if len(indication.strip()) > 0 and len(formula.strip()) > 0:
                            # 提取药方名称（通常在最后的括号中）
                            name_match = re.search(r'\(([^)]+)\)$', formula.strip())
                            formula_name = name_match.group(1) if name_match else ""
                            
                            # 清理配方内容，移除最后的来源信息
                            clean_formula = re.sub(r'\([^)]*\)$', '', formula.strip()).strip()
                            
                            # 组合成字符串格式
                            if formula_name:
                                pairing_str = f"治{indication.strip()}：{clean_formula}（{formula_name}）"
                            else:
                                pairing_str = f"治{indication.strip()}：{clean_formula}"
                            
                            pairings.append(pairing_str)
                    
                    # 如果找到了配伍信息就跳出循环
                    if pairings:
                        break
            
            # 如果没有找到标准格式，尝试其他格式
            if not pairings:
                # 尝试匹配简单的药方列举
                simple_patterns = [
                    r'常用配伍[：:\s]*([^【]{1,200})',
                    r'配伍[：:\s]*([^【]{1,200})',
                ]
                
                for pattern in simple_patterns:
                    match = re.search(pattern, cleaned_text)
                    if match:
                        pairing_text = match.group(1).strip()
                        # 简单分割
                        pairing_items = re.split(r'[。；]', pairing_text)
                        for item in pairing_items:
                            if item.strip() and len(item.strip()) > 5 and len(item.strip()) < 100:
                                pairings.append(item.strip())
                        break
            
            herbal_data['commonPairings'] = pairings
            
        except Exception as e:
            logging.warning(f"提取配伍信息失败: {e}")
    
    def extract_cautions_info(self, herbal_data, page_text, soup):
        """提取注意事项和禁忌 - 优化版：只保留核心禁忌信息"""
        try:
            cleaned_text = re.sub(r'\s+', ' ', page_text)
            
            # 优化的禁忌提取模式 - 只匹配到句号结束
            contraindication_patterns = [
                r'【使用禁忌】([^【。]*?)。',
                r'【禁忌】([^【。]*?)。',
                r'使用禁忌[：:\s]*([^【。]*?)。',
                r'禁忌[：:\s]*([^【。]*?)。',
                r'【注意事项】([^【。]*?)。',
                r'注意事项[：:\s]*([^【。]*?)。',
            ]
            
            for pattern in contraindication_patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    contraindications_text = match.group(1).strip()
                    
                    # 清理HTML标签
                    contraindications_text = re.sub(r'<[^>]+>', '', contraindications_text)
                    # 清理多余的空白
                    contraindications_text = re.sub(r'\s+', ' ', contraindications_text)
                    # 去除开头和结尾的特殊字符
                    contraindications_text = contraindications_text.strip('，；：】')
                    
                    if len(contraindications_text) > 2 and len(contraindications_text) < 100:
                        herbal_data['contraindications'] = contraindications_text
                        break
                    
        except Exception as e:
            logging.warning(f"提取禁忌信息失败: {e}")
    
    def extract_description(self, herbal_data, page_text, soup):
        """提取描述信息，整合药用部位、植物形态、产地分布、采收加工、药材性状等详细信息"""
        try:
            cleaned_text = re.sub(r'\s+', ' ', page_text)
            description_parts = []
            
            # 定义要提取的字段模式
            field_patterns = [
                ('药用部位', [
                    r'【药用部位】([^【]{1,300})',
                    r'药用部位[：:\s]*([^【]{1,300})',
                ]),
                ('植物形态', [
                    r'【植物形态】([^【]{1,500})',
                    r'【形态特征】([^【]{1,500})',
                    r'植物形态[：:\s]*([^【]{1,500})',
                    r'形态特征[：:\s]*([^【]{1,500})',
                ]),
                ('产地分布', [
                    r'【产地分布】([^【]{1,300})',
                    r'【生境分布】([^【]{1,300})',
                    r'产地分布[：:\s]*([^【]{1,300})',
                    r'生境分布[：:\s]*([^【]{1,300})',
                ]),
                ('采收加工', [
                    r'【采收加工】([^【]{1,300})',
                    r'【采制】([^【]{1,300})',
                    r'采收加工[：:\s]*([^【]{1,300})',
                    r'采制[：:\s]*([^【]{1,300})',
                ]),
                ('药材性状', [
                    r'【药材性状】([^【]{1,400})',
                    r'【性状】([^【]{1,400})',
                    r'药材性状[：:\s]*([^【]{1,400})',
                    r'性状[：:\s]*([^【]{1,400})',
                ])
            ]
            
            # 提取每个字段的内容
            for field_name, patterns in field_patterns:
                field_content = None
                
                for pattern in patterns:
                    match = re.search(pattern, cleaned_text)
                    if match:
                        content = match.group(1).strip()
                        # 清理多余的空白和标点
                        content = re.sub(r'\s+', ' ', content)
                        content = content.strip('。，；：')
                        
                        # 过滤掉包含页面导航元素的内容
                        if field_name == '药用部位':
                            # 如果包含明显的导航或页面元素，跳过
                            nav_keywords = ['分类', '共收录', '当前位置', '主页', '设为首页', '加入收藏', 'QQ空间', '朋友网']
                            if any(keyword in content for keyword in nav_keywords):
                                continue
                            # 如果内容过长也可能包含无关信息
                            if len(content) > 100:
                                continue
                        
                        if len(content) > 10 and len(content) < 500:  # 合理的长度范围
                            field_content = content
                            break
                
                # 如果找到了内容，添加到描述中
                if field_content:
                    description_parts.append(f"{field_name}：{field_content}")
            
            # 如果没有找到任何特定字段，尝试获取基本信息
            if not description_parts:
                fallback_patterns = [
                    r'【来源】([^【]{1,200})',
                    r'【别名】([^【]{1,100})',
                ]
                
                for pattern in fallback_patterns:
                    match = re.search(pattern, cleaned_text)
                    if match:
                        content = match.group(1).strip()
                        if len(content) > 5 and len(content) < 200:
                            description_parts.append(content)
                            break
            
            # 如果还是没有内容，使用页面标题
            if not description_parts:
                title = soup.find('title')
                if title:
                    title_text = title.get_text(strip=True)
                    description_parts.append(title_text)
            
            # 组合所有部分，用换行符分割
            if description_parts:
                herbal_data['description'] = '\n'.join(description_parts)
            else:
                herbal_data['description'] = ""
                    
        except Exception as e:
            logging.warning(f"提取描述信息失败: {e}")
            herbal_data['description'] = ""
    
    def extract_images(self, soup, page_url):
        """提取药材图片 - 优化版：只提取真正的药材主图"""
        images = []
        try:
            img_tags = soup.find_all('img')
            
            for img in img_tags:
                src = img.get('src')
                if not src:
                    continue
                
                # 转换为绝对URL
                full_url = urljoin(page_url, src)
                
                # 基本过滤：过滤掉明显不相关的图片
                if not self.is_herb_image(src, img):
                    continue
                
                # 精确过滤：只保留真正的药材主图
                if self.is_main_herb_image(img, soup):
                    images.append(full_url)
            
            # 去重
            images = list(set(images))
            
        except Exception as e:
            logging.warning(f"提取图片失败: {e}")
        
        return images
    
    def is_herb_image(self, src, img_tag):
        """判断是否为药材相关图片"""
        # 过滤掉明显不相关的图片
        exclude_keywords = ['logo', 'icon', 'button', 'banner', 'nav']
        
        src_lower = src.lower()
        for keyword in exclude_keywords:
            if keyword in src_lower:
                return False
        
        # 特殊处理：避免误判allimg中的ad
        if 'ad' in src_lower and 'allimg' not in src_lower:
            return False
        
        # 检查图片尺寸属性
        width = img_tag.get('width')
        height = img_tag.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                # 过滤掉太小的图片（可能是图标）
                if w < 50 or h < 50:
                    return False
            except ValueError:
                pass
        
        return True
    
    def is_main_herb_image(self, img, soup):
        """判断是否为药材主图（非相关推荐图片）"""
        try:
            # 检查1: Alt属性是否包含功效、作用等关键词
            alt = img.get('alt', '').strip()
            if alt:
                # 如果alt包含功效、作用等关键词，可能是主图
                main_keywords = ['功效', '作用', '的功效与作用']
                if any(keyword in alt for keyword in main_keywords):
                    return True
                
                # 如果alt是其他药材名称，很可能是推荐图片
                other_herb_keywords = ['苦瓜', '肾茶', '鸡冠花', '金果榄', '菊花', '白背叶根']
                if any(keyword in alt for keyword in other_herb_keywords):
                    return False
            
            # 检查2: 父元素结构
            parent = img.parent
            if parent:
                # 如果父元素是链接且class包含title，很可能是推荐链接
                if parent.name == 'a' and 'title' in parent.get('class', []):
                    return False
                
                # 如果父元素是段落标签，可能是正文中的主图
                if parent.name == 'p':
                    return True
            
            # 检查3: 容器位置
            container = img.find_parent('div')
            if container:
                container_classes = container.get('class', [])
                
                # 如果在主要文本区域，可能是主图
                if 'text' in container_classes:
                    return True
                
                # 如果在推荐区域，是推荐图片
                if any(cls in container_classes for cls in ['box5_c', 'box8_c', 'marT10']):
                    return False
            
            # 检查4: 图片样式特征
            style = img.get('style', '')
            if style and ('width:' in style or 'height:' in style):
                # 有明确尺寸设置的图片更可能是主图
                return True
            
            # 检查5: 图片对齐方式
            align = img.get('align', '')
            if align in ['right', 'left']:
                # 有对齐设置的图片更可能是正文中的主图
                return True
            
            # 默认情况：如果无法确定，保守地认为是主图
            return True
            
        except Exception as e:
            logging.warning(f"判断主图失败: {e}")
            return True
    
    def crawl_all_categories(self, max_categories=None, max_herbs_per_category=None):
        """爬取所有分类的药材数据"""
        logging.info("开始爬取所有分类的药材数据...")
        
        # 首先获取所有分类
        categories = self.parse_category_page()
        
        if not categories:
            logging.error("未能获取到任何分类信息")
            return
        
        # 限制爬取的分类数量
        if max_categories:
            categories = categories[:max_categories]
        
        for i, category in enumerate(categories, 1):
            logging.info(f"处理分类 {i}/{len(categories)}: {category['name']}")
            
            # 获取该分类下的药材列表
            herb_items = self.parse_category_list_page(category)
            
            if not herb_items:
                logging.warning(f"分类 '{category['name']}' 中没有找到药材")
                continue
            
            # 限制每个分类爬取的药材数量
            if max_herbs_per_category:
                herb_items = herb_items[:max_herbs_per_category]
            
            # 爬取每个药材的详细信息
            for j, herb_item in enumerate(herb_items, 1):
                logging.info(f"处理药材 {j}/{len(herb_items)}: {herb_item['name']}")
                
                herb_data = self.parse_herb_detail_page(herb_item)
                if herb_data:
                    self.herbal_data.append(herb_data)
                    logging.info(f"成功爬取药材 '{herb_item['name']}' 的信息")
                
                # 每爬取5个药材后保存一次数据
                if len(self.herbal_data) % 5 == 0:
                    self.save_data()
            
            # 每个分类之间增加延时
            time.sleep(2)
        
        # 最终保存所有数据
        self.save_data()
        logging.info(f"爬取完成！总共获取了 {len(self.herbal_data)} 个药材的信息")
    
    def save_data(self):
        """保存数据到JSON文件"""
        if not self.herbal_data:
            logging.warning("没有数据需要保存")
            return
        
        filename = 'zhongyoo_herbal_data.json'
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.herbal_data, f, ensure_ascii=False, indent=2)
            logging.info(f"数据已保存到 {filename}，共 {len(self.herbal_data)} 条记录")
        except Exception as e:
            logging.error(f"保存数据失败: {e}")

def main():
    """主函数"""
    crawler = ZhongYooHerbalCrawler()
    
    print("=== 中医药网数据爬取工具 ===")
    print("1. 查看所有分类")
    print("2. 爬取指定数量的分类数据")
    print("3. 爬取所有分类数据")
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == "1":
        # 仅查看分类
        categories = crawler.parse_category_page()
        print(f"\n找到 {len(categories)} 个分类:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category['name']} - {category['url']}")
    
    elif choice == "2":
        # 爬取指定数量
        max_categories = input("请输入要爬取的分类数量（默认3个）: ").strip()
        max_herbs = input("请输入每个分类爬取的药材数量（默认5个）: ").strip()
        
        try:
            max_categories = int(max_categories) if max_categories else 3
            max_herbs = int(max_herbs) if max_herbs else 5
        except ValueError:
            max_categories, max_herbs = 3, 5
        
        crawler.crawl_all_categories(max_categories=max_categories, 
                                   max_herbs_per_category=max_herbs)
    
    elif choice == "3":
        # 爬取所有数据
        confirm = input("这将爬取所有分类的所有药材数据，可能需要很长时间。确认继续？(y/N): ").strip().lower()
        if confirm == 'y':
            crawler.crawl_all_categories()
        else:
            print("操作已取消")
    
    else:
        print("无效的选择")

if __name__ == "__main__":
    main() 