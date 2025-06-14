

import os
import json
from typing import Dict, List, Optional, Set, Tuple

class IODeltaForce:
    """
    读取和写入deltaforce.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "deltaforce.json")
        self.data = self._read_json(self.path)
        self.data = self.data if self.data is not None else {}
        self.data = (
            self.data
            if self.data != {}
            else {
                "deltaforce": {
                },
            }
        )
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}

    def _write_json(self, data: Dict) -> None:
        """
        写入json文件
        """
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}

    def put(self, key: str, value: Dict) -> None:
        """
        写入json文件中的数据
        """
        self.data[key] = value
        self._write_json(self.data)
        self.data = self._read_json(self.path)
        
        
class ROCollection:
    """
    读取collection.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "collection.json")
        self.data = self._read_json(self.path)
    
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}
    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}

class ROArmor:
    """
    读取armor.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "armor.json")
        self.data = self._read_json(self.path)
    
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}
    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}

class ROBag:
    """
    读取bag.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "bag.json")
        self.data = self._read_json(self.path)
    
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}
    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}
class ROChest:
    """
    读取 chest.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "chest.json")
        self.data = self._read_json(self.path)
    
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}
    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}
class ROHelmet:
    """
    读取 helmet.json文件
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "helmet.json")
        self.data = self._read_json(self.path)
    
    def _read_json(self, path) -> Dict:
        """
        读取json文件
        """
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                os.remove(path)
        return {}
    def get(self, key: str) -> Dict:
        """
        获取json文件中的数据
        """
        return self.data[key] if key in self.data else {}


import random  
    
class DrawItem:
    """
    跑刀模拟器(简化为开盲盒)
    """
    def __init__(self) -> None:
        self.items = []
        self.items.append(ROCollection().data)
        self.items.append(ROArmor().data)
        self.items.append(ROBag().data)
        self.items.append(ROChest().data)
        self.items.append(ROHelmet().data)
    
    def draw_item(self):        
        weight = random.random() * 100 
        
        if weight < 60:
            pool = [i for i in self.items if i['grade'] == 1]  # 白
        elif weight < 85:
            pool = [i for i in self.items if i['grade'] == 2]  # 绿
        elif weight < 95:
            pool = [i for i in self.items if i['grade'] == 3]  # 蓝
        elif weight < 99:
            pool = [i for i in self.items if i['grade'] == 4]  # 紫
        elif weight < 99.95:
            pool = [i for i in self.items if i['grade'] == 5]  # 金
        else:
            pool = [i for i in self.items if i['grade'] == 6]  # 红
            
        return random.choice(pool)
    
    # 十连保底机制（必出紫+）
    def ten_draw(self):
        results = []
        found_epic = False
        
        for i in range(10):
            item = self.draw_item()
            results.append(item)
            if item['grade'] >= 4:  # 紫或以上
                found_epic = True
        
        # 未出紫装时替换最后一件
        if not found_epic:
            epic_pool = [i for i in self.items if i['grade'] >= 4]
            results[-1] = random.choice(epic_pool)        
        return results