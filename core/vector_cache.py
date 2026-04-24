import os
import sys
import hashlib
import json
import numpy as np


class VectorCache:
    def __init__(self, cache_dir=None):
        if cache_dir:
            self._cache_dir = cache_dir
        else:
            self._cache_dir = self._get_default_cache_dir()
    
    def _get_default_cache_dir(self):
        if getattr(sys, 'frozen', False):
            project_root = sys._MEIPASS
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(project_root, 'cache')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir
    
    def _get_folder_hash(self, folder_path):
        return hashlib.md5(folder_path.encode('utf-8')).hexdigest()
    
    def _get_messages_hash(self, messages):
        msg_str = '|||'.join(messages)
        return hashlib.md5(msg_str.encode('utf-8')).hexdigest()
    
    def load(self, folder_path, messages):
        folder_hash = self._get_folder_hash(folder_path)
        messages_hash = self._get_messages_hash(messages)
        
        metadata_file = os.path.join(self._cache_dir, f'{folder_hash}_meta.json')
        vectors_file = os.path.join(self._cache_dir, f'{folder_hash}_vectors.npy')
        
        if not os.path.exists(metadata_file) or not os.path.exists(vectors_file):
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if metadata.get('messages_hash') != messages_hash:
                return None
            
            vectors = np.load(vectors_file)
            return vectors
        except Exception:
            return None
    
    def save(self, folder_path, messages, vectors):
        folder_hash = self._get_folder_hash(folder_path)
        messages_hash = self._get_messages_hash(messages)
        
        metadata_file = os.path.join(self._cache_dir, f'{folder_hash}_meta.json')
        vectors_file = os.path.join(self._cache_dir, f'{folder_hash}_vectors.npy')
        
        try:
            metadata = {
                'folder_path': folder_path,
                'messages_hash': messages_hash,
                'message_count': len(messages)
            }
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False)
            
            np.save(vectors_file, vectors)
            return True
        except Exception:
            return False
    
    def clear(self, folder_path=None):
        if folder_path:
            folder_hash = self._get_folder_hash(folder_path)
            metadata_file = os.path.join(self._cache_dir, f'{folder_hash}_meta.json')
            vectors_file = os.path.join(self._cache_dir, f'{folder_hash}_vectors.npy')
            for f in [metadata_file, vectors_file]:
                if os.path.exists(f):
                    os.remove(f)
        else:
            for f in os.listdir(self._cache_dir):
                if f.endswith('_meta.json') or f.endswith('_vectors.npy'):
                    os.remove(os.path.join(self._cache_dir, f))
