"""
这段代码定义了一个名为 TreeLog 的类，用于记录和管理树形结构的搜索算法（如 MCTS、Beam Search 和 DFS）在搜索过程中的快照。它提供了将不同搜索算法的结果转换为 TreeLog 对象的方法，并支持将 TreeLog 对象序列化为 JSON 格式。

TreeLog 类的主要组成部分如下：

TreeLogEncoder：一个自定义的 JSON 编码器，用于将 TreeSnapshot 及其相关对象转换为 JSON 格式。
TreeLog 类的初始化方法和一些特殊方法，如 __getitem__、__iter__、__len__ 和 __str__，用于支持对 TreeLog 对象的索引、迭代、长度查询和字符串表示。
from_mcts_results、from_beam_search_results 和 from_dfs_results 三个类方法，分别用于将 MCTS、Beam Search 和 DFS 的搜索结果转换为 TreeLog 对象。
"""

import json
from typing import Sequence, Union

from reasoners.algorithm import MCTSNode, MCTSResult, BeamSearchNode, BeamSearchResult, DFSNode, DFSResult
from reasoners.visualization.tree_snapshot import NodeId, EdgeId, TreeSnapshot, NodeData, EdgeData


class TreeLogEncoder(json.JSONEncoder):
    def default(self, o):
        from numpy import float32

        if isinstance(o, TreeSnapshot.Node):
            return o.__dict__
        elif isinstance(o, TreeSnapshot.Edge):
            return o.__dict__
        elif isinstance(o, TreeSnapshot):
            return o.__dict__()
        elif isinstance(o, float32):
            return float(o)
        if isinstance(o, TreeLog):
            return {"logs": list(o)}
        else:
            return super().default(o)


class TreeLog:
    def __init__(self, tree_snapshots: Sequence[TreeSnapshot]) -> None:
        self._tree_snapshots = tree_snapshots

    def __getitem__(self, item):
        return self._tree_snapshots[item]

    def __iter__(self):
        return iter(self._tree_snapshots)

    def __len__(self):
        return len(self._tree_snapshots)

    def __str__(self):
        return json.dumps(self, cls=TreeLogEncoder, indent=2)

    @classmethod
    def from_mcts_results(cls, mcts_results: MCTSResult, node_data_factory: callable = None,
                          edge_data_factory: callable = None) -> 'TreeLog':
        """从 MCTS 搜索结果创建 TreeLog 对象"""

        def get_reward_details(n: MCTSNode) -> Union[dict, None]:
            """获取节点的奖励细节"""
            if hasattr(n, "reward_details"):
                return n.reward_details
            return n.fast_reward_details if hasattr(n, "fast_reward_details") else None

        def default_node_data_factory(n: MCTSNode) -> NodeData:
            """默认的节点数据工厂函数"""
            if not n.state:
                return NodeData({})
            # 将任何对象转换为字典
            if hasattr(n.state, "_asdict"):
                # 如果状态是 NamedTuple
                state_dict = n.state._asdict()
            elif isinstance(n.state, list):
                state_dict = {idx: value for idx, value in enumerate(n.state)}
            else:
                try:
                    state_dict = dict(n.state)
                except TypeError:
                    raise TypeError("The type of the state is not supported. "
                                    "Please provide a node_data_factory function to transform the state to a dict.")
            return NodeData(state_dict)

        def default_edge_data_factory(n: MCTSNode) -> EdgeData:
            """默认的边数据工厂函数"""
            return EdgeData({"Q": n.Q, "reward": n.reward, **get_reward_details(n)})

        node_data_factory = node_data_factory or default_node_data_factory
        edge_data_factory = edge_data_factory or default_edge_data_factory

        snapshots = []

        def all_nodes(node: MCTSNode):
            """递归遍历所有节点"""
            node_id = NodeId(node.id)

            nodes[node_id] = TreeSnapshot.Node(node_id, node_data_factory(node))
            if node.children is None:
                return
            for child in node.children:
                edge_id = EdgeId(len(edges))
                edges.append(TreeSnapshot.Edge(edge_id, node.id, child.id, edge_data_factory(child)))
                all_nodes(child)

        if mcts_results.tree_state_after_each_iter is None:
            tree_states = [mcts_results.tree_state]
        else:
            tree_states = mcts_results.tree_state_after_each_iter
        for step in range(len(tree_states)):
            edges = []
            nodes = {}

            root = tree_states[step]
            all_nodes(root)
            tree = TreeSnapshot(list(nodes.values()), edges)

            # 选择跟踪 MCTS 搜索路径的边
            if mcts_results.trace_in_each_iter:
                trace = mcts_results.trace_in_each_iter[step]
                for step_idx in range(len(trace) - 1):
                    in_node_id = trace[step_idx].id
                    out_node_id = trace[step_idx + 1].id
                    for edges in tree.out_edges(in_node_id):
                        if edges.target == out_node_id:
                            nodes[in_node_id].selected_edge = edges.id
                            break

            # 对于其他节点，选择 Q 值最高的边
            for node in tree.nodes.values():
                if node.selected_edge is None and tree.children(node.id):
                    node.selected_edge = max(
                        tree.out_edges(node.id),
                        key=lambda edge: edge.data.get("Q", -float("inf"))
                    ).id
            
            snapshots.append(tree)

        return cls(snapshots)

    @classmethod
    def from_beam_search_results(cls, bs_results: Union[BeamSearchResult, Sequence[BeamSearchResult]],
                                 node_data_factory: callable = None, edge_data_factory: callable = None) -> 'TreeLog':
        """从 Beam Search 搜索结果创建 TreeLog 对象"""
        
        if isinstance(bs_results, BeamSearchResult):
            bs_results = [bs_results]
        bs_results = bs_results[0]

        def default_node_data_factory(n: BeamSearchNode) -> NodeData:
            """默认的节点数据工厂函数"""
            if not n.state:
                return NodeData({})
            # 将任何对象转换为字典
            if hasattr(n.state, "_asdict"):
                # 如果状态是 NamedTuple
                state_dict = n.state._asdict()
            elif isinstance(n.state, list):
                state_dict = {idx: value for idx, value in enumerate(n.state)}
            else:
                try:
                    state_dict = dict(n.state)
                except TypeError:
                    raise TypeError("The type of the state is not supported. "
                                    "Please provide a node_data_factory function to transform the state to a dict.")
            return NodeData(state_dict)


        def default_edge_data_factory(n: BeamSearchNode) -> EdgeData:
            """默认的边数据工厂函数"""
            return EdgeData({"reward": n.reward, "action": n.action})

        node_data_factory = node_data_factory or default_node_data_factory
        edge_data_factory = edge_data_factory or default_edge_data_factory

        snapshots = []

        def all_nodes(node: BeamSearchNode):
            """递归遍历所有节点"""
            node_id = NodeId(node.id)

            nodes[node_id] = TreeSnapshot.Node(node_id, node_data_factory(node))
            for child in node.children:
                edge_id = EdgeId(len(edges))
                edges.append(TreeSnapshot.Edge(edge_id, node.id, child.id, edge_data_factory(child)))
                all_nodes(child)

        root = bs_results.tree
        edges = []
        nodes = {}
        all_nodes(root)
        tree = TreeSnapshot(list(nodes.values()), edges)

        # 选择奖励最高的边
        for node in tree.nodes.values():
            if node.selected_edge is None and tree.children(node.id):
                node.selected_edge = max(
                    tree.out_edges(node.id),
                    key=lambda edge: edge.data.get("reward", -float("inf"))
                ).id

        snapshots.append(tree)

        return cls(snapshots)

    @classmethod
    def from_dfs_results(cls, dfs_results: DFSResult, node_data_factory: callable = None,
                        edge_data_factory: callable = None) -> 'TreeLog':
        """从 DFS 搜索结果创建 TreeLog 对象"""

        def default_node_data_factory(n: DFSNode) -> NodeData:
            """默认的节点数据工厂函数"""
            if not n.state:
                return NodeData({})
            # 将任何对象转换为字典
            if hasattr(n.state, "_asdict"):
                # 如果状态是 NamedTuple
                state_dict = n.state._asdict()
            elif isinstance(n.state, list):
                state_dict = {idx: value for idx, value in enumerate(n.state)}
            else:
                try:
                    state_dict = dict(n.state)
                except TypeError:
                    raise TypeError("The type of the state is not supported. "
                                    "Please provide a node_data_factory function to transform the state to a dict.")
            return NodeData(state_dict)

        def default_edge_data_factory(n: DFSNode) -> EdgeData:
            """默认的边数据工厂函数"""
            return EdgeData({"reward": n.reward, "action": n.action})

        node_data_factory = node_data_factory or default_node_data_factory
        edge_data_factory = edge_data_factory or default_edge_data_factory

        snapshots = []

        edges = []
        nodes = {}

        def all_nodes(node: DFSNode):
            """递归遍历所有节点"""
            node_id = NodeId(node.id)
            nodes[node_id] = TreeSnapshot.Node(node_id, node_data_factory(node))
            for child in node.children:
                edge_id = EdgeId(len(edges))
                edges.append(TreeSnapshot.Edge(edge_id, node.id, child.id, edge_data_factory(child)))
                all_nodes(child)


        root = dfs_results.tree_state
        all_nodes(root)
        tree = TreeSnapshot(list(nodes.values()), edges)

        # 选择奖励最高的边
        for node in tree.nodes.values():
            if node.selected_edge is None and tree.children(node.id):
                node.selected_edge = max(
                    tree.out_edges(node.id),
                    key=lambda edge: edge.data.get("reward", -float("inf"))
                ).id

        snapshots.append(tree)

        return cls(snapshots)