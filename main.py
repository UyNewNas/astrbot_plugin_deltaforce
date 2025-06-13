
from typing import Dict, List, Optional, Set, Tuple

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

from .data_deltaforce import DrawCollection

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
        self.games = {
            "runs":{}
        }
        
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
    
    @filter.command_group("deltaforce", alias={"洲","DF"})
    async def deltaforce_cmd(self, event: AstrMessageEvent):
        pass
    
    
    @deltaforce_cmd.command("签到") # type: ignore
    async def deltaforce_sign(self, event: AstrMessageEvent):
        """签到"""
        player_id = event.get_sender_id()
        player_name = event.get_sender_name()
        player_raw = f"{player_name}({player_id})"
        player_raw = self._format_display_info(player_raw)
        group_id = event.get_group_id()
        if group_id not in self.games["runs"]:
            self.games["runs"][group_id] = {}
        if player_id not in self.games["runs"][group_id]:
            self.games["runs"][group_id][player_id] = {}
        if "sign" not in self.games["runs"][group_id][player_id]:
            self.games["runs"][group_id][player_id]["sign"] = 0
        if self.games["runs"][group_id][player_id]["sign"] == 0:
            # 签到成功,按天数*n获得十连抽
            self.games["runs"][group_id][player_id]["sign"] = 1            
            if "sign_days" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["sign_days"] = 0
            self.games["runs"][group_id][player_id]["sign_days"] += 1
            if "ap" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["ap"] = 0
            self.games["runs"][group_id][player_id]["ap"] += self.games["runs"][group_id][player_id]["sign_days"] * 100
            yield event.plain_result(f"{player_raw} 签到成功,获得{self.games['runs'][group_id][player_id]['sign_days'] * 10}点行动次数,当前可行动次数{self.games['runs'][group_id][player_id]['ap']}点")
        elif self.games["runs"][group_id][player_id]["sign"] == 1:
            yield event.plain_result(f"{player_raw} 已经签到过了,当前可行动次数{self.games['runs'][group_id][player_id]['ap']}点")
        
    
    def _format_collections(self, collections:List[Dict]):
        """格式化collection"""
        info = {
            1:[],
            2:[],
            3:[],
            4:[],
            5:[],
            6:[],
            "result":""
        }
        for collection in collections:
            grade = collection.get("grade")
            if grade in info:
                info[grade].append(collection)
        for i in range(1,7):
            if len(info[i]) == 0:continue
            if i == 1:
                tag="⚪"
            if i == 2:
                tag="🟢"
            if i == 3:
                tag="🔵"
            if i == 4:
                tag="🟣"
            if i == 5:
                tag="🟡"
            if i == 6:
                tag="🔴"
            collection_names = [collection.get("objectName") for collection in info[i]]
            info_str = f"{tag}战利品({len(info[i])})有:{collection_names}" # type: ignore
            info["result"] += info_str + "\n"
        return info["result"]
            

    @deltaforce_cmd.command("跑刀") # type: ignore
    async def deltaforce_run(self, event: AstrMessageEvent, _times: str|None=None):
        """跑刀"""
        try:
            if _times is None:
                times = 1
            else:
                times = int(_times)
                if times > 10:
                    times = 10
            player_id = event.get_sender_id()
            player_name = event.get_sender_name()
            player_raw = f"{player_name}({player_id})"
            player_raw = self._format_display_info(player_raw)
            group_id = event.get_group_id()
            if group_id not in self.games["runs"]:
                self.games["runs"][group_id] = {}
            if player_id not in self.games["runs"][group_id]:
                self.games["runs"][group_id][player_id] = {}
            if "ap" not in self.games["runs"][group_id][player_id]:
                self.games["runs"][group_id][player_id]["ap"] = 0
            ap = self.games["runs"][group_id][player_id]["ap"]
            if ap < times:
                yield event.plain_result(f"{player_raw} 行动次数不足,当前可行动次数{ap}点")
                return
            self.games["runs"][group_id][player_id]["ap"] -= times
            chain = [
                Comp.At(qq=player_id),
                Comp.Plain(f"{player_raw} 跑了 {times} 次刀.")
            ]
            draw_collection = DrawCollection()
            if times == 10:
                results = draw_collection.ten_draw()
                yield event.plain_result("跑刀中, 请等待雇佣兵返回结果")               
            else:
                results = []
                for _ in range(times):
                    results.append(draw_collection.draw_item())
            for _ in results:
                chain.append(Comp.Image.fromURL(_.get("pic")))
            info = self._format_collections(results)
            chain.append(Comp.Plain(info))
            yield event.chain_result(chain)
        except Exception as e:
            logger.exception(e)
            yield event.plain_result(f"跑刀失败,请联系管理员")
            
            
            
            
            
            
            
            
    