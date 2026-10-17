"""演示路由与 Groq Function Calling 循环。密钥只在服务端读取。"""
import json
import re
import urllib.request
import urllib.error
from tools import calculate, study_plan

TOOLS = [
    {'type': 'function', 'function': {'name': 'calculate', 'description': '计算算术表达式，所有算术问题必须使用此工具', 'parameters': {'type': 'object', 'properties': {'expression': {'type': 'string'}}, 'required': ['expression'], 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'study_plan', 'description': '生成可下载的七天学习计划', 'parameters': {'type': 'object', 'properties': {'topic': {'type': 'string'}, 'minutes': {'type': 'integer', 'minimum': 15, 'maximum': 180}}, 'required': ['topic', 'minutes'], 'additionalProperties': False}}},
]


def execute(name, args):
    if name == 'calculate':
        return str(calculate(**args)), None
    if name == 'study_plan':
        plan = study_plan(**args)
        return plan, plan
    raise ValueError('不支持的工具')


def demo_reply(prompt):
    if '计划' in prompt or '学习' in prompt:
        topic = 'Python' if 'python' in prompt.lower() else '编程入门'
        plan = study_plan(topic)
        return plan, ['study_plan：已生成 7 天计划（演示规则触发）'], plan
    match = re.search(r'[\d(][\d\s.+*/%()×÷−-]*', prompt)
    if match and any(c in match.group() for c in '+-*/%×÷'):
        expr = match.group().strip()
        result = calculate(expr)
        return f'计算结果：**{expr} = {result}**', [f'calculate({expr}) → {result}（演示规则触发）'], None
    return ('你好，我是 Mia！当前是**无需密钥的规则演示模式**，不具备自由 AI 对话能力。\n\n'
            '试试「帮我计算 125 × 36」或「制定 7 天 Python 学习计划」。接入 Groq 后可进行 AI 聊天。'), [], None


def ai_reply(prompt, history, key, model, reserve):
    messages = [{'role': 'system', 'content': '你是 Mia，友善的中文学习助手。所有计算必须调用 calculate；七天计划必须调用 study_plan。只使用允许的工具，不声称能访问电脑、浏览网页或保存文件。'}]
    messages += [{'role': m['role'], 'content': m['content'][:4000]} for m in history[-8:]]
    messages.append({'role': 'user', 'content': prompt})
    traces, plan = [], None
    for _ in range(3):
        if not reserve():
            raise ValueError('本小时共享 AI 请求额度已用完，请稍后再试或切换演示模式')
        payload = json.dumps({'model': model, 'messages': messages, 'tools': TOOLS,
                              'tool_choice': 'auto', 'max_tokens': 1200, 'temperature': 0.3}).encode()
        req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions', data=payload,
              headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                message = json.load(response)['choices'][0]['message']
        except urllib.error.HTTPError as exc:
            raise ValueError({401: 'API Key 无效，请检查服务端配置', 429: '免费额度或请求频率已达上限，请稍后再试'}.get(exc.code, '模型服务暂时不可用，请尝试演示模式')) from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('无法连接模型服务，请检查网络或使用演示模式') from None
        calls = message.get('tool_calls') or []
        if not calls:
            return message.get('content') or '模型未返回文本，请重试。', traces, plan
        if len(calls) > 4:
            raise ValueError('工具请求过多，请缩小任务')
        messages.append({k: message[k] for k in ('role', 'content', 'tool_calls') if k in message})
        for call in calls:
            name = call['function']['name']
            try:
                args = json.loads(call['function']['arguments'])
                result, artifact = execute(name, args)
                if artifact:
                    plan = artifact
                traces.append(f'{name} → 已完成')
            except (ValueError, TypeError, SyntaxError, ArithmeticError):
                result = '工具参数无效或计算超出限制，请修正后重试'
                traces.append(f'{name} → 参数错误')
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': result})
    return '已达到工具调用轮数限制。' + ('学习计划已生成，可在下方下载。' if plan else '请简化请求后重试。'), traces, plan
