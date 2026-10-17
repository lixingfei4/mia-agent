import io
import json
import unittest
from unittest.mock import patch
from tools import calculate, study_plan
from agent import demo_reply, ai_reply


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
            reply, traces, _ = ai_reply('125*36', [], 'fake-key', 'test-model', lambda: True)
        self.assertIn('4500', reply)
        self.assertEqual(calls[1]['messages'][-1]['content'], '4500')
        self.assertEqual(len(traces), 1)

    def test_quota_stops_network(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):
                ai_reply('你好', [], 'fake-key', 'test-model', lambda: False)
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
