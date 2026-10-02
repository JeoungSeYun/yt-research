#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
옛날 사람들은 뭐 하고 놀았을까? — 타입캐스트(Typecast) API로 내레이션 만들기

  export TYPECAST_API_KEY=...          # 타입캐스트 API 콘솔에서 만든 키 (환경 변수로만 넣는다)
  export TYPECAST_VOICE_ID=tc_...      # (선택) 쓸 목소리. 없으면 설명에 맞는 목소리를 추천받아 첫 번째를 쓴다
  python3 oldfun_voice.py build/oldfun

장면마다 한 줄씩 만들어 voice_1~3.wav로 저장하고, 단어별 시간 정보로 자막(subs.ass)과
배치 정보(voice.json)를 쓴다. 줄이 장면 길이보다 길면 말 빠르기를 올려 다시 만든다.
"""
import base64, json, os, sys, urllib.parse, urllib.request

API = 'https://api.typecast.ai'
MODEL = 'ssfm-v30'
VOICE_QUERY = '밝고 다정한 한국어 여성 내레이터, 어린이 교육 쇼츠, 또박또박 경쾌한 말투'

# (말할 문장, 자막, 장면 안에서 시작할 시각, 끝나야 하는 시각). 숫자는 읽는 그대로 한글로 적는다.
LINES = [
    ('폰도 없던 옛날엔 뭐 하고 놀았을까? 약 사만 년 전엔 뼈 피리를 불었어요!',
     ['폰도 없던 옛날엔 뭐 하고 놀았을까?', '약 4만 년 전엔 {Y}뼈 피리{W}를 불었어요!'], 0.08, 4.95),
    ('약 오천 년 전 이집트 사람들은 세네트라는 보드게임을 했고요,',
     ['약 5천 년 전 이집트 사람들은\\N{Y}\'세네트\'{W}라는 보드게임을 했고요,'], 5.22, 9.6),
    ('이천 년도 더 전 그리스에선 양의 뼈로 공기놀이 같은 놀이를 했대요!',
     ['2천 년도 더 전 그리스에선 양의 뼈로\\N{Y}공기놀이{W} 같은 놀이를 했대요!'], 10.12, 14.45),
]

ASS_HEAD = r"""[Script Info]
; 옛날 사람들은 뭐 하고 놀았을까? — 자막 (oldfun_voice.py가 내레이션 타이밍으로 만든 파일)
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,NanumSquareRound,66,&H00FFFFFF,&H00FFFFFF,&H00142235,&H8C000000,-1,0,0,0,100,100,0,0,1,5.5,2.5,2,80,80,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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
    vid = os.environ.get('TYPECAST_VOICE_ID')
    if vid:
        return vid
    q = urllib.parse.urlencode({'query': VOICE_QUERY, 'count': 5})
    recs = request('GET', f'/v1/voices/recommendations?{q}', key)
    for r in recs:
        print(f"  추천 목소리: {r['voice_id']} {r.get('voice_name')} (score {r.get('score')})")
    return recs[0]['voice_id']


def tts(key, voice, text, prev, nxt, tempo):
    body = {
        'model': MODEL, 'voice_id': voice, 'text': text, 'language': 'kor', 'seed': 7,
        'prompt': {'emotion_type': 'smart', 'previous_text': prev, 'next_text': nxt},
        'output': {'audio_format': 'wav', 'audio_tempo': round(tempo, 3), 'remove_silence_ms': 180,
                   'target_lufs': -16},
    }
    return request('POST', '/v1/text-to-speech/with-timestamps?granularity=word', key, body)


def ts(t):
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'build/oldfun'
    key = os.environ.get('TYPECAST_API_KEY', '').strip()
    if not key:
        sys.exit('TYPECAST_API_KEY 환경 변수가 없습니다.')
    voice = pick_voice(key)
    print('voice:', voice)
    placed, events = [], []
    for i, (text, subs, start, end) in enumerate(LINES):
        prev = LINES[i - 1][0] if i else ''
        nxt = LINES[i + 1][0] if i + 1 < len(LINES) else ''
        tempo = 1.1
        for _ in range(3):                                   # 장면에 안 들어가면 조금 빠르게 다시
            r = tts(key, voice, text, prev, nxt, tempo)
            words = [w for w in (r.get('words') or []) if w.get('text', '').strip()]
            dur = words[-1]['end'] if words else r['audio_duration']
            if start + dur <= end or tempo >= 1.5:
                break
            tempo = min(1.5, tempo * (dur / (end - start)) * 1.02)
        lead = words[0]['start'] if words else 0.0            # 앞 무음만큼 당겨서 놓는다
        name = f'voice_{i + 1}.wav'
        with open(os.path.join(out, name), 'wb') as f:
            f.write(base64.b64decode(r['audio']))
        t0 = start - lead
        placed.append({'file': name, 'start': round(t0, 3), 'speech': [round(start, 3), round(t0 + dur, 3)],
                       'tempo': round(tempo, 3)})
        print(f'  {name}: {dur:.2f}s (tempo {tempo:.2f}) {start:.2f}–{t0 + dur:.2f}')
        if len(subs) == 1:                                    # 자막은 장면이 끝날 때까지 둔다
            events.append((start - 0.05, end + 0.15, subs[0]))
        else:                                                 # 두 문장: '?' 뒤 첫 단어에서 자막을 바꾼다
            k = next(j for j, w in enumerate(words) if w['text'].rstrip().endswith('?')) + 1
            cut = t0 + words[k]['start'] - 0.05
            events += [(start - 0.05, cut, subs[0]), (cut, end + 0.05, subs[1])]
    with open(os.path.join(out, 'subs.ass'), 'w') as f:
        f.write(ASS_HEAD)
        for a, b, s in events:
            s = s.replace('{Y}', r'{\c&H0038D8FF&}').replace('{W}', r'{\c&H00FFFFFF&}')
            f.write(f'Dialogue: 0,{ts(max(0, a))},{ts(min(b, 14.6))},Sub,,0,0,0,,{s}\n')
    json.dump({'voice_id': voice, 'model': MODEL, 'lines': placed}, open(os.path.join(out, 'voice.json'), 'w'),
              ensure_ascii=False, indent=1)
    print('wrote voice_1~3.wav, subs.ass, voice.json')


if __name__ == '__main__':
    main()
