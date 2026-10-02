"""阅读页的顺序与内容必须来自真实事件，不能用最终状态覆盖中途提交。"""
from business_analysis_repro.case_viewer.timeline import project_timeline


def test_original_submission_is_preserved_with_return_and_order():
    wrong = {'tasks': [{'period': {'start': '2026-08-17', 'end': '2026-08-30'}}]}
    events = [
        {'kind': 'model_response', 'seq': 1, 'tool_calls': [{'name': 'finish_plan', 'args': wrong}]},
        {'kind': 'span_start', 'seq': 2, 'span_id': 'submit', 'category': 'tool',
         'name': 'finish_plan', 'inputs': wrong},
        {'kind': 'span_end', 'seq': 3, 'span_id': 'submit', 'status': 'ok',
         'output': {'result': {'validation': {'accepted': False, 'errors': ['版本未填']}}}},
        {'kind': 'model_response', 'seq': 4, 'content': '继续检查参数'},
        {'kind': 'model_response', 'seq': 5, 'content': '最终回复'},
    ]
    result = project_timeline(events, [{'id': 'submit', 'role': '模型调用工具'}], '最终回复')
    assert [x['seq'] for x in result] == [2, 4]
    assert result[0]['input'] == wrong
    assert result[0]['output']['result']['validation']['accepted'] is False
    assert result[1]['text'] == '继续检查参数'


def test_unexecuted_request_is_not_presented_as_completed_tool():
    events = [{'kind': 'model_response', 'seq': 1,
               'tool_calls': [{'name': 'search_metrics', 'args': {'query': '保费'}}]},
              {'kind': 'model_error', 'seq': 2, 'error': '调用失败'}]
    result = project_timeline(events, [], '')
    assert result[0]['status'] == 'not_recorded'
    assert result[0]['output'] is None
    assert result[1]['kind'] == 'error'


def test_validation_does_not_leak_offline_expectations_into_execution():
    events = [{'kind': 'experiment_inspection', 'seq': 1,
               'validation': {'accepted': True}, 'expected': {'secret_gold': '不能出现在执行轨迹'}}]
    result = project_timeline(events, [], '')
    assert result == [{'id': 'event-1', 'seq': 1, 'kind': 'validation', 'validation': {'accepted': True}}]


def test_program_feedback_stays_between_submissions_without_repeating_history():
    initial = [{'type': 'system', 'content': '系统配置'},
               {'type': 'human', 'content': '用户问题及组装上下文'}]
    corrected = initial + [{'type': 'ai', 'content': ''},
                           {'type': 'tool', 'content': '{"accepted_for_validation": true}'},
                           {'type': 'human', 'content': '尚缺省份枚举，请补齐检索'}]
    events = [
        {'kind': 'model_request', 'seq': 1, 'messages': initial},
        {'kind': 'span_start', 'seq': 2, 'span_id': 'first', 'category': 'tool',
         'name': 'finish_resolution', 'inputs': {'requests': ['原始参数']}},
        {'kind': 'model_request', 'seq': 3, 'messages': corrected},
        {'kind': 'model_request', 'seq': 4, 'messages': corrected},
        {'kind': 'span_start', 'seq': 5, 'span_id': 'second', 'category': 'tool',
         'name': 'finish_resolution', 'inputs': {'requests': ['再次提交']}},
        # 截断或重写的上下文不冒充程序新反馈。
        {'kind': 'model_request', 'seq': 6,
         'messages': [{'type': 'human', 'content': '替换后的用户上下文'}]},
    ]
    result = project_timeline(events, [], '')
    assert [x['kind'] for x in result] == ['tool', 'feedback', 'tool']
    assert [x['seq'] for x in result] == [2, 3, 5]
    assert result[1]['text'] == '尚缺省份枚举，请补齐检索'
    assert result[0]['input']['requests'] == ['原始参数']
    assert result[2]['input']['requests'] == ['再次提交']
