"""
Author: slava
Date: 2025-06-14 02:53:16
LastEditTime: 2025-06-30 12:42:07
LastEditors: ch4nslava@gmail.com
Description:

"""

from pickletools import read_uint1
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from flask import session
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)
from .data_deltaforce import DrawItem, DataDeltaForce
from .price import DeltaForcePrice
from .acg_ice_api import AcgIceSJZApi

data = DataDeltaForce()

# import subprocess
# from playwright import _repo_version as pw_version

# def install_playwright_browsers():
#     try:
#         # 检查驱动是否已安装
#         from playwright.__main__ import main
#         if not subprocess.run(["playwright", "install", "--dry-run"], capture_output=True).returncode == 0:
#             print("Installing Playwright browsers...")
#             main(["install"])  # 执行驱动安装
#             main(["install-deps"])  # 安装系统依赖（Linux/Mac需sudo）[7](@ref)
#     except ImportError:
#         raise RuntimeError("Playwright not installed. Run `pip install playwright` first.")

# @filter.on_astrbot_loaded()
# async def on_astrbot_loaded(self):
#     install_playwright_browsers()


@register(
    "DeltaForce",
    "UyNewNas",
    "三角洲搜打撤插件",
    "v0.1",
    "https://github.com/UyNewNas/astrbot_plugin_deltaforce",
)
class DeltaForcePlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.games = (
            {"runs": {}, "bags": {}}
            if data.get_deltaforce() is None
            else data.get_deltaforce()
        )

    def _parse_display_info(self, raw_info: str) -> Tuple[str, str]:
        try:
            if "(" in raw_info and raw_info.endswith(")"):
                name_part, qq_part = raw_info.rsplit("(", 1)
                return name_part.strip(), qq_part[:-1]
            if "(" not in raw_info:
                return raw_info, "未知QQ号"
            parts = raw_info.split("(")
            if len(parts) >= 2:
                return parts[0].strip(), parts[-1].replace(")", "")
            return raw_info, "解析失败"
        except Exception as e:
            print(f"解析display_info失败：{raw_info} | 错误：{str(e)}")
            return raw_info, "解析异常"

    def _format_display_info(self, raw_info: str) -> str:
        nickname, qq = self._parse_display_info(raw_info)
        max_len = self.config.get("display_name_max_length", 10)
        safe_nickname = nickname.replace("\n", "").replace("\r", "").strip()
        formatted_nickname = (
            safe_nickname[:max_len] + "……"
            if len(safe_nickname) > max_len
            else safe_nickname
        )
        return f"{formatted_nickname}({qq})"

    def _get_today(self) -> Tuple[int, int, int]:
        today = datetime.now()
        logger.info(f"当前时间戳: {today}")
        return today.year, today.month, today.day

    def _get_now(self):
        now = datetime.now()
        logger.info(f"当前时间戳: {now}")
        return {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "microsecond": now.microsecond,
        }

    @filter.command_group("deltaforce", alias={"洲", "DF"})
    async def deltaforce_cmd(self, event: AstrMessageEvent):
        """
        三角洲小工具插件指令帮助
        deltaforce （洲/DF）指令组
        该指令组包含以下子指令:
        - 签到: 签到并获得行动点
        - 跑刀: 进行跑刀操作,消耗行动点
        - 查询背包: 查询背包中的物品
        - 查询行动点: 查询当前可用的行动点
        - 查询价格（空格）物品名称: 查询物品的价格
        - 查询背包价格: 查询背包中物品的总价格
        - 卡战备（空格）数值: 查询卡战备数据,数值可以是11W,18W,35W,45W,55W,78W
        - 每日密码: 查询每日地图密码
        - 帮助: 显示该帮助信息
        """
        pass

    @deltaforce_cmd.command("帮助")  # type: ignore
    async def deltaforce_help(self, event: AstrMessageEvent):
        """显示命令帮助信息"""
        plain = [
            "三角洲小工具插件指令帮助",
            "deltaforce （洲/DF）指令组",
            "该指令组包含以下子指令:",
            "- 签到: 签到并获得行动点",
            "- 跑刀: 进行跑刀操作,消耗行动点",
            "- 查询背包: 查询背包中的物品",
            "- 查询行动点: 查询当前可用的行动点",
            "- 查询价格（空格）物品名称: 查询物品的价格",
            "- 查询背包价格: 查询背包中物品的总价格",
            "- 卡战备（空格）数值: 查询卡战备数据,数值可以是11W,18W,35W,45W,55W,78W",
            "- 每日密码: 查询每日地图密码",
            "- 帮助: 显示该帮助信息",
        ]
        chain = [Comp.At(qq=event.get_sender_id()), Comp.Plain("\n".join(plain))]
        yield event.chain_result(chain)

    @deltaforce_cmd.command("签到")  # type: ignore
    async def deltaforce_sign(self, event: AstrMessageEvent):
        """签到"""
        logger.info(self.games)
        today = "%s.%s.%s" % self._get_today()
        now = self._get_now()
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        group_id = event.get_group_id()
        if "runs" not in self.games:
            self.games["runs"] = {}
        if group_id not in self.games["runs"]:
            self.games["runs"][group_id] = {}
        if player_id not in self.games["runs"][group_id]:
            self.games["runs"][group_id][player_id] = {}
        if "sign" not in self.games["runs"][group_id][player_id]:
            self.games["runs"][group_id][player_id]["sign"] = {}
        if f"{today}" not in self.games["runs"][group_id][player_id]["sign"]:
            self.games["runs"][group_id][player_id]["sign"][f"{today}"] = {"is_sign": 0}
        if self.games["runs"][group_id][player_id]["sign"][f"{today}"]["is_sign"] == 0:
            # 记录时间戳用于恢复行动点,以每天第一次签到的时间戳开始计算
            if (
                "sign_timestamp"
                not in self.games["runs"][group_id][player_id]["sign"][f"{today}"]
            ):
                self.games["runs"][group_id][player_id]["sign"][f"{today}"][
                    "sign_timestamp"
                ] = now
            # 签到成功,按天数*n获得十连抽
            self.games["runs"][group_id][player_id]["sign"][f"{today}"]["is_sign"] = 1
            if "sign_days" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["sign_days"] = 0
            self.games["runs"][group_id][player_id]["sign_days"] += 1
            if "ap" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["ap"] = 0
            self.games["runs"][group_id][player_id]["ap"] += (
                self.games["runs"][group_id][player_id]["sign_days"] * 10
            )
            yield event.plain_result(
                f"{player_raw} 签到成功,获得{self.games['runs'][group_id][player_id]['sign_days'] * 10}点行动次数,当前可行动次数{self.games['runs'][group_id][player_id]['ap']}点"
            )
        elif (
            self.games["runs"][group_id][player_id]["sign"][f"{today}"]["is_sign"] == 1
        ):
            yield event.plain_result(
                f"{player_raw} 已经签到过了,当前可行动次数{self.games['runs'][group_id][player_id]['ap']}点"
            )
        logger.info(self.games)
        data.update_deltaforce(self.games)

    def _format_collections(self, collections: List[Dict]):
        """格式化collection"""
        info = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], "result": ""}
        for collection in collections:
            grade = collection.get("grade")
            if grade in info:
                info[grade].append(collection)
        for i in range(1, 7):
            if len(info[i]) == 0:
                continue
            if i == 1:
                tag = "⚪"
            if i == 2:
                tag = "🟢"
            if i == 3:
                tag = "🔵"
            if i == 4:
                tag = "🟣"
            if i == 5:
                tag = "🟡"
            if i == 6:
                tag = "🔴"
            collection_names = [collection.get("objectName",collection.get("name")) for collection in info[i]]
            info_str = f"\n{tag}战利品({len(info[i])})有:{','.join(collection_names)}"  # type: ignore
            info["result"] += info_str
        return info["result"]

    def _collections_progress(self, collections: List[Dict]):
        """计算金色和红色战利品去重后的数量"""
        unique_gold = set()
        unique_red = set()
        for collection in collections:
            if collection.get("grade") == 5:
                unique_gold.add(collection.get("objectName",collection.get("name")))
            if collection.get("grade") == 6:
                unique_red.add(collection.get("objectName",collection.get("name")))
        return {"gold": len(unique_gold), "red": len(unique_red)}

    def _format_progress_bar(self, current: int, total: int, length: int = 20) -> str:
        """格式化进度条"""
        if total <= 0:
            return "无进度"
        filled_length = int(length * current // total)
        bar = "█" * filled_length + "-" * (length - filled_length)
        return f"[{bar}] {current}/{total} ({(current / total) * 100:.2f}%)"

    @deltaforce_cmd.command("跑刀")  # type: ignore
    async def deltaforce_run(self, event: AstrMessageEvent, _times: str | None = None):
        """跑刀（上限10次）"""
        try:
            logger.info(self.games)
            player_id = event.get_sender_id()
            player_name = event.get_sender_name()
            player_raw = f"{player_name}({player_id})"
            player_raw = self._format_display_info(player_raw)
            group_id = event.get_group_id()
            today = "%s.%s.%s" % self._get_today()
            if "runs" not in self.games:
                self.games["runs"] = {}
            if "bags" not in self.games:
                self.games["bags"] = {}
            if group_id not in self.games["runs"]:
                self.games["runs"][group_id] = {}
            if player_id not in self.games["bags"]:
                self.games["bags"][player_id] = []
            if player_id not in self.games["runs"][group_id]:
                self.games["runs"][group_id][player_id] = {}
            if "sign" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["sign"] = {}
            # 判断是否签到
            if f"{today}" not in self.games["runs"][group_id][player_id]["sign"]:
                yield event.plain_result(f"{player_raw} 请先签到")
                return
            now = self._get_now()
            # 计算时间差
            sign_timestamp = self.games["runs"][group_id][player_id]["sign"][
                f"{today}"
            ]["sign_timestamp"]
            now_datetime = datetime(
                year=now["year"],
                month=now["month"],
                day=now["day"],
                hour=now["hour"],
                minute=now["minute"],
                second=now["second"],
                microsecond=now["microsecond"],
            )
            sign_timestamp_datetime = datetime(
                year=sign_timestamp["year"],
                month=sign_timestamp["month"],
                day=sign_timestamp["day"],
                hour=sign_timestamp["hour"],
                minute=sign_timestamp["minute"],
                second=sign_timestamp["second"],
                microsecond=sign_timestamp["microsecond"],
            )
            time_diff = now_datetime - sign_timestamp_datetime
            days = time_diff.days
            total_seconds = time_diff.total_seconds()
            remaining_seconds = total_seconds - (days * 24 * 3600)
            hours = remaining_seconds / 3600.0
            # 每过一个小时恢复2点行动点
            if hours >= 1:
                self.games["runs"][group_id][player_id]["ap"] += 2 * int(hours)
            if _times is None:
                times = 1
            else:
                times = int(_times)
                if times > 10:
                    times = 10
            if group_id not in self.games["runs"]:
                self.games["runs"][group_id] = {}
            if player_id not in self.games["runs"][group_id]:
                self.games["runs"][group_id][player_id] = []
            if "ap" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["ap"] = 0
            ap = self.games["runs"][group_id][player_id]["ap"]
            if ap < times:
                yield event.plain_result(
                    f"{player_raw} 行动次数不足,当前可行动次数{ap}点"
                )
                return
            self.games["runs"][group_id][player_id]["ap"] -= times
            chain = [
                Comp.At(qq=player_id),
                Comp.Plain(f"{player_raw} 跑了 {times} 次刀."),
            ]
            draw_collection = DrawItem()
            if draw_collection.items == []:
                await DeltaForcePrice().get_all_items_price()
                draw_collection = DrawItem()
            
            if times == 10:
                results = draw_collection.ten_draw()
                yield event.plain_result("跑刀中, 请等待雇佣兵返回结果")
            else:
                results = []
                for _ in range(times):
                    results.append(draw_collection.draw_item())
            total_price = 0
            for _ in results:
                # 查询物品价格并累加
                name = _.get("objectName",_.get("name"))
                price = await DeltaForcePrice().get_price(name)
                if price is not None:
                    total_price += price
                # 只有稀有度大于等于5的才展示图片
                if _.get("grade") >= 5:
                    if "pic" in _:
                        chain.append(Comp.Image.fromURL(_.get("pic")))
                    self.games["bags"][player_id].append(_)
            info = self._format_collections(results)
            info += f"\n总价值约为{total_price:,}哈夫币"
            chain.append(Comp.Plain(info))
            yield event.chain_result(chain)
            # 写入数据
            data.update_deltaforce(self.games)
        except Exception as e:
            logger.exception(e)
            yield event.plain_result(f"跑刀失败,请联系管理员")

    @deltaforce_cmd.command("查询背包")  # type: ignore
    async def deltaforce_bag(self, event: AstrMessageEvent):
        """查询背包"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        if player_id not in self.games["bags"]:
            yield event.plain_result(f"{player_raw} 背包为空")
            return
        if len(self.games["bags"][player_id]) == 0:
            yield event.plain_result(f"{player_raw} 背包为空")
            return

        plain = [f"{player_raw} 的背包:"]
        info = self._format_collections(self.games["bags"][player_id])
        plain.append(info)
        player_progress = self._collections_progress(self.games["bags"][player_id])
        all_progress = self._collections_progress(DrawItem().items)
        bar_gold = self._format_progress_bar(
            player_progress["gold"], all_progress["gold"]
        )
        bar_red = self._format_progress_bar(player_progress["red"], all_progress["red"])
        plain.append(
            f"金色战利品进度: {bar_gold}({player_progress['gold']}/{all_progress['gold']})"
        )
        plain.append(
            f"红色战利品进度: {bar_red}({player_progress['red']}/{all_progress['red']})"
        )
        chain = [Comp.At(qq=player_id), Comp.Plain("\n".join(plain))]
        logger.debug(self.games)
        yield event.chain_result(chain)

    @deltaforce_cmd.command("查询行动点")  # type: ignore
    async def deltaforce_ap(self, event: AstrMessageEvent):
        """查询行动点"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        if player_id not in self.games["runs"]:
            yield event.plain_result(f"{player_raw} 当前没有进行中的行动")
            return
        ap = self.games["runs"][player_id].get("ap", 0)
        yield event.plain_result(f"{player_raw} 当前可行动点: {ap}")

    @deltaforce_cmd.command("查询价格")  # type: ignore
    async def deltaforce_price(self, event: AstrMessageEvent, item_name: str):
        """查询价格"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        yield event.plain_result(
            f"查询物品（{item_name}）的价格(数据来源www.acgice.com)中,请稍候..."
        )
        price = await DeltaForcePrice().get_price(item_name)
        if price is not None:
            yield event.plain_result(
                f"{player_raw}\n{item_name} 的当日价格为: {price}哈夫币\n具体价格可能会有波动,请以实际游戏为准"
            )
        else:
            yield event.plain_result(f"未找到 {item_name} 的当日价格信息,请联系管理员")

    @deltaforce_cmd.command("查询背包价格")  # type: ignore
    async def deltaforce_bag_price(self, event: AstrMessageEvent):
        """查询背包总价格"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        if player_id not in self.games["bags"]:
            yield event.plain_result(f"{player_raw} 背包为空")
            return
        total_price = 0
        for item in self.games["bags"][player_id]:
            price = await DeltaForcePrice().get_price(item.get("objectName",item.get("name")))
            if price is not None:
                total_price += price
        if total_price > 0:
            yield event.plain_result(
                f"{player_raw} 背包总价值约为: {total_price:,}哈夫币"
            )
        else:
            yield event.plain_result(f"{player_raw} 背包中没有可查询价格的物品")

    @deltaforce_cmd.command("卡战备")  # type: ignore
    async def deltaforce_gear_value_threshold(
        self, event: AstrMessageEvent, value: str
    ):
        """查询卡战备数据,数值可以是11W,18W,35W,45W,55W,78W"""
        if value.upper() not in ["11W", "18W", "35W", "45W", "55W", "78W"]:
            yield event.plain_result(
                "无效的卡战备数值,请输入11W,18W,35W,45W,55W,78W之一"
            )
            return
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        yield event.plain_result(
            f"{player_raw} 正在查询卡战备数据(数据来源www.acgice.com),请稍等..."
        )
        acg_api = AcgIceSJZApi()
        kzb_data = await acg_api.jz_zb()
        for kzb in kzb_data:
            if kzb.get("value", "").upper() != value.upper():
                continue
            plain = []
            title = kzb.get("title", "")
            update_time = kzb.get("update_time", "")
            suits = kzb.get("suits", "")
            plain.append(f"已经查询到{len(suits)}个{title}方案")
            for i in range(len(suits)):
                plain.append(f"{i + 1}.{suits[i].get('name', '')}")
            plain.append(f"请输入数字选择方案,输入0退出")
            yield event.plain_result("\n".join(plain))

            def get_suit_info(suits: List, choice: int) -> List:
                for index, suit in enumerate(suits):
                    if choice == 0:
                        break
                    if index + 1 != choice:
                        continue
                    plain = []
                    suit_name = suit.get("name", "")
                    suti_cost = suit.get("cost", "")
                    suit_items = suit.get("items", [])
                    plain.append(f"{title}")
                    plain.append(f"套装：【{suit_name}】(总花费{suti_cost}哈夫币)")
                    for suit_item in suit_items:
                        suit_item_type = suit_item.get("type", "")
                        suit_item_name = suit_item.get("name", "")
                        if suit_item_name == "":
                            continue
                        suit_item_price = suit_item.get("price", 0)
                        suit_item_grade = suit_item.get("grade", "")
                        if suit_item_grade == "0":
                            suit_item_grade = "无"
                        elif suit_item_grade == "1":
                            suit_item_grade = "白⚪"
                        elif suit_item_grade == "2":
                            suit_item_grade = "绿🟢"
                        elif suit_item_grade == "3":
                            suit_item_grade = "蓝🔵"
                        elif suit_item_grade == "4":
                            suit_item_grade = "紫🟣"
                        elif suit_item_grade == "5":
                            suit_item_grade = "金🟡"
                        elif suit_item_grade == "6":
                            suit_item_grade = "红🔴"
                        else:
                            suit_item_grade = "无"
                        suit_item_info = f"[{suit_item_type}]{suit_item_name}({suit_item_grade}):价格{suit_item_price}"
                        plain.append(suit_item_info)
                    return plain
                return []

            # 获取下一条消息
            @session_waiter(timeout=30, record_history_chains=False)  # type: ignore
            async def handle_choice(
                controller: SessionController, event: AstrMessageEvent
            ):
                choice = event.message_str
                message_result = event.make_result()
                if choice == "0":
                    message_result.chain = [Comp.Plain("查询已退出")]
                    await event.send(message_result)
                    controller.stop()
                    return
                elif choice.isdigit():
                    choice = int(choice)
                    plain = get_suit_info(suits, choice)
                else:
                    plain = []
                message_result.chain = [Comp.Plain("\n".join(plain))]
                await event.send(message_result)
                controller.keep(timeout=30, reset_timeout=True)

            try:
                await handle_choice(event)
            except TimeoutError as _:
                logger.error(f"等待超时")
                yield event.plain_result("查询超时,请重新查询")
            finally:
                event.stop_event()

    @deltaforce_cmd.command("更新价格")  # type: ignore
    async def deltaforce_update_price(self, event: AstrMessageEvent):
        """强制更新价格"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        yield event.plain_result("正在更新中,请稍候...")
        price = await DeltaForcePrice().get_all_items_price()
        if price is not None:
            yield event.plain_result(f"更新交易行价格成功！")
        else:
            yield event.plain_result(f"更新价格失败,请咨询管理员。")

    @deltaforce_cmd.command("每日密码")  # type: ignore
    async def deltaforce_daily_password(self, event: AstrMessageEvent):
        """查询地图每日密码"""
        acg_api = AcgIceSJZApi()
        map_pwd_data = await acg_api.map_pwd_daily()
        if not map_pwd_data:
            yield event.plain_result("未找到每日密码数据")
            return
        if not map_pwd_data:
            yield event.plain_result("未找到每日密码数据3")
            return
        plain = []
        for key, value in map_pwd_data.items():
            map_name = key
            map_pwd = value.get("password")
            map_date = value.get("date")
            plain.append(f"地图: {map_name}, {map_date}密码: {map_pwd}")
        yield event.plain_result("\n".join(plain))
