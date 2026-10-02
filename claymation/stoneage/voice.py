#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 사람들은 뭐 하고 놀았을까? — 타입캐스트(Typecast) API로 내레이션 만들기

  export TYPECAST_API_KEY=...          # 타입캐스트 API 콘솔에서 만든 키 (환경 변수로만 넣는다)
  export TYPECAST_VOICE_ID=tc_...      # (선택) 쓸 목소리. 없으면 설명에 맞는 목소리를 추천받아 첫 번째를 쓴다
  python3 voice.py [--only f01,f02] [--force]

script.py의 줄마다 build/stoneage/voice/<id>.wav를 만든다(이미 있으면 건너뜀).
앞뒤 문맥을 함께 보내는 스마트 감정으로, 차분한 다큐 내레이션 톤.
build.py는 이 파일 길이로 타임라인·자막을 다시 짠다.
"""
import base64, json, os, sys, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import LINES                                  # noqa: E402

API = 'https://api.typecast.ai'
MODEL = 'ssfm-v30'
VOICE_QUERY = '차분하고 따뜻한 한국어 다큐멘터리 내레이터, 지식 유튜브, 또렷한 발음'
OUT = os.path.join(os.path.dirname(HERE), 'build', 'stoneage', 'voice')


def request(method, path, key, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header('X-API-KEY', key)
    req.add_header('User-Agent', 'typecast-direct/1 python yt-research-claymation/1')
    if body is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'Typecast {method} {path}: HTTP {e.code} {e.read()[:300]!r}')


def pick_voice(key):
    """TYPECAST_VOICE_ID가 없으면 설명으로 추천받되, 스마트 감정을 쓰는 ssfm-v30을 지원하는 목소리만 고른다."""
    vid = os.environ.get('TYPECAST_VOICE_ID')
    if vid:
        return vid
    q = urllib.parse.urlencode({'query': VOICE_QUERY, 'count': 10})
    recs = request('GET', f'/v1/voices/recommendations?{q}', key)
    v30 = {v['voice_id']: v for v in request('GET', f'/v3/voices?model={MODEL}', key)}
    ok = [r for r in recs if r['voice_id'] in v30]
    for r in ok:
        v = v30[r['voice_id']]
        name = v.get('voice_name') or {}
        print(f"  추천 목소리: {r['voice_id']} {name.get('kor') or name.get('eng')} "
              f"({v.get('gender')}, {v.get('age')}, {', '.join(v.get('use_cases') or [])}) "
              f"score {r.get('score')}  미리 듣기: {v.get('preview_url')}")
    if not ok:
        sys.exit(f'{MODEL}을 지원하는 추천 목소리가 없습니다. TYPECAST_VOICE_ID로 직접 지정하세요.')
    return ok[0]['voice_id']


def main():
    a = sys.argv[1:]
    key = os.environ.get('TYPECAST_API_KEY', '').strip()
    if not key:
        sys.exit('TYPECAST_API_KEY 환경 변수가 없습니다.')
    only = set(a[a.index('--only') + 1].split(',')) if '--only' in a else None
    os.makedirs(OUT, exist_ok=True)
    voice = pick_voice(key)
    print('voice:', voice)
    for i, L in enumerate(LINES):
        if only and L['id'] not in only:
            continue
        path = os.path.join(OUT, L['id'] + '.wav')
        if os.path.exists(path) and '--force' not in a:
            continue
        body = {
            'model': MODEL, 'voice_id': voice, 'text': L['tts'], 'language': 'kor', 'seed': 11,
            'prompt': {'emotion_type': 'smart',
                       'previous_text': LINES[i - 1]['tts'] if i else '',
                       'next_text': LINES[i + 1]['tts'] if i + 1 < len(LINES) else ''},
            'output': {'audio_format': 'wav', 'audio_tempo': 1.0, 'remove_silence_ms': 250, 'target_lufs': -16},
        }
        r = request('POST', '/v1/text-to-speech/with-timestamps?granularity=word', key, body)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(r['audio']))
        json.dump(r.get('words') or [], open(path[:-4] + '.json', 'w'), ensure_ascii=False)
        print(f"  {L['id']}: {r['audio_duration']:.2f}s  {L['sub'][:30]}")
    json.dump({'voice_id': voice, 'model': MODEL}, open(os.path.join(OUT, 'voice.json'), 'w'))


if __name__ == '__main__':
    main()
