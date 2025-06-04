#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys

def main():
    """测试JSON文件编码和解析"""
    try:
        with open('zhongyoo_herbal_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"共找到 {len(data)} 条药材数据\n")
        
        # 显示所有药材名称
        print("所有药材列表:")
        for i, item in enumerate(data):
            print(f"{i+1}. {item['name']} ({item['pinyin']}) - {item['category']}")
            
        if len(data) > 0:
            # 显示第一个药材的详细信息
            print("\n第一个药材的详细信息:")
            item = data[0]
            print(f"ID: {item['id']}")
            print(f"名称: {item['name']}")
            print(f"拼音: {item['pinyin']}")
            print(f"分类: {item['category']}")
            print(f"味道归经: {item['taste']}")
            print(f"归经: {', '.join(item['meridians'])}")
            print(f"图片数量: {len(item['images'])}")
            print(f"源网址: {item['source_url']}")
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 