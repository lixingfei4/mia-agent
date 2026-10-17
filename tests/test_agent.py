import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from tools import calculate, study_plan
from agent import AgentError, SYSTEM_PROMPT, demo_reply, ai_reply


class AgentTests(unittest.TestCase):
    def test_calculation_and_security(self):
        self.assertEqual(calculate('125 × 36'), 4500)
        self.assertEqual(calculate('-(2+3)*4'), -20)
        for bad in ["__import__('os').system('id')", '2**10000', '1/0', '9'*200, '1e100', 'True+1']:
            with self.subTest(bad=bad), self.assertRaises((ValueError, SyntaxError, ArithmeticError)):
                calculate(bad)

    def test_plan_and_demo(self):
        plan = study_plan('Python', 60)
        self.assertEqual(plan.count('## 第 '), 7)
        self.assertEqual(demo_reply('帮我计算 125 × 36')[0], '计算结果：**125 × 36 = 4500**')
        self.assertIsNotNone(demo_reply('制定 7 天 Python 学习计划')[2])

    def test_model_tool_roundtrip(self):
        responses = [
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': '1', 'type': 'function', 'function': {'name': 'calculate', 'arguments': '{"expression":"125*36"}'}}]},
            {'role': 'assistant', 'content': '结果是 4500。'},
        ]
        calls = []
        def fake_open(request, **kwargs):
            calls.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': responses.pop(0)}]}).encode())
        with patch('urllib.request.urlopen', side_effect=fake_open):
            reply, traces, _ = ai_reply('125*36', [], 'gsk_fake_key', 'test-model', lambda: True)
        self.assertIn('4500', reply)
        self.assertEqual(calls[1]['messages'][-1]['content'], '4500')
        self.assertEqual(len(traces), 1)

    def test_http_error_is_safe_and_actionable(self):
        error = urllib.error.HTTPError('https://api.groq.com', 401, 'private response', {}, io.BytesIO(b'secret-provider-body'))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(AgentError) as caught:
                ai_reply('你好', [], 'gsk_private_key', 'test-model', lambda: True)
        self.assertIn('401', str(caught.exception))
        self.assertNotIn('gsk_private_key', str(caught.exception))
        self.assertNotIn('secret-provider-body', str(caught.exception))

    def test_placeholder_key_never_reaches_network(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(AgentError) as caught:
                ai_reply('你好', [], '提示文字', 'test-model', lambda: True)
            self.assertIn('密钥格式', str(caught.exception))
            network.assert_not_called()

    def test_unavailable_model_falls_back(self):
        calls = []
        def fallback_open(request, **kwargs):
            calls.append(json.loads(request.data))
            if len(calls) == 1:
                raise urllib.error.HTTPError('https://api.groq.com', 404, 'Not Found', {}, io.BytesIO(b'{}'))
            return io.BytesIO(json.dumps({'choices': [{'message': {'role': 'assistant', 'content': '你好'}}]}).encode())
        with patch('urllib.request.urlopen', side_effect=fallback_open):
            answer, traces, _ = ai_reply('你好', [], 'gsk_fake_key', 'unavailable-model', lambda: True)
        self.assertEqual(answer, '你好')
        self.assertEqual(calls[1]['model'], 'openai/gpt-oss-120b')
        self.assertEqual(calls[1]['messages'][0]['role'], 'user')
        self.assertIn(SYSTEM_PROMPT, calls[1]['messages'][0]['content'])
        self.assertTrue(traces)

    def test_reasoning_model_keeps_history_and_tool_messages(self):
        history = [{'role': 'user', 'content': '之前的问题'}, {'role': 'assistant', 'content': '之前的回答'}]
        responses = [
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c', 'type': 'function', 'function': {'name': 'calculate', 'arguments': '{"expression":"6*7"}'}}]},
            {'role': 'assistant', 'content': '42'},
        ]
        calls = []
        def fake_open(request, **kwargs):
            calls.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': responses.pop(0)}]}).encode())
        with patch('urllib.request.urlopen', side_effect=fake_open):
            reply, _, _ = ai_reply('6*7', history, 'gsk_fake_key', 'openai/gpt-oss-120b', lambda: True)
        self.assertEqual(reply, '42')
        self.assertEqual(calls[1]['messages'][:2], history)
        self.assertEqual(calls[0]['messages'][2], calls[1]['messages'][2])
        self.assertEqual(calls[1]['messages'][2]['content'].count(SYSTEM_PROMPT), 1)
        self.assertEqual(calls[1]['messages'][-1], {'role': 'tool', 'tool_call_id': 'c', 'content': '42'})
        self.assertEqual(calls[1]['reasoning_format'], 'hidden')
        self.assertNotIn(SYSTEM_PROMPT, history[0]['content'])

    def test_plan_download_uses_real_tool_artifact(self):
        responses = [
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'p', 'type': 'function', 'function': {'name': 'study_plan', 'arguments': '{"topic":"Python","minutes":45}'}}]},
            {'role': 'assistant', 'content': '下载不存在的 PDF: sandbox:/tmp/plan.pdf'},
        ]
        def fake_open(request, **kwargs):
            return io.BytesIO(json.dumps({'choices': [{'message': responses.pop(0)}]}).encode())
        with patch('urllib.request.urlopen', side_effect=fake_open):
            answer, traces, plan = ai_reply('制定七天学习计划', [], 'gsk_fake_key', 'test-model', lambda: True)
        self.assertEqual(plan.count('## 第 '), 7)
        self.assertIn('45 分钟', plan)
        self.assertIn(plan, answer)
        self.assertNotIn('sandbox:', answer)

    def test_quota_stops_network(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):
                ai_reply('你好', [], 'gsk_fake_key', 'test-model', lambda: False)
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
