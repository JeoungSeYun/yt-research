#!/usr/bin/env python3
"""
진짜 마크 블록 텍스처로 텍스처 세트를 만든다(textures.py와 같은 이름으로 저장 → mc_world.py가 그대로 쓴다).

원본: Mojang이 공식 공개한 Bedrock 리소스 팩(github.com/Mojang/bedrock-samples, resource_pack/textures/blocks).
Mojang 저작물(마인크래프트 EULA 적용)이라 저장소에는 넣지 않고 build/ 안에서만 쓴다.

  git clone --depth 1 --filter=blob:none --sparse https://github.com/Mojang/bedrock-samples bedrock
  git -C bedrock sparse-checkout set resource_pack/textures/blocks
  python3 real_textures.py bedrock/resource_pack/textures/blocks build/tex_real
"""
import os, sys
from PIL import Image

GRASS, FOLIAGE, BIRCH, WATER = (0x91, 0xBD, 0x59), (0x77, 0xAB, 0x2F), (0x80, 0xA7, 0x55), (0x3F, 0x76, 0xE4)


def load(src, name):
    im = Image.open(os.path.join(src, name)).convert('RGBA')
    return im.crop((0, 0, 16, 16)) if im.size != (16, 16) else im    # 물처럼 세로로 긴 애니메이션은 첫 장만


def tint(im, c):
    """회색 텍스처 × 바이옴 색(마크가 잔디·잎·물을 칠하는 방식)."""
    px = im.load()
    out = im.copy()
    po = out.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            po[x, y] = (r * c[0] // 255, g * c[1] // 255, b * c[2] // 255, a)
    return out


def whiten_flowers(im):
    """진달래 꽃잎(분홍)을 흰 수국 색으로."""
    out = im.copy()
    po = out.load()
    for y in range(16):
        for x in range(16):
            r, g, b, a = po[x, y]
            if a and r > g + 25:
                v = (r + g + b) // 3
                po[x, y] = (min(255, v + 95), min(255, v + 92), min(255, v + 70), a)
    return out


def grid(src, rows):
    """블록 여러 장을 이어 붙인 외벽 텍스처(한 칸 = 한 블록 = 1m)."""
    h, w = len(rows), len(rows[0])
    out = Image.new('RGBA', (16 * w, 16 * h))
    for j, row in enumerate(rows):
        for i, name in enumerate(row):
            out.paste(load(src, name), (16 * i, 16 * j))
    return out


def lattice(im):
    out = im.copy()
    po = out.load()
    for y in range(16):
        for x in range(16):
            if not (x in (0, 1, 14, 15) or y in (0, 1, 14, 15) or abs(x - y) < 1.5):
                po[x, y] = (0, 0, 0, 0)
    return out


def make(src, out):
    os.makedirs(out, exist_ok=True)
    L = lambda n: load(src, n)
    T = {
        'grass_top': tint(L('grass_top.png'), GRASS),
        'grass_side': L('grass_side_carried.png'),
        'dirt': L('dirt.png'),
        'stone': L('stone_andesite.png'),
        'cobble': L('stone_diorite.png'),
        'smooth': L('stone_slab_top.png'),
        'path': L('hardened_clay_stained_white.png'),          # 흰색 테라코타: 연분홍 베이지 산책로
        'gravel': L('gravel.png'),
        'log_side': L('log_oak.png'),
        'log_top': L('log_oak_top.png'),
        'leaves': tint(L('leaves_oak.tga'), FOLIAGE),
        'leaves_poplar': tint(L('leaves_birch.tga'), BIRCH),
        'leaves_pink': L('azalea_leaves_flowers.png'),
        'leaves_white': whiten_flowers(L('azalea_leaves_flowers.png')),
        'bush': L('azalea_leaves.png'),
        'tallgrass': tint(L('tallgrass.tga'), GRASS),
        'flower_pink': L('flower_tulip_pink.png'),
        'reeds': tint(L('fern.tga'), GRASS),
        'water': tint(L('water_still_grey.png'), WATER),
        'wall': L('stonebrick.png'),
        'concrete': L('concrete_silver.png'),
        'crane': lattice(L('concrete_yellow.png')),
        'iron': L('polished_basalt_side.png'),
        'lantern': L('glowstone.png'),
        'hill': tint(L('leaves_oak_opaque.png'), FOLIAGE),
        'white': L('quartz_block_side.png'),
        # 앞서 걷는 두 사람: 양털 옷
        'cloth_black': L('wool_colored_black.png'),
        'cloth_grey': L('wool_colored_silver.png'),
        'cloth_dark': L('wool_colored_gray.png'),
        'hair_blond': L('wool_colored_yellow.png'),
        'bag_brown': L('wool_colored_brown.png'),
    }
    # 강 건너 아파트: 흰 콘크리트 층 + 유리창(몇 개는 불 켜진 창)
    T['facade'] = grid(src, [
        ['concrete_white.png'] * 4,
        ['glass_light_blue.png', 'glass_light_blue.png', 'glowstone.png', 'glass_light_blue.png'],
        ['concrete_white.png'] * 4,
        ['glass_light_blue.png', 'glowstone.png', 'glass_light_blue.png', 'glass_light_blue.png'],
    ])
    T['facade2'] = grid(src, [
        ['quartz_block_side.png'] * 4,
        ['glass_gray.png', 'glass_gray.png', 'glass_gray.png', 'glowstone.png'],
        ['quartz_block_side.png'] * 4,
        ['glowstone.png', 'glass_gray.png', 'glass_gray.png', 'glass_gray.png'],
    ])
    T['crane'] = L('concrete_yellow.png')                   # 크레인도 노란 콘크리트 블록 그대로
    T['fence'] = L('planks_big_oak.png')                     # 가로등 기둥: 짙은 참나무 울타리
    # 캐릭터 스킨·구름·달: blocks 옆 폴더(entity, environment)에서 원본 크기 그대로
    up = os.path.dirname(os.path.normpath(src))
    raw = lambda *p: Image.open(os.path.join(up, *p)).convert('RGBA')
    T['skin_steve'] = raw('entity', 'steve.png')
    T['skin_alex'] = raw('entity', 'alex.png')
    T['clouds_map'] = raw('environment', 'clouds.png')
    T['moon'] = raw('environment', 'moon_phases.png').crop((0, 0, 32, 32))   # 보름달
    for name, im in T.items():
        im.save(os.path.join(out, name + '.png'))
    return sorted(T)


if __name__ == '__main__':
    print(make(sys.argv[1], sys.argv[2]))
