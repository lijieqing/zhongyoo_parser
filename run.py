#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中药材爬虫项目主运行脚本
"""

import os
import sys
from zhongyoo_crawler import ZhongYooHerbalCrawler
from data_processor import HerbalDataProcessor

def main():
    """主函数"""
    print("=== 中药材数据爬取项目 ===")
    print("🌿 中医药网 (zhongyoo.com) 专用爬虫")
    print()
    print("选择操作:")
    print("1. 🚀 开始爬取数据")
    print("2. 🧪 测试爬虫功能")
    print("3. 📊 处理已有数据")
    print("4. 🔄 完整流程（爬取+处理）")
    
    choice = input("请选择操作 (1-4): ").strip()
    
    if choice == "1":
        print("\n🚀 启动中医药网爬虫...")
        run_zhongyoo_crawler()
        
    elif choice == "2":
        print("\n🧪 测试爬虫功能...")
        test_crawler()
        
    elif choice == "3":
        print("\n📊 开始处理数据...")
        process_existing_data()
            
    elif choice == "4":
        print("\n🔄 开始完整流程...")
        run_complete_workflow()
            
    else:
        print("❌ 无效的选择，请重新运行程序")

def test_crawler():
    """测试爬虫功能"""
    print("选择测试类型:")
    print("1. 快速功能测试")
    print("2. 完整功能测试")
    print("3. 查看药材列表页")
    
    choice = input("请选择测试类型 (1-3): ").strip()
    
    if choice == "1":
        print("🏃‍♂️ 运行快速测试...")
        os.system("py quick_test.py")
    elif choice == "2":
        print("🔍 运行完整测试...")
        os.system("py test_zhongyoo_crawler.py")
    elif choice == "3":
        print("📋 查看药材列表页...")
        crawler = ZhongYooHerbalCrawler()
        herbs, total_pages = crawler.parse_name_list_page(1)
        print(f"\n找到 {total_pages} 个页面，第1页有 {len(herbs)} 个药材:")
        for i, herb in enumerate(herbs[:10], 1):  # 只显示前10个
            print(f"{i}. {herb['name']} - {herb['url']}")
    else:
        print("❌ 无效选择")

def run_zhongyoo_crawler():
    """运行中医药网爬虫"""
    crawler = ZhongYooHerbalCrawler()
    
    print("🎯 中医药网数据爬取选项:")
    print("1. 小规模测试 (1页，3个药材)")
    print("2. 中等规模爬取 (3页，每页5个药材)")
    print("3. 自定义爬取数量")
    print("4. 爬取所有数据 ⚠️")
    
    sub_choice = input("请选择爬取模式 (1-4): ").strip()
    
    if sub_choice == "1":
        # 小规模测试
        print("🧪 开始小规模测试爬取...")
        try:
            crawler.crawl_all_pages(max_pages=1, max_herbs_per_page=3)
            print("✅ 小规模测试完成！")
        except KeyboardInterrupt:
            print("⏹️ 用户中断爬取")
            crawler.save_data()
        except Exception as e:
            print(f"❌ 爬取过程中出现错误: {e}")
            crawler.save_data()
    
    elif sub_choice == "2":
        # 中等规模爬取
        print("🚀 开始中等规模爬取...")
        try:
            crawler.crawl_all_pages(max_pages=3, max_herbs_per_page=5)
            print("✅ 中等规模爬取完成！")
        except KeyboardInterrupt:
            print("⏹️ 用户中断爬取")
            crawler.save_data()
        except Exception as e:
            print(f"❌ 爬取过程中出现错误: {e}")
            crawler.save_data()
    
    elif sub_choice == "3":
        # 自定义爬取
        max_pages = input("请输入要爬取的页面数量（默认3页）: ").strip()
        max_herbs = input("请输入每个页面爬取的药材数量（默认5个）: ").strip()
        
        try:
            max_pages = int(max_pages) if max_pages else 3
            max_herbs = int(max_herbs) if max_herbs else 5
        except ValueError:
            max_pages, max_herbs = 3, 5
        
        print(f"🎯 开始自定义爬取 ({max_pages}页，每页{max_herbs}个药材)...")
        try:
            crawler.crawl_all_pages(max_pages=max_pages, 
                                   max_herbs_per_page=max_herbs)
            print("✅ 自定义爬取完成！")
        except KeyboardInterrupt:
            print("⏹️ 用户中断爬取")
            crawler.save_data()
        except Exception as e:
            print(f"❌ 爬取过程中出现错误: {e}")
            crawler.save_data()
    
    elif sub_choice == "4":
        # 爬取所有数据
        confirm = input("⚠️  这将爬取所有页面的所有药材数据（约45页，899个药材），可能需要很长时间。确认继续？(y/N): ").strip().lower()
        if confirm == 'y':
            print("🌍 开始完整数据爬取...")
            try:
                crawler.crawl_all_pages()
                print("✅ 完整数据爬取完成！")
            except KeyboardInterrupt:
                print("⏹️ 用户中断爬取")
                crawler.save_data()
            except Exception as e:
                print(f"❌ 爬取过程中出现错误: {e}")
                crawler.save_data()
        else:
            print("❌ 操作已取消")
    
    else:
        print("❌ 无效的选择")

def process_existing_data():
    """处理已有数据"""
    processor = HerbalDataProcessor()
    
    # 只检查中医药网数据文件
    data_file = 'zhongyoo_herbal_data.json'
    
    if not os.path.exists(data_file):
        print(f"❌ 错误：找不到数据文件 {data_file}")
        print("请先运行爬虫获取数据")
        return
    
    print(f"📁 找到数据文件: {data_file}")
    
    # 生成输出文件名
    base_name = data_file.replace('.json', '')
    output_file = f'{base_name}_processed.json'
    
    processor.process_all_data(data_file, output_file)
    print("✅ 数据处理完成！")

def run_complete_workflow():
    """运行完整工作流程"""
    print("🔄 完整流程将进行数据爬取和处理")
    
    # 设置爬取参数
    max_pages = input("请输入要爬取的页面数量（默认3页）: ").strip()
    max_herbs = input("请输入每个页面爬取的药材数量（默认5个）: ").strip()
    
    try:
        max_pages = int(max_pages) if max_pages else 3
        max_herbs = int(max_herbs) if max_herbs else 5
    except ValueError:
        max_pages, max_herbs = 3, 5
        
    # 1. 爬取数据
    print("\n🚀 步骤1: 爬取数据...")
    crawler = ZhongYooHerbalCrawler()
    input_file = 'zhongyoo_herbal_data.json'
    
    try:
        crawler.crawl_all_pages(max_pages=max_pages, 
                               max_herbs_per_page=max_herbs)
    except KeyboardInterrupt:
        print("⏹️ 用户中断爬取")
        crawler.save_data()
    except Exception as e:
        print(f"❌ 爬取过程中出现错误: {e}")
        crawler.save_data()
    
    # 2. 处理数据
    print("\n📊 步骤2: 处理数据...")
    processor = HerbalDataProcessor()
    
    if os.path.exists(input_file):
        base_name = input_file.replace('.json', '')
        output_file = f'{base_name}_processed.json'
        processor.process_all_data(input_file, output_file)
        print("✅ 完整流程执行完成！")
    else:
        print("⚠️  警告：没有找到爬取的数据文件")

if __name__ == "__main__":
    main() 