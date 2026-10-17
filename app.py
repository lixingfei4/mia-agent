import os
import time
import threading
import hmac
import streamlit as st
from agent import AgentError, demo_reply, ai_reply

st.set_page_config(page_title='Mia Agent 1.0', page_icon='🌱', layout='centered')


def setting(name, default=''):
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default


@st.cache_resource
def shared_quota():
    return {'hour': int(time.time() // 3600), 'used': 0, 'lock': threading.Lock()}


def reserve():
    quota = shared_quota()
    with quota['lock']:
        hour = int(time.time() // 3600)
        if hour != quota['hour']:
            quota.update(hour=hour, used=0)
        if quota['used'] >= 30:
            return False
        quota['used'] += 1
        return True


st.title('🌱 Mia Agent 1.0')
st.caption('你的学习搭子 · 计算工具 · 七天学习计划')
key = setting('GROQ_API_KEY')
password = setting('ACCESS_PASSWORD')
with st.sidebar:
    st.header('开始体验')
    mode = st.radio('运行模式', ['免费演示', 'AI 聊天'])
    st.caption('免费演示使用规则和模板，完全不调用模型。')
    st.info('可输入：帮我计算 125 × 36\n\n或：制定 7 天 Python 学习计划')
    if st.button('清空对话'):
        st.session_state.messages = []
        st.rerun()
    st.caption('每个会话最多 20 次提交，间隔至少 3 秒；全站每小时最多 30 次模型请求。重启会重置计数。')

st.session_state.setdefault('messages', [])
st.session_state.setdefault('submits', 0)
st.session_state.setdefault('last_submit', 0.0)
if mode == 'AI 聊天':
    st.warning('对话会发送给 Groq。请勿输入密码、个人隐私或其他敏感信息。')
    if not key:
        st.info('尚未配置 GROQ_API_KEY，请先体验免费演示。')
        st.stop()
    if not password:
        st.info('AI 模式需要服务端设置 ACCESS_PASSWORD，避免公开消耗账户额度。')
        st.stop()
    entered = st.text_input('AI 体验口令', type='password')
    if not hmac.compare_digest(entered.encode(), str(password).encode()):
        if entered:
            st.error('体验口令不匹配。请输入与 Secrets 中 ACCESS_PASSWORD 完全相同的内容；如果刚修改过配置，请等待约一分钟后刷新。')
        else:
            st.info('请输入你为 Mia 设置的体验口令，然后按回车。')
        st.stop()
else:
    st.info('当前是规则演示模式：计算和下载可用；接入 API 后才支持自由 AI 聊天。')

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message['role']):
        st.markdown(message.get('plan') or message['content'])
        if message.get('traces'):
            with st.expander('查看工具调用记录'):
                for trace in message['traces']:
                    st.text(trace)
        if message.get('plan'):
            st.download_button('下载 7 天学习计划', message['plan'].encode('utf-8-sig'),
                               'mia-study-plan.md', 'text/markdown', key=f'download-{index}')

prompt = st.chat_input('例如：帮我计算 125 × 36', max_chars=1000)
if prompt:
    now = time.time()
    if st.session_state.submits >= 20:
        st.warning('本会话已达 20 次提交上限。')
        st.stop()
    if now - st.session_state.last_submit < 3:
        st.warning('请间隔 3 秒再提交。')
        st.stop()
    st.session_state.submits += 1
    st.session_state.last_submit = now
    history = st.session_state.messages.copy()
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.spinner('Mia 正在处理…'):
        try:
            if mode == '免费演示':
                answer, traces, plan = demo_reply(prompt)
            else:
                answer, traces, plan = ai_reply(prompt, history, key,
                    setting('GROQ_MODEL', 'openai/gpt-oss-120b'), reserve)
        except AgentError as exc:
            answer, traces, plan = str(exc), [], None
        except (ValueError, TypeError, SyntaxError, ArithmeticError):
            answer, traces, plan = '本次请求未完成。请检查算式、API 配置、网络或免费额度后重试。', [], None
    st.session_state.messages.append({'role': 'assistant', 'content': answer, 'traces': traces, 'plan': plan})
    st.rerun()
