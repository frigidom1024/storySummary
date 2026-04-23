"""分步调试节点生成过程

用法:
    python scripts/debug_node_generation.py --phase 1  # 测试 Phase 1: 节点提取
    python scripts/debug_node_generation.py --phase 2  # 测试 Phase 2: 时间锚点
    python scripts/debug_node_generation.py --phase 3  # 测试 Phase 3: 图谱构建
    python scripts/debug_node_generation.py --phase all # 完整流程
"""
import os
import sys
import json
import asyncio
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

# 测试文本 - 使用 wind.txt 的第一章
TEST_TEXT = """青岛路旧书店，下午三点多。

陈屿第三次拿起那本《围城》，又放下了。扉页上的签名让他心绪复杂——"林知夏"，这名字他翻了三年才在旧书店找到。

"你要不买，别人可就买了。"店员的声音打断了他的思绪。

陈屿没有说话，只是把书买了下来。

然后坐了两个小时，读完了整本书。

又花了一周，把林知夏的朋友圈从第一条翻到最后一条。

她喜欢摄影，讨厌香菜，会在深夜发一些没人听的歌单。

陈屿在某条状态下停留了很久：没有完美的生活，只有短暂的停留。

然后他就做了一个决定。"""

# Phase 2 需要用到的测试节点
TEST_NODES = [
    {"id": "n-0-0", "scene": "青岛路旧书店，下午三点多", "characters": [{"name": "陈屿"}], "beat_index": 0},
    {"id": "n-0-1", "scene": "陈屿第三次拿起那本《围城》", "characters": [{"name": "陈屿"}], "beat_index": 1},
    {"id": "n-0-2", "scene": "店员的声音打断了他的思绪", "characters": [{"name": "陈屿"}, {"name": "店员"}], "beat_index": 2},
    {"id": "n-0-3", "scene": "陈屿没有说话，只是把书买了下来", "characters": [{"name": "陈屿"}], "beat_index": 3},
    {"id": "n-0-4", "scene": "坐了两个小时，读完了整本书", "characters": [{"name": "陈屿"}], "beat_index": 4},
    {"id": "n-0-5", "scene": "花了一周翻完林知夏的朋友圈", "characters": [{"name": "陈屿"}, {"name": "林知夏"}], "beat_index": 5},
    {"id": "n-0-6", "scene": "陈屿做了某个决定", "characters": [{"name": "陈屿"}], "beat_index": 6},
]


def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def save_json(data, filename):
    """保存结果到文件供下一步使用"""
    path = os.path.join(root_dir, "data", "debug", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [已保存] {path}")
    return path


def load_json(filename):
    """加载上一步的结果"""
    path = os.path.join(root_dir, "data", "debug", filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


async def phase1_test_beat_extraction():
    """Phase 1: 测试基础节点提取"""
    print_section("Phase 1: 节点提取 (Beat Extraction)")

    from src.core.node_generator import NarrativeNodeGenerator
    from src.models.chunk import Chunk

    print(f"\n输入文本长度: {len(TEST_TEXT)} 字符")

    # 创建 Chunk 对象
    chunk = Chunk(id="debug-001", text=TEST_TEXT.strip(), order=0)

    # 生成节点
    generator = NarrativeNodeGenerator()

    print("\n[1] 调用 LLM 提取节点...")
    nodes = await generator.generate_from_chunk(chunk)

    print(f"\n[2] 提取结果: {len(nodes)} 个节点")
    for i, node in enumerate(nodes):
        print(f"\n  节点 {i+1}: {node.id}")
        print(f"    scene: {node.scene[:50]}..." if len(node.scene) > 50 else f"    scene: {node.scene}")
        print(f"    characters: {[c.name for c in node.characters]}")
        print(f"    importance: {node.importance}")

    # 保存结果供 Phase 2 使用
    nodes_data = [n.model_dump() for n in nodes]
    save_json(nodes_data, "phase1_nodes.json")

    print("\n[3] 验证要点:")
    print("    [OK] scene 是否简洁描述了场景?")
    print("    [OK] characters 是否正确识别?")
    print("    [OK] importance 是否反映节点重要性?")
    print("    [OK] interactions 是否描述角色互动?")

    return nodes_data


async def phase2_test_time_anchor(prev_nodes=None):
    """Phase 2: 测试时间锚点解析"""
    print_section("Phase 2: 时间锚点 (Time Anchor)")

    if prev_nodes is None:
        prev_nodes = load_json("phase1_nodes.json")
        if prev_nodes is None:
            print("  [错误] 请先运行 Phase 1")
            return None

    print(f"\n输入: {len(prev_nodes)} 个节点")

    from src.core.time_anchor_resolver import TimeAnchorResolver

    resolver = TimeAnchorResolver()

    print("\n[1] 调用 LLM 解析时间锚点...")
    time_anchors = await resolver.resolve(prev_nodes, last_timeline_state={})

    print(f"\n[2] 时间锚点结果: {len(time_anchors)} 个")
    for i, ta in enumerate(time_anchors):
        print(f"\n  锚点 {i+1}: {ta.node_id}")
        print(f"    time_type: {ta.time_type}")
        print(f"    relative_to_prev: {ta.relative_to_prev}")
        print(f"    anchor_hint: {ta.anchor_hint}")
        print(f"    confidence: {ta.confidence}")

    # 保存结果
    anchors_data = [ta.model_dump() for ta in time_anchors]
    save_json(anchors_data, "phase2_anchors.json")

    print("\n[3] 验证要点:")
    print("    ✓ time_type 是否正确 (present/past/future)?")
    print("    ✓ relative_to_prev 是否正确 (continue/jump)?")
    print("    ✓ 时间跳转是否有标记 (jump)?")

    return anchors_data


async def phase3_test_graph_builder(prev_nodes=None, time_anchors=None):
    """Phase 3: 测试图谱构建"""
    print_section("Phase 3: 图谱构建 (Graph Builder)")

    if prev_nodes is None:
        prev_nodes = load_json("phase1_nodes.json")
        if prev_nodes is None:
            print("  [错误] 请先运行 Phase 1")
            return None

    if time_anchors is None:
        time_anchors = load_json("phase2_anchors.json")
        if time_anchors is None:
            print("  [错误] 请先运行 Phase 2")
            return None

    print(f"\n输入: {len(prev_nodes)} 个节点, {len(time_anchors)} 个时间锚点")

    from src.core.graph_builder import GraphBuilder

    builder = GraphBuilder()

    print("\n[1] 调用 LLM 构建图谱...")
    result_nodes = await builder.build(prev_nodes, time_anchors)

    print(f"\n[2] 图谱构建结果: {len(result_nodes)} 个节点")

    # 按 thread 分组展示
    threads = {}
    for node in result_nodes:
        thread_id = node.get("thread_id", "main")
        if thread_id not in threads:
            threads[thread_id] = []
        threads[thread_id].append(node)

    for thread_id, nodes in threads.items():
        print(f"\n  线程 [{thread_id}]: {len(nodes)} 个节点")
        for node in nodes:
            print(f"    - {node['id']}: timeline_order={node.get('timeline_order', 0)}, "
                  f"prev={node.get('thread_prev_node_id', 'none')[:20] if node.get('thread_prev_node_id') else 'none'}")

    # 保存结果
    save_json(result_nodes, "phase3_graph.json")

    print("\n[3] 验证要点:")
    print("    ✓ thread_id 是否正确分组 (main/line_xxx)?")
    print("    ✓ timeline_order 是否正确排序?")
    print("    ✓ thread_prev_node_id 是否形成正确链路?")
    print("    ✓ 是否正确识别 is_time_jump?")

    return result_nodes


async def run_all():
    """完整流程"""
    print_section("完整节点生成流程调试")
    print(f"测试文本: {len(TEST_TEXT)} 字符")

    # Phase 1
    nodes = await phase1_test_beat_extraction()

    # Phase 2
    anchors = await phase2_test_time_anchor(nodes)

    # Phase 3
    graph = await phase3_test_graph_builder(nodes, anchors)

    print_section("调试完成")
    print("\n各阶段结果已保存到 data/debug/ 目录:")
    print("  - phase1_nodes.json: 节点提取结果")
    print("  - phase2_anchors.json: 时间锚点结果")
    print("  - phase3_graph.json: 图谱构建结果")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="分步调试节点生成")
    parser.add_argument("--phase", "-p", default="all",
                        choices=["1", "2", "3", "all"],
                        help="选择调试的阶段 (1: 节点提取, 2: 时间锚点, 3: 图谱构建, all: 全部)")
    args = parser.parse_args()

    if args.phase == "all":
        asyncio.run(run_all())
    elif args.phase == "1":
        asyncio.run(phase1_test_beat_extraction())
    elif args.phase == "2":
        asyncio.run(phase2_test_time_anchor())
    elif args.phase == "3":
        asyncio.run(phase3_test_graph_builder())
