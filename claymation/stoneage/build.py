#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 사람들은 뭐 하고 놀았을까? — 8분 영상 조립

script.py의 내레이션 줄(LINES)과 장면(SHOTS)으로 타임라인을 짜고,
  1) 장면마다 1920×1080 조각 영상을 만든다
     - 사진: 4K로 키운 뒤 천천히 줌/팬 (12fps로 움직여 한 장씩 두 번 = 스톱모션 카메라 느낌)
     - 영상: Kling 클립을 짝수 장만 남겨 on twos, 길이가 모자라면 조금 느리게, 그래도 모자라면 마지막 장을 잡아 둔다
     - 그레인·비네팅·조명 깜빡임도 여기서(12fps) 입혀 한 장 안에서는 그대로 머물게 한다
  2) 조각을 이어 붙이고, 자막(테두리 없이 부드러운 그림자만)과 소리를 얹어 인코딩한다

내레이션 파일(build/stoneage/voice/<줄 id>.wav)이 있으면 그 길이를, 없으면 글자 수로 어림한 길이를 쓴다.

  python3 build.py            # 전체
  python3 build.py --plan     # 타임라인만 출력
  python3 build.py --segments 3,4   # 특정 장면 조각만 다시
"""
import json, os, re, subprocess, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                              # claymation/
sys.path.insert(0, HERE)
from script import LINES, SHOTS                           # noqa: E402

BUILD = os.environ.get('STONEAGE_BUILD', os.path.join(ROOT, 'build', 'stoneage'))
IMG, CLIP, VOICE, SEG = (os.path.join(BUILD, d) for d in ('img', 'clip', 'voice', 'seg'))
IMG = os.environ.get('STONEAGE_IMG', IMG)                 # 미리보기 그림으로 시험할 때
OUT = os.environ.get('STONEAGE_OUT', os.path.join(ROOT, 'stoneage.mp4'))
FPS = 24
LEAD, GAP, CHAPTER_GAP, TAIL = 0.25, 0.45, 1.1, 2.5       # 줄 앞 여유, 줄 사이, 장 바뀔 때, 끝
DIP = 0.35                                                 # 장이 바뀔 때 검은 화면으로 넘어가는 시간


# ─── 타임라인 ───
def syllables(s):
    return len(re.findall(r'[가-힣]', s)) + 0.6 * len(re.findall(r'[0-9A-Za-z]', s))

def estimate(text):
    """내레이션이 아직 없을 때: 차분한 다큐 말투 기준(초당 약 5.4음절) + 쉼표·마침표 쉼."""
    return syllables(text) / 5.4 + 0.22 * text.count(',') + 0.35 * len(re.findall(r'[.?!…]', text))

def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()

def even_frame(t):
    """장면 경계를 12fps 격자(24fps의 짝수 장)에 맞춘다."""
    return 2 * int(round(t * FPS / 2))

def plan():
    t, out = 0.0, []
    for i, L in enumerate(LINES):
        if L.get('chapter') and i:
            t += CHAPTER_GAP
        vf = os.path.join(VOICE, L['id'] + '.wav')
        has = os.path.exists(vf)
        dur = wav_seconds(vf) if has else estimate(L['tts'])
        v0 = t + LEAD
        v1 = v0 + dur
        w1 = v1 + L.get('hold', GAP)
        out.append(dict(L, v0=v0, v1=v1, w0=t, w1=w1, dur=dur, voiced=has))
        t = w1
    out[-1]['w1'] += TAIL
    # 장면: 줄의 화면 구간을 장면 수로 나눈다 (경계는 짝수 장)
    shots = []
    for k, L in enumerate(out):
        ids = L['shots']
        f0, f1 = even_frame(L['w0']), even_frame(L['w1'])
        for j, sid in enumerate(ids):
            a = f0 + even_frame((f1 - f0) * j / len(ids) / FPS)
            b = f0 + even_frame((f1 - f0) * (j + 1) / len(ids) / FPS)
            shots.append(dict(id=sid, line=L['id'], f0=a, f1=b,
                              dip_in=bool(L.get('chapter')) and j == 0,
                              dip_out=j == len(ids) - 1 and k + 1 < len(out) and bool(out[k + 1].get('chapter'))))
    # 바로 앞 장면과 같은 장면이면 하나로 합친다
    merged = []
    for s in shots:
        if merged and merged[-1]['id'] == s['id'] and not s['dip_in']:
            merged[-1]['f1'] = s['f1']
            merged[-1]['dip_out'] = s['dip_out']
        else:
            merged.append(s)
    return out, merged


# ─── 조각 영상 ───
def look(sh):
    """그레인·비네팅·조명 깜빡임. 불이 있는 장면은 모닥불처럼 조금 더 일렁이게."""
    amp = 0.045 if 'fire' in sh.get('sfx', []) else 0.010
    grade = "colorbalance=rs=-0.04:bs=0.05:rh=0.03:bh=-0.03"   # 그림자는 살짝 푸르게, 밝은 곳은 따뜻하게
    return f"eq=brightness='{amp}*(random(0)-0.5)':eval=frame,{grade},vignette=PI/6.5,noise=alls=3:allf=t"

def zoompan(move, n, focus=(0.5, 0.5)):
    """move: in / out / left / right / up / down / hold. n = 12fps 장 수."""
    fx, fy = focus
    z0, z1 = {'in': (1.0, 1.12), 'out': (1.12, 1.0)}.get(move, (1.10, 1.10))
    if move == 'hold':
        z0 = z1 = 1.03
    z = f"{z0}+({z1}-{z0})*on/{max(1, n - 1)}"
    # 줌의 중심: focus 쪽으로. 팬: 화면 끝에서 끝까지(여유 범위 안)
    cx = f"(iw-iw/zoom)*{fx}"
    cy = f"(ih-ih/zoom)*{fy}"
    p = f"on/{max(1, n - 1)}"
    if move == 'left':
        cx = f"(iw-iw/zoom)*(1-{p})"
    elif move == 'right':
        cx = f"(iw-iw/zoom)*{p}"
    elif move == 'up':
        cy = f"(ih-ih/zoom)*(1-{p})"
    elif move == 'down':
        cy = f"(ih-ih/zoom)*{p}"
    return f"zoompan=z='{z}':x='{cx}':y='{cy}':d={n}:s=1920x1080:fps=12"

def fades(n24, dip_in, dip_out):
    f = []
    if dip_in:
        f.append(f"fade=t=in:st=0:d={DIP}")
    if dip_out:
        f.append(f"fade=t=out:st={n24 / FPS - DIP:.3f}:d={DIP}")
    return (',' + ','.join(f)) if f else ''

def render(seg, idx):
    sh = SHOTS[seg['id']]
    n24 = seg['f1'] - seg['f0']
    n12 = n24 // 2
    path = os.path.join(SEG, f"{idx:03d}_{seg['id']}.mp4")
    clip = os.path.join(CLIP, seg['id'] + '.mp4')
    if sh.get('clip') and os.path.exists(clip):
        native = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'csv=p=0', clip], capture_output=True, text=True).stdout) // 2
        slow = min(max(n12 / native, 1.0), 1.6)            # 모자라면 최대 1.6배까지 느리게
        hold = max(0.0, n24 / FPS - native * slow / 12)
        vf = (f"select='not(mod(n\\,2))',setpts=N/(12*TB)*{slow:.4f},"
              f"scale=1920:1084:flags=lanczos,crop=1920:1080,{look(sh)},"
              f"tpad=stop_mode=clone:stop_duration={hold + 0.2:.3f},fps={FPS}{fades(n24, seg['dip_in'], seg['dip_out'])},format=yuv420p")
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', clip, '-vf', vf]
    else:
        img = os.path.join(IMG, seg['id'] + '.png')
        vf = (f"scale=3840:2172:flags=lanczos,crop=3840:2160,{zoompan(sh.get('move', 'in'), n12, sh.get('focus', (0.5, 0.5)))},"
              f"{look(sh)},fps={FPS}{fades(n24, seg['dip_in'], seg['dip_out'])},format=yuv420p")
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', img, '-vf', vf]
    cmd += ['-frames:v', str(n24), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', path]
    subprocess.run(cmd, check=True)
    return path


# ─── 자막 (Pretendard, 테두리 없이 부드러운 그림자) ───
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Text,Pretendard SemiBold,56,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0.4,0,1,0,0,2,100,100,80,1
Style: Shade,Pretendard SemiBold,56,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0.4,0,1,0,0,2,100,100,80,1
Style: ChapNo,Pretendard Medium,30,&H00E6F2FF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,0,0,7,0,0,0,1
Style: ChapNoShade,Pretendard Medium,30,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,0,0,7,0,0,0,1
Style: Chap,Pretendard Bold,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,0,0,7,0,0,0,1
Style: ChapShade,Pretendard Bold,64,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
HL = r'{\c&H7FD4FF&}'                                      # 강조 (따뜻한 노랑)
WH = r'{\c&HFFFFFF&}'

def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

def wrap(text, width=24):
    """한 줄 width자 안팎으로, 어절 단위로 두 줄까지 나눈다."""
    words, lines, cur = text.split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    lines.append(cur)
    return lines

def chunks(text):
    """자막 한 화면 = 두 줄 이하. 길면 여러 화면으로 나눈다(문장·쉼표 경계 우선)."""
    parts = [p.strip() for p in re.split(r'(?<=[.?!,…])\s+', text) if p.strip()]
    out, cur = [], ''
    for p in parts:
        cand = (cur + ' ' + p).strip()
        if cur and len(wrap(cand)) > 2:
            out.append(cur)
            cur = p
        else:
            cur = cand
    out.append(cur)
    final = []
    for c in out:                                          # 쉼표 없이 긴 문장은 어절로 자른다
        ls = wrap(c)
        while len(ls) > 2:
            final.append(' '.join(ls[:2]))
            ls = ls[2:]
        final.append(' '.join(ls))
    return final

def highlight(s, words):
    for w in words:
        s = s.replace(w, HL + w + WH)
    return s

def subtitles(lines, path):
    ev = []
    for L in lines:
        parts = chunks(L['sub'])
        tot = sum(syllables(p) for p in parts) or 1
        t = L['v0']
        for p in parts:
            d = (L['v1'] - L['v0']) * syllables(p) / tot
            body = r'\N'.join(wrap(p))
            ev.append((t - 0.05, t + d + 0.15, body, L.get('hl', [])))
            t += d
    with open(path, 'w') as f:
        f.write(ASS_HEAD)
        for k, (a, b, body, hl) in enumerate(ev):
            if k + 1 < len(ev):
                b = min(b, ev[k + 1][0])
            f.write(f"Dialogue: 0,{ts(a)},{ts(b)},Shade,,0,0,0,,{{\\pos(963,1003)\\blur10\\alpha&H38&}}{body}\n")
            f.write(f"Dialogue: 0,{ts(a)},{ts(b)},Shade,,0,0,0,,{{\\pos(961,1001)\\blur3\\alpha&H68&}}{body}\n")
            f.write(f"Dialogue: 1,{ts(a)},{ts(b)},Text,,0,0,0,,{{\\pos(960,1000)}}{highlight(body, hl)}\n")
        for L in lines:                                    # 장 제목: 왼쪽 위에 3초
            if not L.get('chapter'):
                continue
            no, title = L['chapter']
            a, b = L['w0'] + 0.3, L['w0'] + 3.6
            for st, y, txt in (('ChapNo', 96, no), ('Chap', 138, title)):
                f.write(f"Dialogue: 2,{ts(a)},{ts(b)},{st}Shade,,0,0,0,,{{\\pos(124,{y + 3})\\blur9\\alpha&H40&\\fad(500,500)}}{txt}\n")
                f.write(f"Dialogue: 3,{ts(a)},{ts(b)},{st},,0,0,0,,{{\\pos(121,{y})\\fad(500,500)}}{txt}\n")


# ─── 실행 ───
def main():
    args = sys.argv[1:]
    lines, segs = plan()
    total = segs[-1]['f1'] / FPS
    if '--plan' in args:
        for L in lines:
            print(f"{L['id']:>6} {L['v0']:7.2f}–{L['v1']:7.2f} {'V' if L['voiced'] else '~'} {L['sub'][:40]}")
        print(f"{len(segs)} shots, {int(total // 60)}:{total % 60:04.1f}")
        return
    for d in (SEG,):
        os.makedirs(d, exist_ok=True)
    only = None
    if '--segments' in args:
        only = {int(x) for x in args[args.index('--segments') + 1].split(',')}
    paths = []
    for i, s in enumerate(segs):
        p = os.path.join(SEG, f"{i:03d}_{s['id']}.mp4")
        if only is None or i in only or not os.path.exists(p):
            print(f"[{i + 1}/{len(segs)}] {s['id']} {(s['f1'] - s['f0']) / FPS:.1f}s", flush=True)
            p = render(s, i)
        paths.append(p)
    if only is not None:
        return
    with open(os.path.join(BUILD, 'concat.txt'), 'w') as f:
        f.writelines(f"file '{p}'\n" for p in paths)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(BUILD, 'concat.txt'),
                    '-c', 'copy', os.path.join(BUILD, 'video.mp4')], check=True)
    subs = os.path.join(BUILD, 'subs.ass')
    subtitles(lines, subs)
    json.dump({'lines': lines, 'shots': segs, 'total': total}, open(os.path.join(BUILD, 'timeline.json'), 'w'),
              ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, 'score.py'), BUILD], check=True)
    audio = os.path.join(BUILD, 'audio.wav')
    meas = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', audio, '-af',
                           'loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                          capture_output=True, text=True).stderr
    m = json.loads(re.findall(r'\{[^{}]*\}', meas, re.S)[-1])
    ln = (f"loudnorm=I=-15:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(BUILD, 'video.mp4'), '-i', audio,
                    '-vf', f"subtitles={subs},format=yuv420p", '-af', f"{ln},aresample=44100",
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f"{total:.3f}", '-movflags', '+faststart', OUT], check=True)
    print('done:', OUT, f"{int(total // 60)}:{total % 60:04.1f}")


if __name__ == '__main__':
    main()
