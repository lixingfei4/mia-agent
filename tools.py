"""Agent 工具：只允许有限的算术，不执行用户代码。"""
import ast
import math
import operator

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def calculate(expression):
    if not isinstance(expression, str) or len(expression) > 160:
        raise ValueError('算式最长 160 个字符')
    tree = ast.parse(expression.replace('×', '*').replace('÷', '/'), mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 60:
        raise ValueError('算式太复杂')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError('指数绝对值不能超过 10')
            value = OPS[type(node.op)](left, right)
        else:
            raise ValueError('仅支持数字、括号和 + - * / % **')
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
            raise ValueError('结果超出范围（最多一万亿）')
        return value
    return visit(tree.body)


def study_plan(topic='Python', minutes=60):
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 80:
        raise ValueError('主题应为 1–80 个字符')
    if type(minutes) is not int or not 15 <= minutes <= 180:
        raise ValueError('每日学习时间为 15–180 分钟')
    lessons = [
        ('认识与准备', '了解用途，准备学习环境', '完成一个最小示例，写下运行步骤'),
        ('基础概念', '学习 3 个核心概念', '用自己的话解释，并各做一个小练习'),
        ('动手练习', '复习昨天的概念', '独立完成一个基础任务并记录问题'),
        ('拆解问题', '把任务拆成输入、处理和输出', '分三步实现一个小功能'),
        ('处理错误', '学习常见错误和排查方法', '主动制造并修复两个错误'),
        ('迷你项目', '选择一个可在一天完成的小项目', '做出可运行版本，保存成果'),
        ('复盘与展示', '总结知识与未解决的问题', '整理说明，录制一分钟演示，制定下一周目标'),
    ]
    if 'python' in topic.lower():
        lessons = [
            ('环境与输出', '认识解释器、变量和 print', '输出自我介绍，修改三个变量'),
            ('数据与输入', '字符串、数字、input 和类型转换', '制作年龄或温度转换器'),
            ('条件判断', 'if / elif / else 与比较运算', '制作成绩评级器，测试边界值'),
            ('循环与列表', 'for、range 和列表', '统计一周学习分钟数'),
            ('函数与异常', 'def、参数、返回值和 try / except', '把计算器拆成函数，处理除零'),
            ('文件与小项目', '读写 UTF-8 文本文件', '实现学习记录保存功能'),
            ('复盘与展示', '梳理输入、函数、输出的关系', '整理 README 并演示学习记录程序'),
        ]
    parts = [f'# {topic.strip()} · 7 天学习计划', f'每天 {minutes} 分钟。建议理解占三分之一，练习占三分之二。',
             '这是可调整的入门模板，请根据实际进度增减任务。']
    for day, (title, learn, practice) in enumerate(lessons, 1):
        parts.append(f'## 第 {day} 天：{title}\n- 学习：{learn}\n- 实践：{practice}\n- 验收：留下可运行示例或一段自己的总结。')
    return '\n\n'.join(parts)
