from .states import GraphState

def user_profile_node(state: GraphState) -> GraphState:
    """
    用户画像节点，用于获取用户信息，并根据用户信息调整对话风格
    """
    # TODO: 实现用户偏好获取逻辑：获取用户编号，昵称、口味、长期上下文标记
    return state

def tool_nodes(state: GraphState) -> GraphState:
    """
    工具节点，用于处理工具调用
    """
    # TODO: 知识库检索、天气、日历、TTS
    # TODO：知识库检索：站内文档索引、FAQ 映射
    return state

def present_node(state: GraphState) -> GraphState:
    """
    展示节点，用于呈现结果
    """
    # TODO: 实现展示逻辑：动作（如果 live2D 支持）、网页操作、TTS、文本
    return state

def record_node(state: GraphState) -> GraphState:
    """
    记录节点，用于保存对话历史
    """
    # TODO: 实现记录逻辑：保存对话历史；作摘要处理并保存向量、图数据库
    return state

