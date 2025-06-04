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
        text = re.sub(r'[^\u4e00-\u9fff\w\s,，;；、。！？""''()（）【】\[\]:：·]', '', text)
        
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
    
    def clean_prescriptions(self, prescriptions: List[str]) -> List[str]:
        """清理和标准化配伍药方"""
        if not prescriptions or not isinstance(prescriptions, list):
            return []
        
        cleaned = []
        for prescription in prescriptions:
            if not prescription or not isinstance(prescription, str):
                continue
            
            # 清理文本
            prescription = self.clean_text(prescription)
            
            if prescription:
                cleaned.append(prescription)
        
        return cleaned
    
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
        text_fields = ['name', 'pinyin', 'category', 'taste', 
                      'contraindications', 'morphology', 'medicinal_part', 
                      'distribution', 'processing', 'characteristics', 
                      'pharmacology', 'main_components', 'clinical_application']
        
        for field in text_fields:
            if field in processed:
                processed[field] = self.clean_text(str(processed[field]))
        
        # 标准化拼音
        if 'pinyin' in processed:
            processed['pinyin'] = self.standardize_pinyin(processed['pinyin'])
        
        # 标准化归经
        if 'meridians' in processed:
            processed['meridians'] = self.standardize_meridians(processed['meridians'])
        
        # 清理和标准化配伍药方
        if 'prescriptions' in processed:
            processed['prescriptions'] = self.clean_prescriptions(processed['prescriptions'])
        
        # 清理图片URL
        if 'images' in processed:
            processed['images'] = self.clean_image_urls(processed['images'])
        
        return processed
    
    def process_all_data(self, input_file: str, output_file: str) -> None:
        """处理所有中药材数据并保存"""
        print(f"开始处理数据文件: {input_file}")
        data = self.load_data(input_file)
        
        if not data:
            print("无数据需要处理")
            return
        
        print(f"成功加载 {len(data)} 条中药材记录")
        
        # 处理每条记录
        processed_data = []
        for herbal in data:
            if self.validate_herbal_data(herbal):
                processed_herbal = self.process_single_herbal(herbal)
                processed_data.append(processed_herbal)
            else:
                print(f"警告: 跳过无效数据记录 id={herbal.get('id', 'unknown')}, name={herbal.get('name', 'unknown')}")
        
        # 保存处理后的数据
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"成功处理并保存 {len(processed_data)} 条中药材记录到 {output_file}")
            
            # 生成统计信息
            stats = self.generate_statistics(processed_data)
            stats_file = output_file.replace('.json', '_stats.json')
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"统计信息已保存到 {stats_file}")
            
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    def generate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成数据统计信息"""
        stats = {
            "total_count": len(data),
            "categories": {},
            "meridians": {},
            "image_coverage": 0,
            "fields_coverage": {}
        }
        
        # 字段覆盖率统计
        fields = ['name', 'pinyin', 'category', 'taste', 'meridians', 
                 'morphology', 'medicinal_part', 'distribution', 'processing', 
                 'characteristics', 'pharmacology', 'main_components', 
                 'clinical_application', 'prescriptions', 'contraindications', 'images']
        
        field_counts = {field: 0 for field in fields}
        
        for herb in data:
            # 统计分类
            category = herb.get('category', '')
            if category:
                if category in stats['categories']:
                    stats['categories'][category] += 1
                else:
                    stats['categories'][category] = 1
            
            # 统计归经
            for meridian in herb.get('meridians', []):
                if meridian in stats['meridians']:
                    stats['meridians'][meridian] += 1
                else:
                    stats['meridians'][meridian] = 1
            
            # 统计图片覆盖
            if herb.get('images', []):
                stats['image_coverage'] += 1
            
            # 统计字段覆盖
            for field in fields:
                if field in herb:
                    value = herb[field]
                    if isinstance(value, list) and value:
                        field_counts[field] += 1
                    elif isinstance(value, str) and value:
                        field_counts[field] += 1
                    elif value:  # 其他非空值
                        field_counts[field] += 1
        
        # 计算覆盖率
        for field, count in field_counts.items():
            stats['fields_coverage'][field] = {
                'count': count,
                'percentage': round(count / len(data) * 100, 2) if data else 0
            }
        
        # 图片覆盖率
        stats['image_coverage'] = {
            'count': stats['image_coverage'],
            'percentage': round(stats['image_coverage'] / len(data) * 100, 2) if data else 0
        }
        
        return stats

def main():
    """主函数"""
    print("=== 中药材数据处理工具 ===")
    
    processor = HerbalDataProcessor()
    
    input_file = input("请输入要处理的数据文件路径 (默认: zhongyoo_herbal_data.json): ").strip()
    if not input_file:
        input_file = "zhongyoo_herbal_data.json"
    
    output_file = input("请输入处理后的输出文件路径 (默认: processed_herbal_data.json): ").strip()
    if not output_file:
        output_file = "processed_herbal_data.json"
    
    processor.process_all_data(input_file, output_file)

if __name__ == "__main__":
    main() 