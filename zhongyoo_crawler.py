#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中药材数据爬取脚本 - 中医药网版本
作者: AI Assistant
功能: 爬取中医药网(zhongyoo.com)的中药材数据
网站结构:
1. 名称列表页面: http://www.zhongyoo.com/name/
2. 药材详情页面: http://www.zhongyoo.com/name/{name}_{id}.html
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
import random
from fake_useragent import UserAgent
from retrying import retry
import os
from urllib.parse import urljoin, urlparse
import logging
import chardet
import argparse

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
        self.name_list_url = "http://www.zhongyoo.com/name/"
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
        # 爬取间隔设置
        self.page_interval = (4, 6)  # 页面间隔4-6秒
        self.item_interval = (2, 3)  # 药材项目间隔2-3秒
        
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=3000)
    def get_page(self, url):
        """获取页面内容，包含重试机制和编码检测"""
        try:
            # 每次请求前更新User-Agent
            self.session.headers.update({
                'User-Agent': self.ua.random,
            })
            
            response = self.session.get(url, timeout=15)
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
    
    def parse_name_list_page(self, page_num=1):
        """解析药材名称列表页面"""
        url = f"{self.name_list_url}page_{page_num}.html" if page_num > 1 else self.name_list_url
        logging.info(f"正在爬取名称列表页面: {url}")
        
        try:
            html = self.get_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            herbal_items = []
            
            # 查找药材列表区域 - 根据网页结构，查找包含药材信息的 div.r2-con
            r2_con_div = soup.find('div', class_='r2-con')
            
            if r2_con_div:
                # 找到所有药材项目 div.sp
                herb_divs = r2_con_div.find_all('div', class_='sp')
                
                for herb_div in herb_divs:
                    # 获取药材名称和链接
                    link_tag = herb_div.find('a', class_='title')
                    if link_tag:
                        herb_name = link_tag.get_text(strip=True)
                        herb_url = urljoin(self.base_url, link_tag.get('href'))
                        
                        if herb_name and len(herb_name) > 0 and herb_url:
                            herbal_items.append({
                                'name': herb_name,
                                'url': herb_url
                            })
            
            # 如果没有找到药材项目，尝试其他方式
            if not herbal_items:
                # 查找所有可能的药材链接
                all_links = soup.find_all('a', class_='title')
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/name/' in href and '.html' in href and text:
                        herb_url = urljoin(self.base_url, href)
                        herbal_items.append({
                            'name': text,
                            'url': herb_url
                        })
            
            logging.info(f"在页面 {page_num} 中找到 {len(herbal_items)} 个药材")
            
            # 获取最大页码数
            max_page = 1
            pagination_div = soup.find('div', class_='dede_pages')
            if pagination_div:
                # 查找最后一页链接
                last_page_link = pagination_div.find('a', string='末页')
                if last_page_link:
                    href = last_page_link.get('href', '')
                    match = re.search(r'page_(\d+)\.html', href)
                    if match:
                        max_page = int(match.group(1))
                
                # 如果没有找到末页链接，则查找所有页码链接
                if max_page == 1:
                    page_links = pagination_div.find_all('a', href=re.compile(r'page_\d+\.html'))
                    for page_link in page_links:
                        match = re.search(r'page_(\d+)\.html', page_link.get('href', ''))
                        if match:
                            page_num = int(match.group(1))
                            if page_num > max_page:
                                max_page = page_num
            
            return herbal_items, max_page
            
        except Exception as e:
            logging.error(f"解析名称列表页面失败: {e}")
            return [], 1
    
    def parse_herb_detail_page(self, herb_item):
        """解析药材详情页面"""
        name = herb_item['name']
        url = herb_item['url']
        
        logging.info(f"正在爬取药材 '{name}' 的详细信息: {url}")
        
        try:
            html = self.get_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            # 初始化数据结构
            herbal_data = {
                "id": self.current_id,
                "name": name,
                "pinyin": "",
                "category": "",
                "taste": "",
                "meridians": [],
                "morphology": "",  # 植物形态
                "medicinal_part": "",  # 药用部位
                "distribution": "",  # 产地分布
                "processing": "",  # 采收加工
                "characteristics": "",  # 药材性状
                "pharmacology": "",  # 药理研究
                "main_components": "",  # 主要成分/化学成分
                "clinical_application": "",  # 临床应用
                "prescriptions": [],  # 配伍药方
                "contraindications": "",  # 使用禁忌
                "images": [],
                "source_url": url
            }
            
            # 查找内容区域
            # 首先尝试class='wrap1'包含的内容
            content_div = None
            
            # 查找各种可能的内容区域
            content_candidates = [
                soup.find('div', class_='text'),
                soup.find('div', class_='gaishu'),
                soup.find('div', class_='con_left2'),
                soup.find('div', class_='wrap1')
            ]
            
            # 选择第一个找到的且包含足够文本的区域
            for div in content_candidates:
                if div and len(div.get_text(strip=True)) > 100:
                    content_div = div
                    break
            
            # 如果没有找到合适的区域，尝试找最长文本的div
            if not content_div:
                all_divs = soup.find_all('div')
                max_text_len = 0
                for div in all_divs:
                    text_len = len(div.get_text(strip=True))
                    if text_len > max_text_len:
                        max_text_len = text_len
                        content_div = div
            
            if not content_div:
                logging.warning(f"在页面中未找到主要内容区域: {url}")
                return None
                
            html_content = str(content_div)
            
            # 首先查找所有【<strong>...</strong>】格式的标题
            section_titles = re.findall(r'【<strong>(.*?)</strong>】', html_content)
            
            # 遍历找到的标题进行内容提取
            for title in section_titles:
                pattern = f'【<strong>{title}</strong>】(.*?)(?:【<strong>|<div class="pagead">|$)'
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    clean_content = self._clean_html_tags(content)
                    
                    # 根据标题填充对应字段
                    if title == "中药名":
                        # 从内容中提取拼音部分，通常在中药名后面
                        name_parts = clean_content.split()
                        if len(name_parts) > 1:
                            herbal_data["pinyin"] = name_parts[1]
                    elif title == "性味归经":
                        herbal_data["taste"] = clean_content
                        # 从性味归经中提取归经信息
                        meridians = re.findall(r'[肝心脾肺肾胃大小肠三焦膀胱胆]经', clean_content)
                        if meridians:
                            herbal_data["meridians"] = list(set(meridians))
                    elif title == "植物形态":
                        herbal_data["morphology"] = clean_content
                    elif title == "药用部位":
                        herbal_data["medicinal_part"] = clean_content
                    elif title == "产地分布":
                        herbal_data["distribution"] = clean_content
                    elif title == "采收加工":
                        herbal_data["processing"] = clean_content
                    elif title == "药材性状":
                        herbal_data["characteristics"] = clean_content
                    elif title == "功效与作用":
                        # 从功效与作用中可能可以提取分类信息
                        herbal_data["category"] = self._extract_category(clean_content)
                    elif title == "药理研究":
                        herbal_data["pharmacology"] = clean_content
                    elif title == "化学成分" or title == "主要成分":
                        herbal_data["main_components"] = clean_content
                    elif title == "临床应用":
                        herbal_data["clinical_application"] = clean_content
                    elif title == "配伍药方":
                        # 提取药方条目，尝试各种可能的格式
                        prescriptions = []
                        
                        # 尝试使用序号提取方剂
                        # 中文数字序号
                        chinese_numbered = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩].*?(?=(?:[①②③④⑤⑥⑦⑧⑨⑩]|$))', clean_content)
                        if chinese_numbered:
                            prescriptions.extend(chinese_numbered)
                        
                        # 阿拉伯数字序号
                        if not prescriptions:
                            arabic_numbered = re.findall(r'[1-9]、.*?(?=(?:[1-9]、|$))', clean_content)
                            if arabic_numbered:
                                prescriptions.extend(arabic_numbered)
                        
                        # 书名号《》包裹的方剂
                        if not prescriptions:
                            book_titled = re.findall(r'《.*?》.*?(?=(?:《|$))', clean_content)
                            if book_titled:
                                prescriptions.extend(book_titled)
                        
                        # 如果以上都未提取到，可能是单方或其他格式，直接使用整个内容
                        if not prescriptions and clean_content:
                            prescriptions = [clean_content]
                        
                        herbal_data["prescriptions"] = [p.strip() for p in prescriptions if p.strip()]
                    elif title == "使用禁忌" or title == "禁忌":
                        herbal_data["contraindications"] = clean_content
            
            # 提取图片
            herbal_data['images'] = self.extract_images(soup, url)
            
            self.current_id += 1
            
            # 延时避免请求过快
            time.sleep(random.uniform(self.item_interval[0], self.item_interval[1]))
            
            return herbal_data
            
        except Exception as e:
            logging.error(f"解析药材 '{name}' 详情页面失败: {e}")
            return None
    
    def _extract_category(self, text):
        """从功效与作用中提取分类信息"""
        category = ""
        # 常见分类关键词
        category_patterns = [
            r'属(.*?)药',
            r'属于(.*?)类',
            r'归属(.*?)类'
        ]
        
        for pattern in category_patterns:
            match = re.search(pattern, text)
            if match:
                category = match.group(1).strip()
                break
        
        return category
    
    def _clean_html_tags(self, text):
        """清理HTML标签和实体"""
        if not text:
            return ""
        # 使用BeautifulSoup清理HTML标签
        clean_text = BeautifulSoup(text, 'lxml').get_text()
        # 替换多个空白字符为单个空格
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def extract_images(self, soup, page_url):
        """从详情页提取药材图片"""
        images = []
        try:
            # 首先尝试从页面中找到药材主图
            content_area = soup.find('div', class_='gaishu')
            if content_area:
                main_img_tags = content_area.find_all('img')
                for img in main_img_tags:
                    src = img.get('src')
                    if src and not src.endswith(('.gif', '.GIF')):
                        img_url = urljoin(page_url, src)
                        if img_url not in images:
                            images.append(img_url)
            
            # 如果未在主内容区域找到图片，尝试查找整个页面的药材图片
            if not images:
                # 尝试查找特定区域内的图片
                herb_img_divs = [
                    soup.find('div', class_='gaishut'),
                    soup.find('div', class_='text'),
                    soup.find('div', class_='con_left2')
                ]
                
                for div in herb_img_divs:
                    if div:
                        img_tags = div.find_all('img')
                        for img in img_tags:
                            src = img.get('src')
                            if src and self.is_herb_image(src, img):
                                img_url = urljoin(page_url, src)
                                if img_url not in images:
                                    images.append(img_url)
            
            # 如果仍未找到图片，尝试查找整个页面中可能的药材图片
            if not images:
                # 获取页面所有图片
                all_img_tags = soup.find_all('img')
                
                # 筛选可能的药材图片
                for img in all_img_tags:
                    src = img.get('src')
                    if not src:
                        continue
                    
                    # 转换为绝对 URL
                    img_url = urljoin(page_url, src)
                    
                    # 过滤掉常见的非药材图片
                    if self.is_herb_image(src, img):
                        # 添加到图片列表
                        if img_url not in images:
                            images.append(img_url)
            
            # 查找特定的药材图片模式
            # 在中药网站中，药材图片通常包含特定的路径模式
            herb_image_patterns = [
                '/uploads/allimg/',
                '/yaocai/',
                '/zhongyao/',
                '/upload/image/',
                '/herb/',
                '/zyimg/'
            ]
            
            potential_herb_images = []
            for img_url in images:
                for pattern in herb_image_patterns:
                    if pattern in img_url.lower():
                        potential_herb_images.append(img_url)
                        break
            
            # 如果找到了特定模式的图片，优先使用这些图片
            if potential_herb_images:
                images = potential_herb_images
                
            # 移除重复的图片URL
            images = list(dict.fromkeys(images))
            
        except Exception as e:
            logging.error(f"提取图片失败: {e}")
        
        return images
    
    def is_herb_image(self, src, img_tag):
        """判断图片是否为药材相关图片"""
        # 忽略明显的非药材图片
        ignored_patterns = [
            'logo', 'icon', 'banner', 'button', 'ad', 'advertisement',
            'nav', 'header', 'footer', 'sidebar', 'menu', 'share',
            'like', 'comment', 'avatar', 'profile', 'user', 'bg', 'background'
        ]
        
        for pattern in ignored_patterns:
            if pattern in src.lower():
                return False
        
        # 忽略常见的图标和装饰图片格式
        if src.endswith(('.gif', '.GIF', 'dot.png', 'spacer.gif')):
            return False
        
        # 检查图片尺寸（如果有）
        width = img_tag.get('width')
        height = img_tag.get('height')
        
        if width and height:
            try:
                w = int(width)
                h = int(height)
                # 忽略非常小的图片
                if w < 100 or h < 100:
                    return False
                # 忽略过于细长的图片（可能是分隔线或装饰）
                if w/h > 5 or h/w > 5:
                    return False
            except ValueError:
                pass
        
        # 检查alt和title属性，如果包含药材名称相关的词语，更可能是药材图片
        alt_text = img_tag.get('alt', '').lower()
        title_text = img_tag.get('title', '').lower()
        
        herb_keywords = ['药材', '中药', '植物', '药用', '功效', '形态', 'herb', 'medicinal']
        for keyword in herb_keywords:
            if keyword in alt_text or keyword in title_text:
                return True
        
        # 检查父元素
        parent = img_tag.parent
        if parent:
            parent_class = ' '.join(parent.get('class', []))
            parent_id = parent.get('id', '')
            parent_text = parent.get_text(strip=True)
            
            # 如果父元素是明显的非内容区域
            if any(pattern in (parent_class + parent_id).lower() for pattern in ignored_patterns):
                return False
            
            # 如果父元素文本包含植物、药材相关词汇，更可能是药材图片
            herb_related_terms = ['植物', '药材', '形态', '性状', '图片', '药用', '中药', '种植', '采收']
            if any(term in parent_text for term in herb_related_terms):
                return True
            
            # 如果父元素有特定的class或id，可能是药材图片容器
            herb_img_containers = ['herb-img', 'herb_img', 'herb-photo', 'herb_photo', 'drug-img', 'drug_img', 'yaocai']
            if any(container in (parent_class + parent_id).lower() for container in herb_img_containers):
                return True
        
        # 尝试通过URL模式判断
        herb_image_patterns = ['/uploads/', '/images/', '/yaocai/', '/zhongyao/', '/upload/']
        if any(pattern in src.lower() for pattern in herb_image_patterns):
            return True
        
        # 默认可能接受大部分图片
        return True
    
    def crawl_all_pages(self, max_pages=None, max_herbs_per_page=None, start_page=1):
        """爬取所有页面的药材数据
        
        参数:
            max_pages: 最大爬取页数，None表示爬取所有页
            max_herbs_per_page: 每页最大爬取药材数，None表示爬取所有
            start_page: 起始页码，用于断点续传
        """
        logging.info("开始爬取所有药材数据...")
        
        try:
            # 如果存在之前的数据，先加载
            if os.path.exists('zhongyoo_herbal_data.json') and start_page > 1:
                try:
                    with open('zhongyoo_herbal_data.json', 'r', encoding='utf-8') as f:
                        self.herbal_data = json.load(f)
                    logging.info(f"已加载现有数据，共 {len(self.herbal_data)} 条记录")
                    
                    # 更新当前ID
                    if self.herbal_data:
                        self.current_id = max([item['id'] for item in self.herbal_data]) + 1
                except Exception as e:
                    logging.error(f"加载现有数据失败: {e}")
            
            # 获取第一页数据和总页数
            _, total_pages = self.parse_name_list_page(1)
            
            # 如果指定了最大页数，使用较小值
            if max_pages is not None:
                total_pages = min(total_pages, max_pages)
            
            logging.info(f"共找到 {total_pages} 页药材数据")
            
            # 处理第一页数据（如果start_page为1）
            if start_page == 1:
                herbs_page1, _ = self.parse_name_list_page(1)
                herbs_to_process = herbs_page1
                
                if max_herbs_per_page is not None:
                    herbs_to_process = herbs_to_process[:max_herbs_per_page]
                
                for herb in herbs_to_process:
                    herb_data = self.parse_herb_detail_page(herb)
                    if herb_data:
                        self.herbal_data.append(herb_data)
                        logging.info(f"成功爬取药材: {herb['name']} ({len(self.herbal_data)}/{len(herbs_page1)})")
                        # 每爬取5个药材保存一次数据
                        if len(self.herbal_data) % 5 == 0:
                            self.save_data()
                
                # 第一页完成后保存一次数据
                self.save_data()
                start_page = 2
            
            # 处理剩余页面
            for page_num in range(start_page, total_pages + 1):
                logging.info(f"开始爬取第 {page_num}/{total_pages} 页")
                
                herbs_page, _ = self.parse_name_list_page(page_num)
                
                if max_herbs_per_page is not None:
                    herbs_page = herbs_page[:max_herbs_per_page]
                
                for i, herb in enumerate(herbs_page):
                    herb_data = self.parse_herb_detail_page(herb)
                    if herb_data:
                        self.herbal_data.append(herb_data)
                        logging.info(f"成功爬取药材: {herb['name']} ({i+1}/{len(herbs_page)})")
                        # 每爬取5个药材保存一次数据
                        if len(self.herbal_data) % 5 == 0:
                            self.save_data()
                
                # 每页完成后保存一次数据
                self.save_data()
                
                # 页面间延迟
                time.sleep(random.uniform(self.page_interval[0], self.page_interval[1]))
                
                # 每爬取10页，提示一下当前进度
                if page_num % 10 == 0:
                    logging.info(f"已完成 {page_num}/{total_pages} 页的爬取，当前共有 {len(self.herbal_data)} 条数据")
            
            logging.info(f"所有页面爬取完成，共获取 {len(self.herbal_data)} 个药材数据")
            
        except Exception as e:
            logging.error(f"爬取过程中出现错误: {e}")
        finally:
            # 保存已获取的数据
            self.save_data()
    
    def save_data(self):
        """保存爬取的数据到JSON文件"""
        try:
            # 主JSON文件，确保中文字符正确显示
            with open('zhongyoo_herbal_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.herbal_data, f, ensure_ascii=False, indent=2)
            logging.info(f"数据已保存到 zhongyoo_herbal_data.json, 共 {len(self.herbal_data)} 条记录")
            
            # 额外保存一个用于调试的副本
            with open('zhongyoo_herbal_data_debug.json', 'w', encoding='utf-8') as f:
                # 使用ASCII编码可以在控制台查看
                json.dump(self.herbal_data, f, ensure_ascii=True, indent=2)
        except Exception as e:
            logging.error(f"保存数据失败: {e}")

def main():
    """主函数"""
    crawler = ZhongYooHerbalCrawler()
    try:
        # 获取命令行参数
        parser = argparse.ArgumentParser(description='中药材爬虫')
        parser.add_argument('--max-pages', type=int, help='最大爬取页数，默认全部爬取', default=None)
        parser.add_argument('--max-herbs', type=int, help='每页最大爬取药材数，默认全部爬取', default=None)
        parser.add_argument('--start-page', type=int, help='起始页码，用于断点续传', default=1)
        parser.add_argument('--interval', type=int, help='页面间隔基准秒数，实际为随机(n,n+2)秒', default=4)
        args = parser.parse_args()
        
        # 设置爬取间隔
        if args.interval:
            crawler.page_interval = (args.interval, args.interval + 2)
            crawler.item_interval = (args.interval // 2, args.interval // 2 + 1)
            logging.info(f"已设置页面间隔 {crawler.page_interval} 秒，药材间隔 {crawler.item_interval} 秒")
        
        # 爬取数据
        crawler.crawl_all_pages(args.max_pages, args.max_herbs, args.start_page)
        
    except KeyboardInterrupt:
        print("\n用户中断爬取，已保存当前进度")
    except Exception as e:
        logging.error(f"爬取过程中出现错误: {e}")
    finally:
        # 保存已获取的数据
        crawler.save_data()

def test_parser():
    """测试解析器"""
    crawler = ZhongYooHerbalCrawler()
    
    # 测试第一页
    herbs, total_pages = crawler.parse_name_list_page(1)
    
    print(f"找到 {len(herbs)} 个药材，共 {total_pages} 页")
    for i, herb in enumerate(herbs[:5]):  # 只打印前5个
        print(f"{i+1}. {herb['name']} - {herb['url']}")
    
    if len(herbs) > 0:
        print("\n测试解析第一个药材详情页...")
        herb_data = crawler.parse_herb_detail_page(herbs[0])
        if herb_data:
            print(f"药材名称: {herb_data['name']}")
            print(f"拼音: {herb_data['pinyin']}")
            print(f"分类: {herb_data['category']}")
            print(f"味道归经: {herb_data['taste']}")
            print(f"归经: {herb_data['meridians']}")
            print(f"图片数量: {len(herb_data['images'])}")
    
    # 测试第二页
    print("\n测试第二页...")
    herbs_page2, _ = crawler.parse_name_list_page(2)
    print(f"第二页找到 {len(herbs_page2)} 个药材")
    for i, herb in enumerate(herbs_page2[:5]):  # 只打印前5个
        print(f"{i+1}. {herb['name']} - {herb['url']}")

if __name__ == "__main__":
    # 判断是否为测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_parser()
    else:
        main() 