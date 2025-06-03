#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理脚本
用于清理和标准化爬取到的中药材数据
"""

import json
import re
from typing import List, Dict, Any

class HerbalDataProcessor:
    def __init__(self):
        self.common_pairings_template = [
            {"name": "甘草", "usage": "调和诸药", "effect": "调和药性，减轻副作用"},
            {"name": "大枣", "usage": "补益脾胃", "effect": "增强药效，保护脾胃"},
        ]
    
    def load_data(self, filename: str) -> List[Dict[str, Any]]:
        """加载JSON数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return []
    
    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\u4e00-\u9fff\w\s,，;；、。！？""''()（）【】\\\[\\\]：:·]', '', text)
        
        return text.strip()
    
    def standardize_pinyin(self, pinyin: str) -> str:
        """标准化拼音格式"""
        if not pinyin:
            return ""
        
        # 转换为首字母大写格式
        words = pinyin.lower().split()
        return ' '.join(word.capitalize() for word in words)
    
    def parse_properties_and_taste(self, text: str) -> tuple:
        """解析性味信息，分离性质和味道"""
        if not text:
            return "", ""
        
        # 常见的性质关键词
        properties_keywords = ['寒', '凉', '平', '温', '热', '微寒', '微凉', '微温', '微热']
        # 常见的味道关键词
        taste_keywords = ['甘', '苦', '辛', '酸', '咸', '淡', '涩', '微甘', '微苦', '微辛']
        
        properties = []
        taste = []
        
        for keyword in properties_keywords:
            if keyword in text:
                properties.append(keyword)
        
        for keyword in taste_keywords:
            if keyword in text:
                taste.append(keyword)
        
        return '、'.join(properties), '、'.join(taste)
    
    def standardize_meridians(self, meridians: List[str]) -> List[str]:
        """标准化归经信息"""
        if not meridians:
            return []
        
        # 标准经络名称映射
        meridian_map = {
            '肺': '肺经', '大肠': '大肠经', '胃': '胃经', '脾': '脾经',
            '心': '心经', '小肠': '小肠经', '膀胱': '膀胱经', '肾': '肾经',
            '心包': '心包经', '三焦': '三焦经', '胆': '胆经', '肝': '肝经'
        }
        
        standardized = []
        for meridian in meridians:
            meridian = self.clean_text(meridian)
            
            # 如果已经是标准格式
            if meridian.endswith('经'):
                standardized.append(meridian)
            else:
                # 尝试匹配标准名称
                for key, value in meridian_map.items():
                    if key in meridian:
                        standardized.append(value)
                        break
                else:
                    # 如果没有匹配到，直接添加
                    if meridian:
                        standardized.append(meridian)
        
        return list(set(standardized))  # 去重
    
    def standardize_dosage(self, dosage: str) -> str:
        """标准化用法用量"""
        if not dosage:
            return ""
        
        dosage = self.clean_text(dosage)
        
        # 常见的用量格式标准化
        # 例如：3~9g -> 3-9g
        dosage = re.sub(r'(\d+)\s*[~～]\s*(\d+)', r'\1-\2', dosage)
        
        return dosage
    
    def generate_common_pairings(self, name: str, category: str) -> List[Dict[str, str]]:
        """根据药材名称和分类生成常见配伍（示例数据）"""
        # 这里可以根据实际的中药配伍知识生成
        # 目前返回模板数据
        return self.common_pairings_template.copy()
    
    def validate_herbal_data(self, data: Dict[str, Any]) -> bool:
        """验证中药材数据的完整性"""
        required_fields = ['id', 'name']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        return True
    
    def clean_image_urls(self, images: List[str]) -> List[str]:
        """清理和验证图片URL列表"""
        if not images or not isinstance(images, list):
            return []
        
        cleaned_images = []
        
        for img_url in images:
            if not img_url or not isinstance(img_url, str):
                continue
            
            # 清理URL
            img_url = img_url.strip()
            
            # 验证URL格式
            if self.is_valid_image_url(img_url):
                cleaned_images.append(img_url)
        
        # 去重
        return list(dict.fromkeys(cleaned_images))
    
    def is_valid_image_url(self, url: str) -> bool:
        """验证图片URL是否有效"""
        if not url:
            return False
        
        # 检查是否是有效的HTTP/HTTPS URL
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        
        # 检查是否有有效的图片扩展名
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
        url_lower = url.lower()
        
        # 移除查询参数来检查扩展名
        url_without_params = url_lower.split('?')[0]
        
        if any(url_without_params.endswith(ext) for ext in valid_extensions):
            return True
        
        # 如果URL包含图片相关的关键词，也认为可能是有效的
        if any(keyword in url_lower for keyword in ['image', 'img', 'photo', 'pic', 'thumb']):
            return True
        
        return False
    
    def process_single_herbal(self, herbal: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个中药材数据"""
        processed = herbal.copy()
        
        # 清理文本字段
        text_fields = ['name', 'pinyin', 'category', 'properties', 'taste', 
                      'dosage', 'usage', 'contraindications', 'description']
        
        for field in text_fields:
            if field in processed:
                processed[field] = self.clean_text(str(processed[field]))
        
        # 标准化拼音
        if 'pinyin' in processed:
            processed['pinyin'] = self.standardize_pinyin(processed['pinyin'])
        
        # 解析性味
        if 'properties' in processed and 'taste' in processed:
            combined_text = f"{processed['properties']} {processed['taste']}"
            properties, taste = self.parse_properties_and_taste(combined_text)
            if properties:
                processed['properties'] = properties
            if taste:
                processed['taste'] = taste
        
        # 标准化归经
        if 'meridians' in processed:
            processed['meridians'] = self.standardize_meridians(processed['meridians'])
        
        # 标准化列表字段
        list_fields = ['functions', 'indications']
        for field in list_fields:
            if field in processed and isinstance(processed[field], list):
                processed[field] = [self.clean_text(item) for item in processed[field] if item]
        
        # 标准化用法用量
        if 'dosage' in processed:
            processed['dosage'] = self.standardize_dosage(processed['dosage'])
        
        # 生成常见配伍（如果为空）
        if 'commonPairings' in processed and not processed['commonPairings']:
            processed['commonPairings'] = self.generate_common_pairings(
                processed.get('name', ''), 
                processed.get('category', '')
            )
        
        # 处理图片字段
        if 'images' in processed:
            processed['images'] = self.clean_image_urls(processed['images'])
        else:
            processed['images'] = []
        
        return processed
    
    def process_all_data(self, input_file: str, output_file: str) -> None:
        """处理所有数据"""
        print(f"开始处理数据文件: {input_file}")
        
        # 加载数据
        data = self.load_data(input_file)
        if not data:
            print("没有数据需要处理")
            return
        
        print(f"加载了 {len(data)} 条记录")
        
        # 处理每条记录
        processed_data = []
        for i, herbal in enumerate(data, 1):
            print(f"处理第 {i}/{len(data)} 条记录: {herbal.get('name', '未知')}")
            
            if self.validate_herbal_data(herbal):
                processed = self.process_single_herbal(herbal)
                processed_data.append(processed)
            else:
                print(f"  跳过无效记录: {herbal}")
        
        print(f"处理完成，有效记录 {len(processed_data)} 条")
        
        # 保存处理后的数据
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"处理后的数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    def generate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成数据统计信息"""
        if not data:
            return {}
        
        stats = {
            'total_count': len(data),
            'categories': {},
            'meridians': {},
            'properties': {},
            'taste': {},
            'completeness': {
                'has_pinyin': 0,
                'has_category': 0,
                'has_functions': 0,
                'has_indications': 0,
                'has_dosage': 0,
                'has_commonPairings': 0,
                'has_images': 0
            }
        }
        
        for herbal in data:
            # 统计分类
            category = herbal.get('category', '未分类')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # 统计归经
            meridians = herbal.get('meridians', [])
            for meridian in meridians:
                stats['meridians'][meridian] = stats['meridians'].get(meridian, 0) + 1
            
            # 统计性质
            properties = herbal.get('properties', '')
            if properties:
                stats['properties'][properties] = stats['properties'].get(properties, 0) + 1
            
            # 统计味道
            taste = herbal.get('taste', '')
            if taste:
                stats['taste'][taste] = stats['taste'].get(taste, 0) + 1
            
            # 统计完整性
            if herbal.get('pinyin'):
                stats['completeness']['has_pinyin'] += 1
            if herbal.get('category'):
                stats['completeness']['has_category'] += 1
            if herbal.get('functions'):
                stats['completeness']['has_functions'] += 1
            if herbal.get('indications'):
                stats['completeness']['has_indications'] += 1
            if herbal.get('dosage'):
                stats['completeness']['has_dosage'] += 1
            if herbal.get('commonPairings'):
                stats['completeness']['has_commonPairings'] += 1
            if herbal.get('images'):
                stats['completeness']['has_images'] += 1
        
        return stats

def main():
    """主函数"""
    processor = HerbalDataProcessor()
    
    # 处理爬取的数据
    input_file = 'herbal_medicine_data.json'
    output_file = 'herbal_medicine_data_processed.json'
    
    processor.process_all_data(input_file, output_file)
    
    # 生成统计信息
    processed_data = processor.load_data(output_file)
    if processed_data:
        stats = processor.generate_statistics(processed_data)
        
        # 保存统计信息
        with open('data_statistics.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print("\n=== 数据统计 ===")
        print(f"总记录数: {stats['total_count']}")
        print(f"分类统计: {len(stats['categories'])} 个分类")
        print(f"归经统计: {len(stats['meridians'])} 个归经")
        print(f"数据完整性统计已保存到 data_statistics.json")

if __name__ == "__main__":
    main() 