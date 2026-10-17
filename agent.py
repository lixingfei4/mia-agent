"""演示路由与 Groq Function Calling 循环。密钥只在服务端读取。"""
import json
import re
import urllib.request
import urllib.error
from tools import calculate, study_plan

class AgentError(ValueError):
    """可安全显示给用户的错误，不包含服务端响应正文或凭据。"""


_MODEL_FALLBACKS = {}
FALLBACK_MODEL = 'openai/gpt-oss-120b'

SYSTEM_PROMPT = """你是 Mia，用自然、清楚的中文帮助用户学习、思考和沟通。
事实与表达：只把用户明确提供的信息作为已知事实。历史助手回复中的推测和示例不构成事实，用户重复问题时不要照搬先前回复中的细节。不要擅自补充动机、经历、时间、权限或承诺；缺少的信息要询问，或明确写成可选建议和条件。严格区分事情发生的时间与通知的时间，不能由通知晚推断对方提出要求也晚。避免套话、空泛安慰和过度道歉。
人际沟通：先回应对方具体受到的影响和情绪，承认自己可核实的责任；说明客观背景时不要把它当作免责理由。优先处理眼前的问题，例如询问最紧迫的困难、协商工作范围与优先级、确认哪些可以延期，并明确下一步由谁向谁确认。把长期制度或流程改进放在当前问题之后，不能只谈将来而回避已经发生的负担。
模拟对话：按用户要求的轮数写双方发言，每轮推进一个具体问题。使用可以直接说出口的短句，不把制度清单塞进台词。让对方保留合理顾虑、追问或不同意；只有当顾虑得到了具体回应，态度才逐步缓和，不强行以双方满意结束。不替任何一方保证客户同意、同事接受或问题一定解决。
工具：所有算术问题必须真正调用 calculate，不能只把工具参数或 JSON 写在回复里；七天学习计划必须调用 study_plan。只使用已提供的工具，不声称能访问电脑或浏览网页。文件只能通过页面实际提供的下载按钮下载，不编造 PDF、sandbox、/tmp 等文件链接。"""


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
    if not isinstance(key, str) or not key.startswith('gsk_') or not key.isascii() or any(c.isspace() for c in key):
        raise AgentError('Groq 密钥格式不正确：请在 Secrets 的 GROQ_API_KEY 中只填写以 gsk_ 开头的完整密钥，清除提示文字、空格和换行。')
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9./_-]+', model):
        raise AgentError('模型名称格式不正确，请检查 Secrets 中的 GROQ_MODEL，保留模型 ID 并去除空格或提示文字。')
    active_model = _MODEL_FALLBACKS.get(model, model)
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages += [{'role': m['role'], 'content': (m.get('plan') or m['content'])[:4000]} for m in history[-8:]]
    messages.append({'role': 'user', 'content': prompt})
    traces, plan = [], None
    for _ in range(3):
        if not reserve():
            raise AgentError('本小时共享 AI 请求额度已用完，请稍后再试或切换演示模式')
        payload = json.dumps({'model': active_model, 'messages': messages, 'tools': TOOLS,
                              'tool_choice': 'auto', 'max_tokens': 1200, 'temperature': 0.3}).encode()
        req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions', data=payload,
              headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                       'User-Agent': 'Mia-Agent/1.0', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                message = json.load(response)['choices'][0]['message']
        except urllib.error.HTTPError as exc:
            # 只分类已知网关错误，绝不向页面返回响应正文。
            error_body = exc.read(4096).decode('utf-8', errors='replace')
            exc.close()
            if exc.code == 404 and active_model != FALLBACK_MODEL:
                active_model = FALLBACK_MODEL
                _MODEL_FALLBACKS[model] = active_model
                traces.append('原模型不可用，已自动改用 GPT OSS 120B')
                continue
            if exc.code == 403 and '1010' in error_body:
                raise AgentError('Groq 网关拒绝了应用连接（HTTP 403 / 1010），需要检查客户端连接方式。') from None
            raise AgentError({
                400: '模型服务拒绝了请求（HTTP 400），请检查 GROQ_MODEL 是否支持当前工具调用。',
                401: 'Groq 密钥验证失败（HTTP 401），请检查 Secrets 中的 GROQ_API_KEY 是否为有效的新密钥。',
                403: 'Groq 拒绝访问（HTTP 403），请检查账户、模型权限及服务地区限制。',
                404: 'Groq 模型或接口不存在（HTTP 404），请检查 GROQ_MODEL。',
                429: 'Groq 免费额度或请求频率已达上限（HTTP 429），请稍后再试。',
            }.get(exc.code, f'Groq 暂时不可用（HTTP {exc.code}），请稍后重试。')) from None
        except (urllib.error.URLError, TimeoutError):
            raise AgentError('无法连接 Groq，请检查服务可达性，或稍后使用演示模式重试。') from None
        calls = message.get('tool_calls') or []
        if not calls:
            if plan:
                return plan + '\n\n请使用下方「下载 7 天学习计划」按钮保存 Markdown 文件。', traces, plan
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
