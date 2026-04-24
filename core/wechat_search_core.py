import os
import re
import io
import time
import sys
import hashlib
import json
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from core.wechat_parser_core import WechatParserCore
from core.vector_cache import VectorCache

class WechatSearchCore:
    def __init__(self):
        self.parser_core = WechatParserCore()
        self.model = None
        self._page_cache = {}
        self.vector_cache = VectorCache()
    
    def load_model(self):
        if self.model is None:
            import sys
            if sys.stdout is None:
                sys.stdout = io.StringIO()
            if sys.stderr is None:
                sys.stderr = io.StringIO()
            if getattr(sys, 'frozen', False):
                project_root = sys._MEIPASS
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, 'models', 'paraphrase-multilingual-MiniLM-L12-v2')
            try:
                if os.path.exists(model_path):
                    self.model = SentenceTransformer(model_path)
                else:
                    self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("错误", f"加载模型失败:\n{e}")
                raise
    
    def get_page_soup(self, page_path):
        if page_path in self._page_cache:
            return self._page_cache[page_path]
        
        if not os.path.exists(page_path):
            return None
        
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        self._page_cache[page_path] = soup
        return soup
    
    def clear_page_cache(self):
        self._page_cache.clear()
    
    def get_page_boxes(self, page_path, record_id):
        soup = self.get_page_soup(page_path)
        
        if not soup:
            return None
        
        target_section = None
        if record_id:
            target_h5 = soup.find('h5', id=record_id)
            if target_h5:
                next_div = target_h5.find_next_sibling('div')
                if next_div:
                    target_section = next_div.find('div', class_='conversationBox')
        
        if not target_section:
            return None
        
        left_boxes = target_section.select('ul > li > div.leftBox, ul > li > div.rightBox')
        return left_boxes

    @staticmethod
    def find_all_message_links(navbar_path):
        with open(navbar_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        message_records = []
        
        wechat_a = None
        for a in soup.find_all('a', class_='jstree-anchor'):
            text = a.get_text().strip()
            if text.startswith('微信') and '（' in text and '/' in text:
                wechat_a = a
                break
        
        if not wechat_a:
            return message_records
        
        wechat_href = wechat_a.get('href', '')
        wechat_id = int(wechat_href.split('#')[1].split('-')[0]) if '#' in wechat_href else 0
        
        target_a = None
        max_count = 0
        for a in soup.find_all('a', class_='jstree-anchor'):
            text = a.get_text().strip()
            if '好友消息' in text and not text.startswith('公众号') and not text.startswith('企业微信'):
                href = a.get('href', '')
                if '#' in href:
                    msg_id = int(href.split('#')[1].split('-')[0])
                    count = int(a.get('count', 0))
                    
                    if msg_id > wechat_id and count > max_count:
                        max_count = count
                        target_a = a
        
        if not target_a:
            return message_records
        
        buddy_ul = target_a.find_next_sibling('ul')
        if not buddy_ul:
            return message_records
        
        for li in buddy_ul.find_all('li', recursive=False):
            a = li.find('a', class_='jstree-anchor')
            if a:
                href = a.get('href', '')
                if href:
                    parts = href.split('#')
                    page = parts[0]
                    record_id = parts[1] if len(parts) > 1 else ''
                    
                    name_text = a.get_text().strip()
                    name_text = name_text.replace('（', '(').replace('）', ')')
                    name_text = name_text.split('(')[0].strip()
                    
                    message_records.append({
                        'name': name_text,
                        'page': page,
                        'id': record_id
                    })
        
        return message_records
    
    def search_in_page_keyword(self, page_path, record_id, keyword, progress_callback=None):
        left_boxes = self.get_page_boxes(page_path, record_id)
        
        if not left_boxes:
            return []
        
        return self.get_page_messages(keyword, left_boxes, record_id, page_path)

    def get_page_messages(self, keyword, left_boxes, record_id, page_path):
        keyword_lower = keyword.lower()
        
        results = []
        
        for box in left_boxes:
            box_text = box.get_text()
            
            if keyword_lower in box_text.lower():
                message = self.format_message(box, record_id, page_path)
               
                if message:
                    results.append(message)

        return results
    
    def format_message(self, box, record_id, page_path):
        box_text = box.get_text()

        message = {}
        sender_elem = box.find('p', class_='ellipsis')
        sender = sender_elem.get('title', '').strip() if sender_elem else ''
        
        time_span = box.find('span', style=re.compile(r'margin-left:\s*15px'))
        send_time = time_span.get_text(strip=True) if time_span else ''
        
        text_div = box.find('div', class_='text')
        message_text = text_div.get_text(strip=True) if text_div else ''
        
        msg_id = box.get('id', '')

        message = {
            'content': box_text.strip(),
            'sender': sender,
            'send_time': send_time,
            'message': message_text,
            'msg_id': msg_id,
            'record_id': record_id,
            'page': page_path
        }

        return message


    def search_in_page_semantic(self, page_path, record_id, query_vec, threshold=0.3, top_k=10, progress_callback=None):
        results = []
        
        left_boxes = self.get_page_boxes(page_path, record_id)
        
        if not left_boxes:
            return results
        
        messages = []
        for box in left_boxes:
            message = self.format_message(box, record_id, page_path)
            if message:
                messages.append(message)
        
        if not messages:
            return results
        
        message_texts = [m['content'] for m in messages]
        
        t2 = time.time()        
        message_vecs = self.model.encode(message_texts)
        t3 = time.time()
        print(f"  模型编码耗时: {t3 - t2:.3f}s")
        
        similarities = cosine_similarity(query_vec, message_vecs)[0]
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        for idx in top_indices:
            if similarities[idx] >= threshold:
                msg = messages[idx]
                results.append({
                    'content': msg['content'],
                    'sender': msg['sender'],
                    'send_time': msg['send_time'],
                    'message': msg['message'],
                    'msg_id': msg['msg_id'],
                    'record_id': record_id,
                    'page': page_path,
                    'score': float(similarities[idx])
                })
        
        return results
    
    def search_folder(self, folder_path, keyword, search_mode='keyword', progress_callback=None):
        folder_path = os.path.abspath(folder_path)
        
        navbar_path = os.path.join(folder_path, 'navbar.html')
        if not os.path.exists(navbar_path):
            return False, "navbar.html not found"
        
        if progress_callback:
            progress_callback("正在搜索...", 0)
        
        if search_mode == 'semantic':
            self.load_model()
            if progress_callback:
                progress_callback("模型加载完成，开始收集消息...", 5)
        
        message_links = self.find_all_message_links(navbar_path)
        
        all_results = []
        total = len(message_links)

        if search_mode == 'semantic':
            # 预先收集所有消息文本和元数据
            all_messages = []
            message_metadata = []
            
            for idx, item in enumerate(message_links):
                page_path = os.path.join(folder_path, item['page'])
                left_boxes = self.get_page_boxes(page_path, item['id'])
                if left_boxes:
                    for box in left_boxes:
                        message = self.format_message(box, item['id'], item['page'])
                        if message and message['message'].strip():
                            all_messages.append(message['content'])
                            message_metadata.append({
                                'chat_name': item['name'],
                                'page': item['page'],
                                'record_id': item['id'],
                                'message': message
                            })
                
                if progress_callback:
                    progress_callback(f"正在收集消息 {item['page']} ({idx+1}/{total})...", int((idx + 1) / total * 40) + 5)
            
            if not all_messages:
                return True, []
            
            if progress_callback:
                progress_callback("正在加载向量缓存...", 45)
            
            cached_vecs = self.vector_cache.load(folder_path, all_messages)
            if cached_vecs is not None:
                message_vecs = cached_vecs
                print(f"从缓存加载向量耗时: 0.001s (共 {len(all_messages)} 条消息)")
            else:
                if progress_callback:
                    progress_callback("正在编码消息向量...(首次编码较慢,请耐心等待)", 50)
                t_start = time.time()
                message_vecs = self.model.encode(all_messages, batch_size=64)
                t_end = time.time()
                print(f"批量编码耗时: {t_end - t_start:.3f}s")
                self.vector_cache.save(folder_path, all_messages, message_vecs)
                print(f"向量已保存到缓存 (共 {len(all_messages)} 条消息)")
            
            # 编码查询向量
            query_vec = self.model.encode([keyword])
            
            # 计算相似度
            if progress_callback:
                progress_callback("正在计算相似度...", 60)
            similarities = cosine_similarity(query_vec, message_vecs)[0]
            # similarities = message_vecs @ query_vec
            
            # 收集结果
            threshold = 0.4
            top_k = 50  # 总共取前50个
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            for idx in top_indices:
                if similarities[idx] >= threshold:
                    meta = message_metadata[idx]
                    msg = meta['message']
                    msg_id = msg.get('msg_id', '')
                    full_path = f"{meta['page']}#{meta['record_id']}"
                    if msg_id:
                        full_path = f"{meta['page']}#{meta['record_id']}--{msg_id}"
                    
                    all_results.append({
                        'chat_name': meta['chat_name'],
                        'page': meta['page'],
                        'content': msg['content'],
                        'sender': msg.get('sender', ''),
                        'send_time': msg.get('send_time', ''),
                        'message': msg['message'],
                        'path': full_path,
                        'score': float(similarities[idx])
                    })
            
            all_results.sort(key=lambda x: x['score'], reverse=True)
        
        else:  # keyword search
            for idx, item in enumerate(message_links):
                page_path = os.path.join(folder_path, item['page'])
                
                if progress_callback:
                    progress_callback(f"正在搜索 {item['page']} ({idx+1}/{total})...", int((idx + 1) / total * 90))
                
                results = self.search_in_page_keyword(page_path, item['id'], keyword)
                
                for result in results:
                    msg_id = result.get('msg_id', '')
                    full_path = f"{item['page']}#{item['id']}"
                    if msg_id:
                        full_path = f"{item['page']}#{item['id']}--{msg_id}"
                    
                    message = result.get('message', '').strip()
                    if not message:
                        continue
                    
                    all_results.append({
                        'chat_name': item['name'],
                        'page': item['page'],
                        'content': result['content'],
                        'sender': result.get('sender', ''),
                        'send_time': result.get('send_time', ''),
                        'message': message,
                        'path': full_path,
                        'score': result.get('score', 1.0)
                    })
        
        return True, all_results
