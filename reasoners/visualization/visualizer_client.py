"""
这段代码是一个用于可视化 LLM Reasoners 库中推理结果的客户端。它的主要功能和结构如下:

定义了 VisualizerClient 类，用于与可视化服务器 API 进行交互，包括上传推理结果数据并获取可访问的可视化页面 URL。

定义了 present_visualizer 函数，用于在浏览器中打开可视化页面。

定义了 visualize 函数，用于将不同类型的推理结果（如 TreeLog、MCTSResult、BeamSearchResult 和 DFSResult）转换为 TreeLog 对象，并上传到可视化服务器。
"""
import dataclasses
import json
from typing import Optional, Union

import requests

from reasoners.algorithm import MCTSResult, BeamSearchResult, DFSResult
from reasoners.visualization import TreeLog, TreeLogEncoder

# 默认的 API 服务器基础 URL
_API_DEFAULT_BASE_URL = "https://2wz3t0av30.execute-api.us-west-1.amazonaws.com/staging"
# 默认的可视化页面基础 URL
_VISUALIZER_DEFAULT_BASE_URL = "https://www.llm-reasoners.net"


class VisualizerClient:
    def __init__(self, base_url: str = _API_DEFAULT_BASE_URL) -> None:
        # 初始化客户端，设置 API 服务器的基础 URL
        self.base_url = base_url

    @dataclasses.dataclass
    class TreeLogReceipt:
        # 定义 TreeLogReceipt 类，用于存储上传后返回的日志 ID 和访问密钥
        id: str
        access_key: str

        @property
        def access_url(self) -> str:
            # 生成可访问的可视化页面 URL
            return f"{_VISUALIZER_DEFAULT_BASE_URL}/visualizer/{self.id}?accessKey={self.access_key}"

    def post_log(self, data: Union[TreeLog, str, dict]) -> Optional[TreeLogReceipt]:
        # 上传推理结果数据到 API 服务器
        if isinstance(data, TreeLog):
            # 如果数据是 TreeLog 对象，将其转换为 JSON 字符串
            data = json.dumps(data, cls=TreeLogEncoder)
        if isinstance(data, dict):
            # 如果数据是字典，将其转换为 JSON 字符串
            data = json.dumps(data)

        url = f"{self.base_url}/logs"
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=data)

        if response.status_code != 200:
            # 如果上传失败，打印错误信息并返回 None
            print(f"POST Log failed with status code: {response.status_code}, message: {response.text}")
            return None

        # 返回 TreeLogReceipt 对象，包含日志 ID 和访问密钥
        return self.TreeLogReceipt(**response.json())


def present_visualizer(receipt: VisualizerClient.TreeLogReceipt):
    # 在浏览器中打开可视化页面
    import webbrowser
    print(f"Visualizer URL: {receipt.access_url}")
    webbrowser.open(receipt.access_url)


def visualize(result: Union[TreeLog, MCTSResult, BeamSearchResult, DFSResult], **kwargs):
    # 将不同类型的推理结果转换为 TreeLog 对象，并上传到可视化服务器
    tree_log: TreeLog

    if isinstance(result, TreeLog):
        # 如果结果已经是 TreeLog 对象，直接使用
        tree_log = result
    elif isinstance(result, MCTSResult):
        # 如果结果是 MCTSResult 对象，将其转换为 TreeLog 对象
        tree_log = TreeLog.from_mcts_results(result, **kwargs)
    elif isinstance(result, BeamSearchResult):
        # 如果结果是 BeamSearchResult 对象，将其转换为 TreeLog 对象
        tree_log = TreeLog.from_beam_search_results(result, **kwargs)
    elif isinstance(result, DFSResult):
        # 如果结果是 DFSResult 对象，将其转换为 TreeLog 对象
        tree_log = TreeLog.from_dfs_results(result, **kwargs)
    elif isinstance(result, ...):
        # 如果结果类型未实现，抛出 NotImplementedError 异常
        raise NotImplementedError()
    else:
        # 如果结果类型不支持，抛出 TypeError 异常
        raise TypeError(f"Unsupported result type: {type(result)}")

    # 使用 VisualizerClient 上传 TreeLog 对象
    receipt = VisualizerClient().post_log(tree_log)

    if receipt is not None:
        # 如果上传成功，在浏览器中打开可视化页面
        present_visualizer(receipt)