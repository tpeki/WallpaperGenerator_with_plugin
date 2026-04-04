import numpy as np
from PIL import Image
import random
from wall_common import *

# 可変生成パラメータ
WIDTH = 1920
HEIGHT = 1080

BASE_COLOR = (17, 96, 0)
FRONT_COLOR = (160, 160, 160)

FRONT_JITTER = 40  # 前景色を-n%～+n%でランダムに(0-255でclip)
SIZE_JITTER = 50  # ランダム時：大きさを 1-#n%～ 1+n% でランダムに拡縮
ALIGN_MODE = 1  # 0:align 1:random

BASE_R = 200
DEPLOY_NUM = 25
STYLE = 75  # 形状閾値 0.235 ± STYLE/1000  0.16<x<0.31

# 内部定数
PEN_RADIUS = 3
FOCUS = 0.7
CONTRAST = 0.85

MASK_CACHE_SIZE = 6
INNER_ALGO = 1  # 内歯車偏心ロジック (0:ランダム 1:内歯車径依存)
RETRY = 100  # 適当な形状になるまでリトライする回数

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '花模様(スピログラフ) 配置 0格子,1ランダム',
                       {'color1':'背景色', 'color2':'基本色',
                        'color_jitter':'色変動%',
                        'sub_jitter':'サイズ変動%',
                        'sub_jitter2':'配置方法',
                        'pwidth':'サイズ', 'pheight':'配置数',
                        'pdepth':'形状'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE_COLOR)
    p.color2.itoc(*FRONT_COLOR)
    p.color_jitter = FRONT_JITTER
    p.sub_jitter = SIZE_JITTER
    p.sub_jitter2 = ALIGN_MODE
    p.pwidth = BASE_R
    p.pheight = DEPLOY_NUM
    p.pdepth = STYLE
    return p


# -----------------------------
# ペン（ぼかし付き）
# -----------------------------
def make_pen_kernel(radius):
    offsets = []
    weights = []

    for dx in range(-radius-1, radius+2):
        for dy in range(-radius-1, radius+2):
            dist = np.sqrt(dx*dx + dy*dy)

            if dist <= radius + 0.5:
                # --- 中心強調＋なだらか減衰 ---
                w = 1.0 - (dist / (radius + 0.5))**1.5
                offsets.append((dx, dy))
                weights.append(w)

    offsets = np.array(offsets, dtype=np.int16)
    weights = np.array(weights, dtype=np.float32)

    # 正規化（強すぎ防止）
    weights /= weights.max()

    return offsets, weights


# -----------------------------
# スピログラフマスク（float）
# -----------------------------
def make_spiro_mask(size, center_R, r, d, offsets, weights, pad, n_points=8000):
    W, H = size

    t = np.linspace(0, 2*np.pi * r, n_points, dtype=np.float32)
    k = (center_R - r) / r

    x = (center_R - r)*np.cos(t) + d*np.cos(k*t)
    y = (center_R - r)*np.sin(t) - d*np.sin(k*t)

    # 正規化
    x = (x - x.min()) / (x.max() - x.min())
    y = (y - y.min()) / (y.max() - y.min())

    margin = pad / W
    x = x * (1 - 2*margin) + margin
    y = y * (1 - 2*margin) + margin

    x = (x * (W - 1)).astype(np.int16)
    y = (y * (H - 1)).astype(np.int16)

    mask = np.zeros((H, W), dtype=np.float32)

    # --- ペン描画（ぼかし付き） ---
    for (dx, dy), w in zip(offsets, weights):
        xx = x + dx
        yy = y + dy

        valid = (0 <= xx) & (xx < W) & (0 <= yy) & (yy < H)

        # 加算ではなくmaxで自然に重ねる
        mask[yy[valid], xx[valid]] = np.maximum(
            mask[yy[valid], xx[valid]],
            w
        )

    return mask


# -----------------------------
# ランダムマスク生成
# -----------------------------
def generate_random_mask(offsets, weights, radius, pen_size, style=115):
    lsty = min(max((235-style)/1000,0),1)
    hsty = min(max((235+style)/1000,0),1)
    pad = int(pen_size * 2.5) + 4
    size = radius + 2 * pad

    for _ in range(RETRY):
        r = random.randint(30, 80)

        if INNER_ALGO == 0:
            d = random.randint(10, r - 5)
        else:
            d = int(r * random.uniform(0.3, 0.8))

        mask = make_spiro_mask((size, size), radius//2, r, d,
                               offsets, weights, pad)

        density = np.count_nonzero(mask > 0.1) / mask.size

        if lsty < density < hsty:
            return mask

    return None


# -----------------------------
# メイン描画（numpy合成）
# -----------------------------
# ランダム版
def scatter_spiro(p: Param):
    iwidth, iheight = p.width, p.height
    vase = p.color1.ctoi()
    flower = p.color2.ctoi()
    fl_var = p.color_jitter
    sz_var = p.sub_jitter
    
    fradius = p.pwidth
    fnum = p.pheight
    fstyle = p.pdepth
    
    pen_size = PEN_RADIUS

    # float canvas
    canvas = np.full((iheight, iwidth, 3), vase, dtype=np.float32)

    offsets, weights = make_pen_kernel(pen_size)

    # --- マスクキャッシュ ---
    masks = []
    attempts = 0

    while len(masks) < MASK_CACHE_SIZE and attempts < 200:
        attempts += 1
        m = generate_random_mask(offsets, weights, fradius, pen_size, fstyle)
        if m is not None:
            masks.append(m)

    if not masks:
        raise RuntimeError("mask生成失敗")

    # -------------------------
    # 配置
    # -------------------------
    for _ in range(fnum):
        base_mask = random.choice(masks)

        # スケール
        scale = random.uniform(1.0 - sz_var/100.0,
                               1.0 + sz_var/100.0)

        new_size = int(base_mask.shape[0] * scale)

        mask_img = Image.fromarray((base_mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((new_size, new_size), Image.BILINEAR)

        # 回転
        angle = random.uniform(0, 360)
        mask_img = mask_img.rotate(angle, expand=True)

        mask = np.array(mask_img, dtype=np.float32) / 255.0

        h, w = mask.shape

        # 色
        seed = np.random.randint(-fl_var, fl_var, size=3)
        color = np.array([
            clip8(flower[i] + flower[i]*seed[i]/100)
            for i in range(3)
        ], dtype=np.float32)

        # 位置
        x = random.randint(-w//2, iwidth - w//2)
        y = random.randint(-h//2, iheight - h//2)

        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(iwidth, x + w)
        y1 = min(iheight, y + h)

        if x0 >= x1 or y0 >= y1:
            continue

        mx0 = x0 - x
        my0 = y0 - y
        mx1 = mx0 + (x1 - x0)
        my1 = my0 + (y1 - y0)

        sub_mask = mask[my0:my1, mx0:mx1][..., None]

        # --- ソフト合成（壁紙向け） ---
        alpha = sub_mask ** FOCUS * CONTRAST
        canvas[y0:y1, x0:x1] = (
            canvas[y0:y1, x0:x1] * (1 - alpha) +
            color * alpha
        )

    # 仕上げ
    return canvas


# 整列版
def align_spiro(p: Param):
    iwidth, iheight = p.width, p.height
    vase = p.color1.ctoi()
    flower = p.color2.ctoi()
    fl_var = p.color_jitter
    sz_var = p.sub_jitter
    
    fradius = p.pwidth
    fnum = p.pheight
    fstyle = p.pdepth
    
    pen_size = PEN_RADIUS
    
    canvas = np.full((iheight, iwidth, 3), vase, dtype=np.float32)

    offsets, weights = make_pen_kernel(pen_size)

    # --- マスクキャッシュ（scatterと同じ） ---
    masks = []
    attempts = 0

    while len(masks) < MASK_CACHE_SIZE and attempts < 200:
        attempts += 1
        m = generate_random_mask(offsets, weights, fradius, pen_size, fstyle)
        if m is not None:
            masks.append(m)

    if not masks:
        raise RuntimeError("mask生成失敗")

    # -------------------------
    # 配置パラメータ
    # -------------------------
    cols = fnum
    cell = iwidth / cols
    rows = int(iheight / cell)+1

    grid_w = cell * cols
    grid_h = cell * rows

    # 余白（センタリング）
    offset_x = (iwidth - grid_w) / 2
    offset_y = (iheight - grid_h) / 2

    for j in range(rows):
        for i in range(fnum):

            base_mask = random.choice(masks)

            # --- サイズ固定 ---
            target_size = int(cell * 0.9)

            mask_img = Image.fromarray((base_mask * 255).astype(np.uint8))
            mask_img = mask_img.resize((target_size, target_size),
                                       Image.BILINEAR)

            # --- 回転 ---
            angle = random.uniform(0, 360)
            mask_img = mask_img.rotate(angle, expand=True)

            mask = np.array(mask_img, dtype=np.float32) / 255.0

            h, w = mask.shape

            # --- 色 ---
            seed = np.random.randint(-fl_var, fl_var, size=3)
            color = np.array([
                clip8(flower[k] + flower[k]*seed[k]/100)
                for k in range(3)
            ], dtype=np.float32)

            # --- セル中央に配置 ---
            cx = offset_x + (i + 0.5) * cell
            cx = int(cx + offset_x*(random.random()-0.5)*0.05)
            cy = offset_y + (j + 0.5) * cell
            cy = int(cy + offset_y*(random.random()-0.5)*0.05)

            x = cx - w // 2
            y = cy - h // 2

            # --- クリッピング ---
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(iwidth, x + w)
            y1 = min(iheight, y + h)

            if x0 >= x1 or y0 >= y1:
                continue

            mx0 = x0 - x
            my0 = y0 - y
            mx1 = mx0 + (x1 - x0)
            my1 = my0 + (y1 - y0)

            sub_mask = mask[my0:my1, mx0:mx1][..., None]

            # --- αブレンド（あなたの設定） ---
            alpha = (sub_mask ** FOCUS) * (CONTRAST*1.5)

            canvas[y0:y1, x0:x1] = (
                canvas[y0:y1, x0:x1] * (1 - alpha) +
                color * alpha
            )

    return canvas

# イメージ生成FE
def generate(p: Param):
    if p.sub_jitter2:
        canvas = scatter_spiro(p)
    else:
        canvas = align_spiro(p)
    
    # 仕上げ
    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    return Image.fromarray(canvas)


# -----------------------------
# 実行
# -----------------------------
if __name__ == "__main__":
    p = default_param(Param())
    img = generate(p)
    img.show()
