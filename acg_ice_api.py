'''
Author: slava
Date: 2025-06-27 08:51:44
LastEditTime: 2025-06-29 12:17:27
LastEditors: ch4nslava@gmail.com
Description: 

'''

from playwright.async_api  import async_playwright  
from typing import List, Dict, Optional, Callable, Union
import re
import asyncio

from astrbot.api import logger

class AcgIceSJZApi:
    """
    acg ice 的api调用
    """
    def __init__(self):
        self.url = {
            "zb_ss": "https://www.acgice.com/sjz/v/zb_ss",
            "index": "https://www.acgice.com/sjz/v/index",
            "item_list": "https://www.acgice.com/sjz/v/%s",
            
        }
        self.p = async_playwright()
    
    async def jz_zb(self):
        captured_data = {}
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
            await page.goto(self.url["zb_ss"])
            await page.wait_for_timeout(5000)
            await browser.close()
            
        for lv, data in captured_data.items():
            print(f"lv={lv} 数据: {data}")
        
        return captured_data
    
    async def map_pwd_daily(self):
        captured_data = {}
        async with self.p as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()            
            
            # 监听所有响应
            async def capture_api(response):
                url = response.url
                
                # 匹配目标接口模式
                if "/api/sjz/map_pwd" in url:
                    logger.info(f"捕获到响应: {url}")
                    captured_data["map_pwd"] = await response.json()  # 存储JSON数据
            page.on("response", capture_api)
            await page.goto(self.url["index"])
            await page.wait_for_timeout(5000)
            await browser.close()
        return captured_data.get("map_pwd", {})
    
    async def get_price(self):
        a_list = ["gun","helmet","armor","chest","bag","consume","collection","keys"]
        captured_data = {}
        [captured_data.setdefault(a, []) for a in a_list]  # 初始化字典
        async with self.p as p:
            browser = await p.chromium.launch(headless=True)
            async def goto_url(a):
                url = self.url["item_list"] % a
                context = await browser.new_context()
                page = await browser.new_page()
                # 监听所有响应
                async def capture_api(response):
                    url = response.url
                    # 匹配目标接口模式
                    if f"/api/sjz/item_list?a={a if a != 'keys' else ''}" in url:
                        logger.info(f"捕获到响应: {url}")
                        p = url.split("&p=")[-1].split("&")[0]
                        resp = await response.json()
                        resp_data = resp.get("data", [])
                        if resp_data:
                            captured_data[a].extend(resp_data)
                page.on("response", capture_api)
                await page.goto(url)
                await page.wait_for_timeout(1000)
                try:
                    while True:
                        await page.wait_for_selector("button.btn-next", state="visible", timeout=5000)
                        next_button = page.locator("button.btn-next")
                        if await next_button.is_disabled():
                            break
                        await next_button.click()
                        await page.wait_for_timeout(1000)
                except Exception as e:
                    logger.error(f"获取 {a} 数据时发生错误: {e}")
                await context.close()
            tasks = [goto_url(a) for a in a_list]
            await asyncio.gather(*tasks)
        return captured_data
        
                    
             