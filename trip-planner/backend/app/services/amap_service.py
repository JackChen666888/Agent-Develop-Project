"""高德地图MCP服务封装"""

from typing import List, Dict, Any, Optional
from httpx import get
from langchain_core.tools import tool, BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient  
import asyncio, json
from app.models.schemas import Location, POIInfo, WeatherInfo, RouteInfo, POIDetailInfo
import json
from ..config import get_settings

# 全局MCP工具实例
_amap_mcp_tool = None


async def get_amap_mcp_tool() -> list[BaseTool]:
    """
    获取高德地图MCP工具实例(单例模式)
    
    Returns:
        MCPTool实例
    """
    global _amap_mcp_tool
    settings = get_settings()

    if _amap_mcp_tool is None:
        
        _amap_client = MultiServerMCPClient(
            {
                "amap-maps-streamableHTTP": {
                    "url": f"https://mcp.amap.com/sse?key={settings.amap_api_key}",
                    "transport": "sse"
                }
            }
        )

        _amap_mcp_tool = await _amap_client.get_tools()
    
    return _amap_mcp_tool


class AmapService:
    """高德地图服务封装类"""
    
    def __init__(self):
        """初始化服务"""
        return 


    async def init_mcp_tools(self):
        self.mcp_tools = await get_amap_mcp_tool()
        print(f'find {len(self.mcp_tools)} tools')
        self.mcp_tools_dict = dict()
        for tool in self.mcp_tools:
            self.mcp_tools_dict[tool.name] = tool


    async def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        【同步】查询天气（封装异步逻辑，外部直接调用）
        
        Args:
            city: 城市名称
            
        Returns:
            天气信息列表
            元素例如：{'date': '2026-02-19', 'week': '4', 'dayweather': '晴', 'nightweather': '晴', 'daytemp': '14', 'nighttemp': '-1', 'daywind': '西南', 'nightwind': '西南', 'daypower': '1-3', 'nightpower': '1-3', 'daytemp_float': '14.0', 'nighttemp_float': '-1.0'}
        """
        try:
            # 调用MCP工具
            tool = self.mcp_tools_dict.get('maps_weather')
            if not tool:
                raise ValueError("天气查询工具未找到")
            result = await tool.arun({'city': city})
            
            print(f"天气查询结果: {result}")
            print(type(result))
            weather_json = json.loads(result[0].get('text'))
            forecasts = weather_json.get('forecasts')  
            return forecasts

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []



    async def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI
        
        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内
            
        Returns:
            POI信息列表
            元素例如：{'id': 'B000A8UIN8', 'name': '故宫博物院', 'address': '景山前街4号', 'typecode': '110201|140100', 'photo': 'http://store.is.autonavi.com/showpic/2f968490d105bb2741e17f90b85c6b79'}, {'id': 'B000A84GDN', 'name': '故宫博物院- 
            午门', 'address': '东华门街道景山前街4号故宫博物院内(南侧)', 'typecode': '110200', 'photo': 'http://store.is.autonavi.com/showpic/dcd78b35cb123744056c03072ecdea17'}
        """
        try:
            # 调用MCP工具
            tool = self.mcp_tools_dict.get('maps_text_search')
            if not tool:
                raise ValueError("POI搜索工具未找到")
            result = await tool.arun({
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower()
                })

            print(result)
            print(type(result))
            poi_json = json.loads(result[0].get('text'))
            pois = poi_json.get('pois')  
            return pois
            
        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []



    async def plan_route(self, 
        origin_address: str,
        origin_city: str, 
        destination_address: str,
        destination_city: str, 
        route_type: str = "walking"
    ) -> List[RouteInfo]:
        """
        规划路线
        
        Args:
            origin_address: 起点地址(经度，纬度)
            destination_address: 终点地址(经度，纬度)
            route_type: 路线类型 (walking/driving/transit)
            
        Returns:
            路线信息
            例子：[{'distance': 20976, 'duration': 16781, 'steps': [{'instruction': '向东北步行46米左转', 'road': '', 'distance': 46, 'orientation': '东北', 'duration': 37}, {'instruction': '向西北步行104米右转', 'road': '', 'distance': 104, 'orientation': '西北', 'duration': 83}]}]
        """
        
        try:
            # 根据路线类型选择工具
            tool_map = {
                "walking": "maps_direction_walking",
                "driving": "maps_direction_driving",
                "transit": "maps_direction_transit_integrated"
            }
            
            tool_name = tool_map.get(route_type, "maps_direction_walking")
            
            origin_address_locations = await self.geocode(origin_address, city=origin_city)
            origin_address_location_str = str(origin_address_locations[0].longitude) + "," + str(origin_address_locations[0].latitude)
            destination_address_locations = await self.geocode(destination_address, city=destination_city)
            destination_address_location_str = str(destination_address_locations[0].longitude) + "," + str(destination_address_locations[0].latitude)
            print(origin_address_location_str)
            print(destination_address_location_str)

            # 构建参数
            arguments = {
                "origin": origin_address_location_str,
                "destination": destination_address_location_str
            }

            if route_type == 'transit':
                arguments['city1'] = origin_city
                arguments['city2'] = destination_city
            
            # 调用MCP工具
            tool = self.mcp_tools_dict.get(tool_name)
            if not tool:
                raise ValueError("路线规划工具未找到")
            result = await tool.arun(arguments)

            print(result)
            print(type(result))
            route_json = json.loads(result[0].get('text'))
            paths = route_json.get('route').get('paths')
            return paths
            
        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return []


    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
            result 元素例如：{"results":[{"country":"中国","province":"北京市","city":"北京市","citycode":"010","district":"朝阳区","street":"阜通东大街","number":"6号","adcode":"110105","location":"116.482086,39.990496","level":"门址"}
        """
        try:
            arguments = {"address": address}
            if city:
                arguments["city"] = city

            # 调用MCP工具
            tool = self.mcp_tools_dict.get("maps_geo")
            if not tool:
                raise ValueError("地理编码工具未找到")
            result = await tool.arun(arguments)

            print(result)
            print(type(result))
            result_json = json.loads(result[0].get('text'))
            results = result_json.get('results')
            geos = []
            for result in results:
                location = result.get('location')
                location_split = location.split(',')
                geos.append(Location(longitude = location_split[0], latitude = location_split[1]))  
            return geos

        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None



    async def get_poi_detail(self, poi_id: str) -> POIDetailInfo:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            # 调用MCP工具
            tool = self.mcp_tools_dict.get("maps_search_detail")
            if not tool:
                raise ValueError("POI详情工具未找到")
            
            arguments = {"id": poi_id}
            result = await tool.arun(arguments)

            print(f"POI详情结果: {result}")
            print(type(result))
            poi_detail_info = json.loads(result[0].get('text'))

            return poi_detail_info

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}
    

# 创建全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service
    
    if _amap_service is None:
        _amap_service = AmapService()
    
    return _amap_service


if __name__ == '__main__':
    service = get_amap_service()
    asyncio.run(service.init_mcp_tools())
    print(asyncio.run(service.get_weather("北京")))
    # print(asyncio.run(service.search_poi("故宫", "北京")))
    # print(asyncio.run(service.get_poi_detail("B000A8UIN8")))
    # print(asyncio.run(service.play_route(
    #     origin_address="天安门",
    #     origin_city="北京",
    #     destination_address="故宫",
    #     destination_city="北京",
    #     route_type="walking"
    # )))