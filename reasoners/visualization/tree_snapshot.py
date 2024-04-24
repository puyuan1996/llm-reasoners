# 这段代码定义了一个名为 TreeSnapshot 的类，用于表示一棵树的快照。该类包含了树的节点和边的信息，并提供了一些方法来访问和操作这些数据。

# 这个 TreeSnapshot 类的主要功能是：

# 存储树的节点和边的信息，并提供方法来访问这些数据。
# 通过 _parent 和 _children 字典来维护节点之间的父子关系。
# 提供 _connected() 方法来检查树是否连通。
# 提供 node()、edge()、out_edges()、in_edges()、parent() 和 children() 方法来访问节点、边以及它们之间的关系。
# 通过 __dict__() 方法返回 TreeSnapshot 对象的字典表示，便于序列化和存储。

from collections import defaultdict
from dataclasses import dataclass
from typing import NewType, Optional, Collection

# 定义节点ID、边ID、节点数据和边数据的类型别名
NodeId = NewType("NodeId", int)
EdgeId = NewType("EdgeId", int)
NodeData = NewType("NodeData", dict)
EdgeData = NewType("EdgeData", dict)


class TreeSnapshot:
    @dataclass
    class Node:
        # 定义表示树节点的内部类，包含节点ID、节点数据和选中的边ID（可选）
        id: NodeId
        data: NodeData
        selected_edge: Optional[EdgeId] = None

    @dataclass
    class Edge:
        # 定义表示树边的内部类，包含边ID、源节点ID、目标节点ID和边数据
        id: EdgeId
        source: NodeId
        target: NodeId
        data: EdgeData

    def __init__(self, nodes: Collection[Node], edges: Collection[Edge]) -> None:
        # 初始化 TreeSnapshot 对象，接受节点和边的集合作为参数
        self.nodes: dict[NodeId, TreeSnapshot.Node] = {node.id: node for node in nodes}  # 将节点按ID存储在字典中
        self.edges: dict[EdgeId, TreeSnapshot.Edge] = {edge.id: edge for edge in edges}  # 将边按ID存储在字典中
        self._parent = {}  # 存储每个节点的父节点ID
        self._children: dict[NodeId, set[NodeId]] = defaultdict(set)  # 存储每个节点的子节点ID集合

        for edge in edges:
            self._parent[edge.target] = edge.source  # 设置目标节点的父节点为源节点
            self._children[edge.source].add(edge.target)  # 将目标节点添加到源节点的子节点集合中

        assert len(self._parent) == len(self.nodes) - 1  # 断言父节点数量比节点数量少1（根节点没有父节点）
        assert self._connected()  # 断言树是连通的

    def _connected(self) -> bool:
        # 检查树是否连通的内部方法
        visited = set()  # 存储已访问过的节点ID
        queue = [next(iter(self.nodes))]  # 从任意一个节点开始遍历
        while queue:
            node = queue.pop()  # 取出队列中的节点
            visited.add(node)  # 将节点标记为已访问
            queue.extend(self._children[node] - visited)  # 将未访问过的子节点加入队列
        return len(visited) == len(self.nodes)  # 如果访问过的节点数等于总节点数，则树是连通的

    def node(self, node_id: NodeId) -> Node:
        # 根据节点ID返回对应的节点对象
        return self.nodes[node_id]

    def edge(self, edge_id: EdgeId) -> Edge:
        # 根据边ID返回对应的边对象
        return self.edges[edge_id]

    def out_edges(self, node_id: NodeId) -> Collection[Edge]:
        # 返回指定节点的出边集合
        return [self.edge(edge_id) for edge_id in self.edges if self.edge(edge_id).source == node_id]

    def in_edges(self, node_id: NodeId) -> Collection[Edge]:
        # 返回指定节点的入边集合
        return [self.edge(edge_id) for edge_id in self.edges if self.edge(edge_id).target == node_id]

    def parent(self, node_id: NodeId) -> NodeId:
        # 返回指定节点的父节点ID
        return self._parent[node_id]

    def children(self, node_id: NodeId) -> Collection[NodeId]:
        # 返回指定节点的子节点ID集合
        return self._children[node_id]

    def __dict__(self):
        # 返回 TreeSnapshot 对象的字典表示，包含节点和边的信息
        return {
            "nodes": self.nodes,
            "edges": self.edges,
        }