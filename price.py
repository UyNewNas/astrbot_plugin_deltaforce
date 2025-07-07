import aiohttp
import os
import json
from typing import Dict, List, Optional, Set, Tuple
import time
import datetime
from astrbot.api import logger

from .acg_ice_api import AcgIceSJZApi
from .data_deltaforce import IOItems
from data.plugins.astrbot_plugin_deltaforce import acg_ice_api

def check_file(path, default_txt='{}'):
    if not os.path.exists(path):
        with open(path,'w') as f:
            f.write(default_txt)
        logger.info(f"文件{path}已创建")
            
            

class IOPrice:
    """
    读取和写入price.json文件
    {
        "20250101": [<item1>, <item2>, ...]
    }
    """

    def __init__(self) -> None:
        self.path = os.path.join(os.path.dirname(__file__), "price.json")
        check_file(self.path)
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

    def put(self, key: str, value: Dict | List) -> None:
        """
        写入json文件中的数据
        """
        self.data[key] = value
        self._write_json(self.data)
        self.data = self._read_json(self.path)


class DeltaForcePrice:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        # self.url = "https://tool.zxfps.com/api/sjz/item_list"
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
        date = f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"
        acg_ice_api = AcgIceSJZApi()
        item_list = await acg_ice_api.get_price()
        """
        item_list = {
            "gun": [
                {
                    "name": "",
                    "grade": 0,
                    "price": 150821,
                    "pic": "https://playerhub.df.qq.com/playerhub/60004/object/18010000040.png"
                }
            ],
        }
        """
        if not item_list:
            logger.error("获取物品价格失败，item_list 为空")
            return {}
        if date not in self.io_price.data:
            self.io_price.data[date] = {}
        for item_type, items in item_list.items():
            if item_type not in self.io_price.data[date]:
                self.io_price.data[date][item_type] = []
            for item in items:
                item_data = {
                    "name": item.get("name", ""),
                    "grade": item.get("grade", 0),
                    "price": int(item.get("current_price", "0").replace(",", "")),
                    "pic": item.get("pic", "")
                }
                self.io_price.data[date][item_type].append(item_data)
        self.io_price.put(date, self.io_price.data[date])
        logger.info(
            f"获取物品价格成功，日期: {date}, 物品数量: {sum(len(v) for v in self.io_price.data[date].values())}"
        )
        # 更新物品
        for item_type, item_list in self.io_price.data[date].items():
            io_items = IOItems(item_type)
            io_items._write_json(item_list)
        
        
        return self.io_price.data[date]

    @staticmethod
    def query_in_dict(dict_item: Dict[str, List[Dict]], item_name) -> Dict:
        """
        遍历物品的静态方法
        """
        for item_type, item_list in dict_item.items():
            for item in item_list:
                if isinstance(item, dict) and "name" in item:
                    if item["name"] == item_name:
                        return item
        return {}

    async def get_price(self, item_name: str) -> int:
        """
        获取单个物品的价格
        """
        self._new_io()
        now = datetime.datetime.now()
        date = f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"
        if date in self.io_price.data:
            item = self.query_in_dict(self.io_price.data[date], item_name)
            return item.get("price", 0)
        else:
            self.io_price.data[date] = {}
        # 如果没有找到，尝试获取今天所有物品的价格
        all_items = await self.get_all_items_price()
        if not all_items:
            logger.error("获取今天所有物品的价格失败")
            return 0
        # 遍历所有物品，查找匹配的物品
        for item_type, items in all_items.items():
            for item in items:
                if item["name"] == item_name:
                    # 找到匹配的物品，返回价格
                    self.io_price.data[date][item_name] = item
                    logger.info(
                        f"找到 {item_type} 物品 {item_name} 的价格: {item['price']}"
                    )
                    return item["price"]
        # 如果没有找到，返回0
        logger.warning(f"未找到物品 {item_name} 的价格")
        return 0
