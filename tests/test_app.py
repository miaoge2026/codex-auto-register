"""Flask Web 接口测试。"""

from pathlib import Path

import pytest

import app as web_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    web_app.app.config['TESTING'] = True

    with web_app.status_lock:
        web_app.registration_status.update(
            {
                'is_running': False,
                'is_continuous': False,
                'success_count': 0,
                'fail_count': 0,
                'current_email': '',
                'start_time': None,
                'log_content': [],
                'proxy': web_app.Config.DEFAULT_PROXY,
            }
        )

    yield web_app.app.test_client()


def test_status_serializes_datetime(client):
    with web_app.status_lock:
        web_app.registration_status['start_time'] = web_app.datetime(2026, 1, 1, 12, 0, 0)

    response = client.get('/api/status')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['start_time'] == '2026-01-01T12:00:00'


def test_logs_endpoint_clamps_requested_lines(client):
    for index in range(600):
        web_app.log_info(f'line-{index}')

    response = client.get('/api/logs?lines=9999')

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload['logs']) == web_app.MAX_LOG_RESPONSE_LINES
    assert payload['logs'][0].endswith('line-100')
    assert payload['logs'][-1].endswith('line-599')


def test_resolve_json_file_blocks_path_traversal(client):
    outside_file = Path('..') / 'outside.json'
    outside_file.write_text('{"secret": true}', encoding='utf-8')

    with pytest.raises(Exception) as exc_info:
        web_app._resolve_json_file('../outside.json')

    assert getattr(exc_info.value, 'code', None) == 400


def test_file_endpoint_reads_local_json(client):
    Path('accounts.json').write_text('{"email": "demo@example.com"}', encoding='utf-8')

    response = client.get('/api/files/accounts.json')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert 'demo@example.com' in payload['content']
