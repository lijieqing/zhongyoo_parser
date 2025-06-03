# 中药材数据爬取项目

## 项目描述
这个项目用于爬取中药材相关网站的数据，并将其转换为结构化的JSON格式。

**支持的数据源：**
1. **中医药网** (http://www.zhongyoo.com/gx/) - **推荐使用**
   - 数据结构完整，分类清晰
   - 支持按药材功效分类爬取
   - 三层结构：功效分类 → 药材列表 → 药材详情
   
2. 原始网站 (https://www.dayi.org.cn/) - 保留兼容
   - 原有爬虫功能

## 新功能特性 (中医药网爬虫)
1. **分层爬取**: 从功效分类页面开始，逐层深入获取数据
   - 功效分类页面: 获取所有药材分类 (如清虚热药、补气药等)
   - 分类药材列表: 获取特定分类下的所有药材
   - 药材详情页面: 获取单个药材的完整信息

2. **智能解析**: 自动提取药材的各种属性
   - 基本信息: 名称、拼音、分类
   - 药性信息: 性味、归经
   - 功效信息: 功效、主治
   - 用法信息: 用法用量、禁忌
   - 图片信息: 自动筛选相关图片

3. **灵活控制**: 支持多种爬取模式
   - 查看分类: 仅获取所有分类信息
   - 限量爬取: 指定爬取的分类数量和每个分类的药材数量
   - 完整爬取: 爬取所有分类的所有药材

4. **数据质量**: 
   - 重试机制: 网络异常时自动重试
   - 延时控制: 避免对服务器造成过大压力
   - 数据验证: 自动过滤无效数据

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始
```bash
py run.py
```

然后选择 "2. 中医药网 (zhongyoo.com)" 作为数据源。

### 测试爬虫功能
```bash
py test_zhongyoo_crawler.py
```

### 直接使用中医药网爬虫
```bash
py zhongyoo_crawler.py
```

## 网站结构说明

中医药网采用三层结构：

```
功效分类页面: http://www.zhongyoo.com/gx/
├── 清虚热药: http://www.zhongyoo.com/gx/qingxureyao/
│   ├── 银柴胡: http://www.zhongyoo.com/name/yinchaihu_2047.html
│   ├── 地骨皮: http://www.zhongyoo.com/name/digupi_xxx.html
│   └── ...
├── 补气药: http://www.zhongyoo.com/gx/buqiyao/
│   ├── 人参: http://www.zhongyoo.com/name/renshen_xxx.html
│   └── ...
└── ...
```

## 输出格式
数据将以JSON格式保存，包含以下字段：

### 基本信息
- `id`: 药材编号
- `name`: 药材名称
- `pinyin`: 拼音名称
- `category`: 药材分类
- `source_url`: 原始页面URL

### 药性信息
- `properties`: 性质
- `taste`: 性味
- `meridians`: 归经（数组）

### 功效信息
- `functions`: 功效（数组）
- `indications`: 主治（数组）

### 用法信息
- `dosage`: 用法用量
- `usage`: 使用方法
- `contraindications`: 禁忌

### 其他信息
- `commonPairings`: 常用配伍（数组）
- `description`: 描述
- `images`: 药材图片URL列表（数组）

## 示例数据格式
```json
{
  "id": 1,
  "name": "银柴胡",
  "pinyin": "yinchaihu",
  "category": "清虚热药",
  "properties": "微寒",
  "taste": "甘、微苦",
  "meridians": ["肝经", "胃经"],
  "functions": ["清虚热", "除疳热"],
  "indications": ["阴虚发热", "骨蒸劳热", "小儿疳积发热"],
  "dosage": "3-10g",
  "usage": "煎汤内服",
  "commonPairings": [],
  "contraindications": "外感风寒及血虚无热者忌服",
  "description": "银柴胡为石竹科植物银柴胡的干燥根...",
  "images": [
    "http://www.zhongyoo.com/uploads/image1.jpg",
    "http://www.zhongyoo.com/uploads/image2.jpg"
  ],
  "source_url": "http://www.zhongyoo.com/name/yinchaihu_2047.html"
}
```

## 文件说明

### 主要文件
- `zhongyoo_crawler.py`: 中医药网爬虫主文件
- `herbal_crawler.py`: 原始爬虫文件 (兼容保留)
- `run.py`: 统一运行入口
- `test_zhongyoo_crawler.py`: 爬虫功能测试脚本

### 数据处理
- `data_processor.py`: 数据后处理脚本
- `website_analyzer.py`: 网站结构分析工具

### 输出文件
- `zhongyoo_herbal_data.json`: 中医药网爬取的原始数据
- `zhongyoo_herbal_data_processed.json`: 处理后的数据
- `zhongyoo_crawler.log`: 爬虫运行日志

## 使用建议

1. **首次使用**: 建议先运行测试脚本验证功能
2. **小规模测试**: 先爬取少量数据验证效果
3. **大规模爬取**: 确认无误后进行完整爬取
4. **遵守规范**: 请合理设置爬取间隔，避免对服务器造成压力

## 注意事项
- 请遵守网站的robots.txt规则
- 建议设置合理的请求间隔，避免对服务器造成过大负担
- 图片URL仅作为参考，实际使用时请确认图片的版权和使用权限
- 仅用于学习和研究目的
- 爬取大量数据时请在网络状况良好的环境下进行

## 故障排除

### 常见问题
1. **网络连接失败**: 检查网络连接和代理设置
2. **编码问题**: 确保系统支持UTF-8编码
3. **依赖包问题**: 运行 `pip install -r requirements.txt` 重新安装依赖

### 测试步骤
1. 运行 `py test_zhongyoo_crawler.py` 进行功能测试
2. 检查日志文件 `zhongyoo_crawler.log` 查看详细错误信息
3. 如果分类获取失败，可能需要检查网站结构是否发生变化

## 许可证
仅用于学习和研究目的。请遵守相关网站的使用条款和robots.txt规则。 