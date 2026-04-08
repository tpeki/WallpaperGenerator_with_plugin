import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import math
import random
from wall_common import *

OUTPUT_SIZE = (1920, 1080)
GRASS_COLOR = (11,60,0)
FIX_ON = 2  # 1=Egg, 2=Chick
TILE = 180
EGG_H = 100
CHICKS = 2  # % of colored chicks

EGG_SHAPE = (0.85, 0.25)
COLORS = [
    (255, 96, 96),
    (96, 112, 255),
    (240, 210, 80),
    (60, 255, 60),
    (60, 240, 240),
    (220, 40, 40),
    (200, 96, 240),
]

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'イースター',
                       {'color1':'背景色',
                        'sub_jitter2':'固定(0-3)',
                        'pwidth':'卵サイズ', 'pheight':'配置間隔',
                        'pdepth':'ひよこ率%'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*GRASS_COLOR)
    p.sub_jitter2 = FIX_ON
    p.pwidth = EGG_H
    p.pheight = TILE
    p.pdepth = CHICKS
    return p




# =========================
# 卵マスク
# =========================
def make_egg(h):
    w = int(h * EGG_SHAPE[0])
    k = EGG_SHAPE[1]

    y, x = np.ogrid[-1:1:h*1j, -1:1:w*1j]
    sx = 1 - k * (1 - y) / 2
    mask = ((x / sx)**2 + y**2) <= 1

    return Image.fromarray((mask * 255).astype(np.uint8), 'L')


# =========================
# ひよこ
# =========================
def make_chick_mask(egg_mask):
    # --- 余白追加（上下） ---
    pad = egg_mask.height // 4
    mask = ImageOps.expand(egg_mask, border=(0, pad, 0, pad), fill=0)

    w, h = mask.size
    draw = ImageDraw.Draw(mask)

    parts = [
        [0.20,0.27, 0,0.25, 0.13,0.38],  # くちばし
        [0.32,0.75, 0.12,0.88, 0.17,0.88],  # ひだりあし
        [0.46,0.80, 0.48,0.95, 0.52,0.95],  # みぎあし
        [0.85,0.65, 1.00,0.65, 0.82,0.75],  # しっぽ
        ]

    for v in parts:
        points = []
        for i in range(len(v)//2):
            points.append((int(w*v[i*2]), int(h*v[i*2+1])))

        draw.polygon(points, fill=255)

    # =====================
    # 目（黒丸）※別レイヤーで使う
    # =====================
    eye_mask = Image.new("L", (w, h), 0)
    draw_eye = ImageDraw.Draw(eye_mask)

    r = max(int(w * 0.1), 2)
    cx = int(w * 0.45)
    cy = int(h * 0.35)

    #draw_eye.ellipse((cx-r, cy-r, cx+r, cy+r), fill=255)  # 白目
    #draw_eye.ellipse((cx-r, cy-int(r*0.7), cx, cy+int(r*0.3)),fill=0)  # 黒目
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=0)  # 白目
    draw.ellipse((cx-r, cy-int(r*0.7), cx, cy+int(r*0.3)),fill=255)  # 黒目

    return mask   #, eye_mask


# =========================
# 陰影（固定空間）
# =========================
def make_gradient(size, angle=135, gamma=2.2):
    w, h = size

    theta = np.deg2rad(angle)
    dx, dy = np.cos(theta), np.sin(theta)

    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(-1, 1, h, dtype=np.float32)[:, None]

    t = x * dx + y * dy
    t = (t - t.min()) / (t.max() - t.min() + 1e-6)
    t = t ** gamma

    return t


# =========================
# パターン（柄マスク）
# =========================

def stripe(w, h, freq):
    y = np.linspace(0, 1, h)[:, None]
    return (np.sin(y * freq * np.pi) > 0).astype(np.float32)

def polka(w, h, scale):
    x = np.arange(w)[None, :]
    y = np.arange(h)[:, None]

    cx = (x // scale) * scale + scale // 2
    cy = (y // scale) * scale + scale // 2

    d = (x - cx)**2 + (y - cy)**2
    return (d < (scale*0.3)**2).astype(np.float32)

def zigzag(w, h, freq):
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]

    z = np.abs(((x + y) * freq) % 1 - 0.5)
    return (z < 0.2).astype(np.float32)


# =========================
# パターン生成（複合）
# =========================
def make_pattern(size):
    w, h = size

    pattern = np.zeros((h, w), dtype=np.float32)

    # レイヤー数（1〜3）
    layers = random.randint(1, 3)

    for _ in range(layers):
        kind = random.choice(["stripe", "polka", "zigzag"])

        if kind == "stripe":
            p = stripe(w, h, random.uniform(6, 14))

        elif kind == "polka":
            p = polka(w, h, random.randint(8, 16))

        else:
            p = zigzag(w, h, random.uniform(6, 12))

        # 合成（maxで重ねると模様が潰れにくい）
        pattern = np.maximum(pattern, p)

    return pattern


# =========================
# 色シート生成（模様回転込み）
# =========================
def make_color_sheet(size, color, angle):
    w, h = size
    base = np.array(color, dtype=np.float32)

    # 陰影（固定）
    t = make_gradient(size)

    img = base * (1.0 - 0.5 * t)[..., None]

    # --- パターン生成 ---
    pattern = make_pattern(size)

    # --- 回転（重要） ---
    pat_img = Image.fromarray((pattern * 255).astype(np.uint8))
    pat_img = pat_img.rotate(angle, resample=Image.BICUBIC)
    pattern = np.array(pat_img).astype(np.float32) / 255.0

    # --- 色レイヤー ---
    alt1 = base * 0.5 + 100
    #alt2 = np.array(random.choice(COLORS[0:2]), dtype=np.float32)
    alt2 = np.array(color, dtype=np.float32)

    # 2段階模様
    mask1 = pattern > 0.5
    mask2 = (pattern > 0.2) & (pattern <= 0.5)

    img = img.copy()
    img[mask1] = alt1
    img[mask2] = alt2

    # --- スペキュラ ---
    img += (t**6)[..., None] * 60

    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


# =========================
# 背景芝生
# =========================
def make_grass(size, basecolor=(17,60,0)):
    w, h = size
    
    # 低周波ノイズ（大きなムラ）
    lc = 4
    low = np.random.rand((h+lc-1)//lc, (w+lc-1)//lc).astype(np.float32)
    low = np.kron(low, np.ones((lc,lc)))
    low = low[:h, :w]

    # 高周波ノイズ（細かい粒）
    high = np.random.rand(h, w).astype(np.float32)

    # 縦方向の筋（草感）
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    dx = np.cos(0.8)  #だいたい70度
    dy = np.sin(0.8)
    noise = np.random.rand(h, w) * 0.2
    t = x*dx + y*dy + noise
    stripes = (np.sin(t * w * 0.15) * 0.6 + 0.5)

    # 合成
    texture = (0.6*low + 0.3*high + 0.1*stripes)
    texture = (texture-texture.min()) / (texture.max()-texture.min()+1e-6)

    # 明暗に方向性
    y = np.linspace(0, 1, h)[:, None]
    light = 0.8 + 0.2 * (1 - y)
    texture *= light

    # =====================
    # 緑に変換
    # =====================
    r = basecolor[0] + texture * basecolor[0]
    g = basecolor[1] + texture * basecolor[1]
    b = basecolor[2] + texture * basecolor[2]

    img = np.stack([r, g, b], axis=-1)

    return Image.fromarray(img.astype(np.uint8))


# =========================
# メイン
# =========================
def generate(p: Param):
    width, height = p.width, p.height
    tile = p.pheight
    egg_h = p.pwidth
    chicks = p.pdepth  # % of colored chicks
    grass_color = p.color1.ctoi()
    rot_on = p.sub_jitter2 % 2 == 0  # 1なら固定、0なら回転
    rot_chick = p.sub_jitter2 & 2 == 0  # 1なら固定、0なら回転
    
    if p.h_img is None:
        base = make_grass((width, height), grass_color)
    else:
        base = p.bg()

    egg_mask = make_egg(egg_h)

    grad_size = (int(egg_h * 1.5), int(egg_h * 1.5))
    cx = grad_size[0] // 2

    # 三角格子
    h = tile * math.sqrt(3) / 2
    points = []

    row = 0
    y = 0
    while y <= height + tile:
        offset = 0 if row % 2 == 0 else tile / 2
        x = offset
        col = 0
        while x <= width + tile:
            points.append((x, y, row, col))
            x += tile
            col += 1
        y += h
        row += 1

    # 描画
    for x, y, row, col in points:
        angle = random.uniform(0, 360) if rot_on else 0
        ci = (col + (row+1)%2) % 3

        # 卵 or ひよこ
        if random.random() < (chicks/100):  # 2%くらい
            base_mask = make_chick_mask(egg_mask)
            angle = angle // 2 if rot_chick else 20
            ci = int(random.random()*len(COLORS))
        else:
            base_mask = egg_mask
            
        egg_r = base_mask.rotate(angle, resample=Image.NEAREST, expand=True)

        color = COLORS[ci]
        sheet = make_color_sheet(grad_size, color, angle)

        w2, h2 = egg_r.size
        x2, y2 = cx - w2//2, cx - h2//2
        crop = sheet.crop((x2, y2, x2+w2, y2+h2))

        px = int(x - w2 / 2)
        py = int(y - h2 / 2)

        shadow = egg_r.copy()
        shadow = shadow.filter(ImageFilter.GaussianBlur(5))
        shadow = shadow.point(lambda p: p * 0.35)
        shadow_color = np.clip([int(x*0.1) for x in grass_color], 0, 255)

        dx, dy = width//120, height//80
        base.paste(tuple(shadow_color), (px+dx, py+dy), shadow)

        base.paste(crop, (px, py), egg_r)

    return base


# 実行
if __name__ == "__main__":
    p = Param()
    p = default_param(p)
    p.width, p.height = OUTPUT_SIZE
    img = generate(p)
    img.show()
