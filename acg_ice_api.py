"""
Author: slava
Date: 2025-06-27 08:51:44
LastEditTime: 2025-06-30 12:39:14
LastEditors: ch4nslava@gmail.com
Description:

"""

from playwright.async_api import async_playwright
from typing import List, Dict, Optional, Callable, Union
import re
import asyncio
from bs4 import BeautifulSoup

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
        async with self.p as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 导航到目标页面并获取完整HTML内容
            await page.goto(self.url["zb_ss"])
            await page.wait_for_load_state("networkidle")  # 等待网络空闲
            html_content = await page.content()  # 获取完整HTML
            await browser.close()

        # 使用BeautifulSoup解析HTML内容
        soup = BeautifulSoup(html_content, "html.parser")

        results = []

        kzb_blocks = soup.find_all("div", class_="m-2")

        for block in kzb_blocks:
            # 提取卡战备标题和日期
            title_tag = block.find("h3", class_="component-preview-title") # type: ignore
            if not title_tag:
                continue

            title_text = title_tag.get_text(strip=True)
            if "卡战备" not in title_text:
                continue
            date_span = title_tag.find("span", class_="p-2")# type: ignore
            update_time = date_span.get_text(strip=True) if date_span else ""

            # 提取战备值（如78W）
            match = re.search(r"卡战备【(\d+W)】", title_text)
            kzb_value = match.group(1) if match else "0W"

            kzb_data = {
                "title": title_text,
                "value": kzb_value,
                "update_time": update_time,
                "suits": [],
            }

            # 定位套装容器
            suits_container = block.find_next("div", class_="overflow-x-auto")
            if not suits_container:
                continue

            # 提取三个套装
            suits = suits_container.find_all( # type: ignore
                "ul", class_="list bg-base-500 rounded-box shadow-md m-2"
            )
            for suit in suits:
                suit_data = {"name": "", "cost": 0, "items": []}

                # 提取套装名称和花费
                header = suit.find("li", class_="p-4")# type: ignore
                if header:
                    header_text = header.get_text(strip=True)
                    name_match = re.search(r"【(.+?)】", header_text)
                    cost_match = re.search(r"预计花费【([\d,]+)】", header_text)

                    if name_match:
                        suit_data["name"] = name_match.group(1)
                    if cost_match:
                        suit_data["cost"] = int(cost_match.group(1).replace(",", ""))

                # 提取物品信息
                items = suit.find_all("li", class_="list-row") # type: ignore
                for item in items:
                    # 跳过非物品行（如标题行）
                    if "cursor-pointer" not in item.get("class", []): # type: ignore
                        continue

                    item_data = {"name": "", "type": "", "price": 0, "grade": ""}

                    # 物品名称
                    name_div = item.select_one(".list-col-grow > div:first-child") # type: ignore
                    if name_div:
                        item_data["name"] = name_div.get_text(strip=True)

                    # 物品价格
                    price_div = item.select_one( # type: ignore
                        ".text-xs.uppercase.font-semibold.opacity-60"
                    )
                    if price_div:
                        price_text = price_div.get_text(strip=True)
                        price_match = re.search(r"(\d[\d,]*)", price_text)
                        if price_match:
                            item_data["price"] = int(
                                price_match.group(1).replace(",", "")
                            )

                    # 物品类型
                    type_badge = item.select_one(".badge.badge-success") # type: ignore
                    if type_badge:
                        item_data["type"] = type_badge.get_text(strip=True)

                    # 物品等级
                    img = item.find("img") # type: ignore
                    if img and "data-grade" in img.attrs: # type: ignore
                        item_data["grade"] = img["data-grade"] # type: ignore

                    suit_data["items"].append(item_data)

                kzb_data["suits"].append(suit_data)

            results.append(kzb_data)
        return results

    async def map_pwd_daily(self):
        captured_data = {}
        async with self.p as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 导航到首页
            await page.goto(self.url["index"])
            await page.wait_for_selector(".stats.bg-base-500", timeout=10000)

            # 提取地图密码数据
            map_data = {}
            map_stats = await page.query_selector_all(".stats.bg-base-500 .stat")

            for stat in map_stats:
                # 提取地图名称
                title_element = await stat.query_selector(".stat-title")
                map_name = (
                    await title_element.inner_text() if title_element else "未知地图"
                )

                # 提取密码
                value_element = await stat.query_selector(".stat-value")
                password = (
                    await value_element.inner_text() if value_element else "未知密码"
                )

                # 提取日期
                date_element = await stat.query_selector(".stat-desc")
                date = await date_element.inner_text() if date_element else "未知日期"

                # 存储到结果字典
                map_data[map_name] = {"password": password, "date": date}

            captured_data["map_pwd"] = map_data
            await browser.close()

        return captured_data.get("map_pwd", {})

    async def get_price(self):
        a_list = [
            "gun",
            "helmet",
            "armor",
            "chest",
            "bag",
            "consume",
            "collection",
            "keys",
        ]
        captured_data = {a: [] for a in a_list}  # 初始化字典
        import re  # 导入正则模块用于提取数字

        async with self.p as p:
            browser = await p.chromium.launch(headless=True)

            async def scrape_page(a):
                url = self.url["item_list"] % a
                context = await browser.new_context()
                page = await context.new_page()
                logger.info(f"访问{url}列表页")
                await page.goto(url)
                await page.wait_for_timeout(3000)  # 等待页面加载

                # 处理分页
                page_num = 1
                max_pages = 50  # 安全限制

                while page_num <= max_pages:
                    # 等待表格加载完成
                    await page.wait_for_selector(
                        "table.table", state="visible", timeout=15000
                    )

                    # 获取所有行
                    rows = await page.query_selector_all("tbody tr")

                    for row in rows:
                        try:
                            # 提取物品ID和名称
                            name_element = await row.query_selector("div.font-bold")
                            name = (
                                await name_element.inner_text()
                                if name_element
                                else "N/A"
                            )
                            
                            # 提取图片链接获取物品ID
                            item_id = None
                            img_container = await row.query_selector("div.avatar > div.mask-squircle")
                            if img_container:
                                img_element = await img_container.query_selector("img")
                                if img_element:
                                    img_src = await img_element.get_attribute("src")
                                    if img_src:
                                        # 提取物品ID - 从URL末尾提取数字部分
                                        match = re.search(r'/(?:\d+|p_[^/.]+)\.png$', img_src)
                                        if match:
                                            item_id = match.group(1) if match.lastindex else match.group(0)
                            
                            # 构建图片URL
                            pic_url = f"https://playerhub.df.qq.com/playerhub/60004/object{item_id}" if item_id else ""
                            pic_url = pic_url.replace("p_","key/p_")
                            
                            # 提取品质信息
                            grade = 0  # 默认值
                            grade_element = await row.query_selector("div.text-sm.opacity-50")
                            if grade_element:
                                grade_text = await grade_element.inner_text()
                                # 使用正则提取数字
                                match = re.search(r'品质：(\d+)级', grade_text)
                                if match:
                                    grade = int(match.group(1))

                            # 提取价格数据
                            cells = await row.query_selector_all("td")
                            if len(cells) >= 7:  # 确保有足够的单元格
                                current_price = await cells[1].inner_text()
                                today_change = await cells[2].inner_text()

                                # 添加到结果 - 添加grade和pic字段
                                captured_data[a].append(
                                    {
                                        "name": name,
                                        "grade": grade,  # 添加品质字段
                                        "pic": pic_url,  # 添加图片URL字段
                                        "current_price": current_price,
                                        "today_change": today_change,
                                    }
                                )
                        except Exception as e:
                            logger.error(f"处理行时出错: {e}")

                    # 检查是否有下一页
                    next_button = await page.query_selector(
                        "button.btn-next:not([disabled])"
                    )
                    if not next_button:
                        break

                    # 点击下一页
                    await next_button.click()
                    await page.wait_for_timeout(2000)  # 等待页面加载
                    page_num += 1

                await context.close()

            # 并行处理所有类别
            tasks = [scrape_page(a) for a in a_list]
            await asyncio.gather(*tasks)
            await browser.close()

        return captured_data