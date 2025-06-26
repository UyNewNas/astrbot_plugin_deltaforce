
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
                    async with self.session.get(self.url, params=params) as response:
                        if response.status == 200:
                            text = await response.text()
                            data = json.loads(text)
                            items = data.get("data", [])
                            for item in items:
                                price_date.append(item)                                               
                        else:
                            logger.error(f"请求失败: {response.status}")
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

from playwright.async_api  import async_playwright  
from typing import List, Dict, Optional, Callable, Union
import re
class AcgIceSJZApi:
    """
    acg ice 的api调用
    """
    def __init__(self):
        self.url = "https://www.acgice.com/sjz/v/zb_ss"
        self.p = async_playwright()
    
    async def jz_zb(self):
        captured_data = {}  # 存储各接口数据：{lv: 数据}
        async with self.p as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()            
            
            # 监听所有响应
            async def capture_api(response):
                url = response.url
                
                # 匹配目标接口模式
                if "/api/sjz/jz_zb?lv=" in url:
                    logger.info(f"捕获到响应: {url}")
                    lv = url.split("&")[0].split("=")[-1]  # 提取lv值
                    if lv in [str(i) for i in range(6)]:  # 仅捕获lv=0~5
                        captured_data[lv] = await response.json()  # 存储JSON数据
            page.on("response", capture_api)
            await page.goto(self.url)
            await page.wait_for_timeout(5000)
            await browser.close()
            
        for lv, data in captured_data.items():
            print(f"lv={lv} 数据: {data}")
        
        return captured_data