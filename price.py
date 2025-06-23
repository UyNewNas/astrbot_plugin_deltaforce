
import aiohttp
import os
import json
from typing import Dict, List, Optional, Set, Tuple
import time
import datetime
from astrbot.api import logger
class IOPrice:
    """
    读取和写入price.json文件
    {
        "20250101": [<item1>, <item2>, ...]
    }
    """
    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "price.json")
        self.data = self._read_json(self.path)
        self.data = self.data if self.data is not None else {}
        
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

    def put(self, key: str, value: Dict|List) -> None:
        """
        写入json文件中的数据
        """
        self.data[key] = value
        self._write_json(self.data)
        self.data = self._read_json(self.path)
        


class DeltaForcePrice:
    
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.url = "https://tool.zxfps.com/api/sjz/item_list"
        self.io_price = IOPrice()
        now = datetime.datetime.now()
        date = f"{now.year}{now.month:02d}{now.day:02d}" 
        
        
    def _new_io(self):
        """
        创建新的IOPrice实例
        """
        self.io_price = IOPrice()
        
        
    async def get_all_items_price(self):
        """
        获取今天所有物品的价格
        """
        self._new_io()
        now = datetime.datetime.now()
        date = f"{now.year}{now.month:02d}{now.day:02d}"
        price_date = []
        a_list = ["gun", "helmet", "chest", "bag", "armor","consume","collection",""]
        for a in a_list:
            params = {
                "a": a,            
            }
            headers = {
                "Content-Type": "application/json",
            }
            logger.info(f"## 1 ##")
            async with self.session.get(self.url, params=params, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    data = json.loads(text)
                    count = data.get("count", 0)
                else:
                    logger.error(f"请求失败: {response.status}")
                    return
                # 每页10个, 循环
                for page in range(1, (count // 10) + 2):
                    params = {
                        "a": a,
                        "p": page,
                    }
                    logger.info(f"## 2 ## {params}")
                    async with self.session.get(self.url, params=params) as response:
                        if response.status == 200:
                            text = await response.text()
                            data = json.loads(text)
                            items = data.get("data", [])
                            for item in items:
                                price_date.append(item)                                               
                        else:
                            logger.error(f"请求失败: {response.status}")
            logger.debug("## 3 ##" + str(date) + str(price_date))
            self.io_price.put(date, price_date)                       
           
    async def get_price(self, item_name: str) -> int:

        """
        获取单个物品的价格
        """
        self._new_io()
        now = datetime.datetime.now()
        date = f"{now.year}{now.month:02d}{now.day:02d}"
        if date not in self.io_price.data:
            await self.get_all_items_price()      
        items = self.io_price.get(date)
        for item in items:
            if item["name"] == item_name:
                return item.get("price", 0)
        return 0
