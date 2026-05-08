# 微信流水记录导出工具

## 环境准备

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 打包成exe：
```bash
flet pack main.py -n wechat_flet --add-data "core;core" --add-data "models;models" --onedir

// 如在其他电脑上打包报错（ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1020)），需要添加certifi证书
flet pack main.py -n wechat_flet --add-data "core;core" --add-data "models;models" --add-data "E:\pl\program\laragon\bin\python\python-3.13\Lib\site-packages\certifi;certifi" --onedir
```

3. 打包完成后，exe文件在 `dist` 文件夹中

## 使用方法

### 搜索微信聊天记录：
1. 双击运行 `wechat_flet.exe`
2. 点击"浏览"选择HTML文件夹
3. 点击"搜索"输入搜索内容

### 导出流水记录：
1. 双击运行 `wechat_flet.exe`
2. 点击"浏览"选择HTML文件夹
3. 点击"导出流水记录"
4. 选择保存路径后开始导出
5. 导出完成后自动打开所在文件夹

## 技术细节

1. 该工具基于微信聊天记录的HTML文件进行解析，不依赖于微信的API。
2. 支持搜索微信聊天记录，用户可以根据搜索内容进行筛选。
3. 导出流水记录时，会自动将搜索到的记录导出到指定路径。
4. 支持关键字搜索和语义搜索。
5. 语义搜索使用模型为 `paraphrase-multilingual-MiniLM-L12-v2`。
6. 初次搜索会将所有消息编码为向量(速度较慢)，后续搜索会根据向量进行相似度计算。
7. 初次搜索后，会缓存向量，后续搜索会直接缓存中读取向量(速度极快)。
