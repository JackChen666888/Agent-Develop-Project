"""LLM服务模块"""

from operator import ge

from hello_agents import HelloAgentsLLM
from app.config import get_settings
from langchain_openai import ChatOpenAI
import os

# 全局LLM实例
_llm_instance = None


def get_llm() -> HelloAgentsLLM:
    """
    获取LLM实例(单例模式)
    
    Returns:
        HelloAgentsLLM实例
    """
    global _llm_instance
    
    if _llm_instance is None:
        settings = get_settings()
        
        # HelloAgentsLLM会自动从环境变量读取配置
        # 包括OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL等
        _llm_instance = HelloAgentsLLM()
        
        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")
    
    return _llm_instance


_llm_instance_doubao = None

def get_llm_DouBao() -> ChatOpenAI:

    global _llm_instance_doubao
    settings = get_settings()
    print('-------------' + str(settings) + '------------------')
    if not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = settings.openai_api_key

    if not _llm_instance_doubao:
        _llm_instance_doubao = ChatOpenAI(
            model = settings.openai_model,
            base_url = settings.openai_base_url    
        )
    return _llm_instance_doubao


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None

