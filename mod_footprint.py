import numpy as np
from PIL import Image, ImageColor
from wall_common import *

'''
- EXCUSE
ごめんなさい、右回りの足跡しか実装できていません
また、下に凸なカーブにする場合など、始点座標と開始角を工夫していただく
ような形になっています。
半径をマイナスにすると下に凸になるとか、
歩数をマイナスにすると左回りになるとか、
工夫の仕様はありそうなんだけどとりあえずリリース
'''


# --- 基本パラメータ ---
FEET_COLOR = (0x77,0x33,0x13)
BASE_COLOR1 = (0xed,0xe8,0xd1)
BASE_COLOR2 = (0xd2,0xc6,0x8c)

STEPS = 40
ANGLE = 20
RADIUS = 980
START_X = 730
START_Y = 1100
FOOT_SIZE = 48

MODE = 1  # 0:LINEAR 1:ARC
JITTER = 30

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '足跡 (歩数=正:CW 負:CCW)',
                       {'color1':'足跡',
                        'color2':'背景1', 'color3':'背景2',
                        'color_jitter':'歩数',
                        'sub_jitter':'角度',
                        'sub_jitter2':'半径(0:直線)',
                        'pwidth':'始点X', 'pheight':'始点Y',
                        'pdepth':'足サイズ'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*FEET_COLOR)
    p.color2.itoc(*BASE_COLOR1)
    p.color3.itoc(*BASE_COLOR2)
    p.color_jitter = STEPS
    p.sub_jitter = ANGLE
    p.sub_jitter2 = RADIUS
    
    p.pwidth = START_X
    p.pheight = START_Y
    p.pdepth = FOOT_SIZE
    return p


# ----
# 足跡生成
# ----
def footprint(color, degree, size=512, left=False):
    '''color: tuple (r,g,b), degree: 0 = upward, size: width & height
    left = False:right foot, True: left foot'''

    # ====================
    # 基本設定
    W, H = size, size
    x = np.linspace(-1, 1, W)
    y = np.linspace(-1, 1, H)
    X, Y = np.meshgrid(x, y)

    # --- 全体回転 ---
    zeta = np.deg2rad(degree+180)
    XR =  X * np.cos(zeta) + Y * np.sin(zeta)
    YR = -X * np.sin(zeta) + Y * np.cos(zeta)

    if left:
        XR = -XR  # 左足

    # ====================
    # かかと
    a1, b1 = 0.28, 0.60
    x1, y1 = -0.06, -0.35
    theta = np.deg2rad(15)

    Xt =  (XR - x1) * np.cos(theta) + (YR - y1) * np.sin(theta)
    Yt = -(XR - x1) * np.sin(theta) + (YR - y1) * np.cos(theta)
    f1 = Xt**2 / a1**2 + Yt**2 / b1**2 - 1

    # ====================
    # 母指球
    a2, b2 = 0.50, 0.27
    x2, y2 = 0.10, 0.10
    f2 = (XR - x2)**2 / a2**2 + (YR - y2)**2 / b2**2 - 1

    # ====================
    # 本体ブレンド
    alpha = 7.0
    f_body = -np.log(np.exp(-alpha * f1) + np.exp(-alpha * f2)) / alpha

    # ====================
    # 指（円弧長ベース・隙間均等）

    toe_r_base = np.array([0.11, 0.13, 0.14, 0.16, 0.23])  # 小指→親指
    toe_r = toe_r_base * 0.7

    # 角度指定
    ang_thumb = np.deg2rad(-205)
    ang_pinky = np.deg2rad(-325)

    # 配置半径
    R = a2 + np.max(toe_r) + 0.04

    # 円弧長
    arc_len = R * (ang_thumb - ang_pinky)

    toe_widths = 2 * toe_r
    used_len = toe_widths.sum()
    gap_arc = (arc_len - used_len) / (len(toe_r) - 1)

    # 円弧長上の中心位置
    centers_len = []
    pos = toe_widths[0] / 2
    centers_len.append(pos)
    for i in range(1, len(toe_r)):
        pos += toe_widths[i-1] / 2 + gap_arc + toe_widths[i] / 2
        centers_len.append(pos)
    centers_len = np.array(centers_len)

    # 向き補正
    angles = ang_thumb - centers_len / R

    # ====================
    # 指を追加（母指球非交差）
    gap_normal = 0.02
    f_all = f_body.copy()

    for ang, r in zip(angles, toe_r):
        ex = x2 + a2 * np.cos(ang)
        ey = y2 + b2 * np.sin(ang)

        nx = np.cos(ang) / a2
        ny = np.sin(ang) / b2
        n = np.sqrt(nx*nx + ny*ny)
        nx /= n
        ny /= n

        tx = ex + nx * (r + gap_normal)
        ty = ey + ny * (r + gap_normal)

        g = (XR - tx)**2 + (YR - ty)**2 - r**2
        f_all = np.minimum(f_all, g)

    # ====================
    # 画像化
    # ====================
    # RGBA化（黒=透過、白=#4444ff）

    # マスク（足跡部分）
    mask = (f_all <= 0)

    # RGBA 配列
    rgba = np.zeros((H, W, 4), dtype=np.uint8)

    c = cnv_rgba(color)
        
    # 白部分 → #4444ff
    rgba[mask, 0] = c[0]  # R
    rgba[mask, 1] = c[1]  # G
    rgba[mask, 2] = c[2]  # B
    rgba[mask, 3] = 255   # A（不透明）

    # 黒部分 → 透明（A=0 のまま）

    image = Image.fromarray(rgba, mode="RGBA")
    return image


def paste_footprint(canvas, fp_img, cx, cy):
    w, h = fp_img.size
    canvas.alpha_composite(
        fp_img,
        (int(cx - w/2), int(cy - h/2))
    )

# ----
# 生成
# ----
def cnv_rgba(color):
    if isinstance(color, str):
        color = (color+'ffff')[0:9]
        return ImageColor.getcolor(color, 'RGBA')

    c = [0,0,0,255]
    if isinstance(color, (list, tuple)):
        if len(color) == 3:
            c[0:3] = [color[i] for i in range(3)]
            c[3] = 255
        if len(color) >= 4:
            c[0:4] = color[0:4]            
    return c


def generate_linear(p: Param):
    '''直線で配置 color, bgcolor, start_x, start_y,
    size=80, angle=30, steps=12 '''

    fgcolor = p.color1
    bg1, bg2 = p.color2, p.color3

    CANVAS_W, CANVAS_H = p.width, p.height
    W = min(max(p.pdepth,10),int(min(CANVAS_W,CANVAS_H)/4))  # 足跡サイズ
    la = p.sub_jitter % 180  # 傾き角度（度）
    steps = max(abs(p.color_jitter), 2)  # 足跡の数
    start_x, start_y = p.pwidth, p.pheight
    jitter = JITTER

    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0,0,0,0))

    # 角度変換
    theta = np.deg2rad(la)
    dx = np.sin(theta)
    dy_dir = -np.cos(theta)

    v = np.array([dx, dy_dir])          # 中心線方向
    n = np.array([dy_dir, -dx])         # 法線方向

    # 正規化
    v /= np.linalg.norm(v)
    n /= np.linalg.norm(n)

    # 中心線開始点（x=0）
    p0 = np.array([start_x, start_y])

    for i in range(steps):
        # 中心線上の位置
        p = p0 + v * (i * W)

        # 左右交互
        side = -1 if i % 2 == 0 else 1
        offset = n * (side * W / 2)

        pos = p + offset

        # 画面外ならスキップ
        if not (0 <= pos[0] <= CANVAS_W and 0 <= pos[1] <= CANVAS_H):
            continue

        # 足跡生成
        fp = footprint(
            color=rgb_random_jitter(fgcolor, jitter).ctoi(),
            degree=la,
            size=W,
            left=(side > 0)
        )
        
        paste_footprint(canvas, fp, pos[0], pos[1])

    return canvas


def generate_arc(p : Param):
    '''弧状に配置'''

    fgcolor = p.color1
    bg1, bg2 = p.color2, p.color3

    CANVAS_W, CANVAS_H = p.width, p.height
    start_x, start_y = p.pwidth, p.pheight
    start_angle_deg = p.sub_jitter % 360
    cr_raw = p.sub_jitter2
    cr = abs(cr_raw)
    
    W = min(max(p.pdepth,10),int(min(CANVAS_W,CANVAS_H)/4))
    steps_raw = p.color_jitter
    steps = max(abs(steps_raw), 2)
    jitter = JITTER

    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0,0,0,0))

    if steps_raw >= 0:
        direction = 1
        phi0 = np.deg2rad(start_angle_deg-180)
    else:
        direction = -1
        phi0 = np.deg2rad(start_angle_deg)

    dphi = W / cr * direction   # 円弧長 ≒ 足跡サイズ

    # --- 基準円弧の開始点（中心は 0,0） ---
    ix = cr * np.cos(phi0)
    iy = cr * np.sin(phi0)

    # --- 平行移動オフセット ---
    off = np.array([start_x - ix, start_y - iy])

    for i in range(steps):
        phi = phi0 + i * dphi

        # 円周上の点（原点中心）
        p_vec = np.array([
            cr * np.cos(phi),
            cr * np.sin(phi)
        ]) + off

        # 接線方向
        t = np.array([-np.sin(phi), np.cos(phi)])
        la = np.rad2deg(np.arctan2(t[0], -t[1]))
        if direction == -1:  # 左回りの時は進行方向が逆なので180度足す
            la += 180

        # 左右オフセット（半径方向）
        n = np.array([np.cos(phi), np.sin(phi)])
        side = -1 if i % 2 == 0 else 1
        # 半径が負のとき法線ベクトルが逆を向くのを補正
        pos = p_vec + n * (side * W / 2) * direction
        
        if not (0 <= pos[0] <= CANVAS_W and 0 <= pos[1] <= CANVAS_H):
            continue

        fp = footprint(
            color=rgb_random_jitter(fgcolor, jitter).ctoi(),
            degree=la,
            size=W,
            left=(side > 0)
        )

        paste_footprint(canvas, fp, pos[0], pos[1])

    return canvas

def generate(p: Param):
    radius = p.sub_jitter2
    if radius != 0:
        fg = generate_arc(p)
    else:
        fg = generate_linear(p)

    if p.h_img is None:
        bg = vertical_gradient_rgb(p.width, p.height,
                                   p.color2, p.color3).convert('RGBA')
    else:
        bg = p.bg().convert('RGBA')
        
    bg.alpha_composite(fg)
    return bg.convert('RGB')


# ----
# テスト
# ----
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080

#    img = generate_linear('#33ff66', '#663388', 0, 600, 80, 110, 30)
#    img = generate_arc('#33ff66', '#663388', 800, 600, 1200, 0, 60, 30)

    img = generate(p)
    img.show()
