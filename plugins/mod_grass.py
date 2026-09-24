import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import math
import random
from wall_common import *

OUTPUT_SIZE = (1920, 1080)
GRASS_COLOR = (31,96,0)  # XeviousGreen
LOW_CYCLE = 4
ANGLE = 70
HI_CYCLE_INTENSITY = 30
STRIPE_INTENSITY = 10
TEXTURE_BRIGHTNESS = 20

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '芝生',
                       {'color1':'背景色',
                        'color_jitter':'高周期強度',
                        'sub_jitter':'風強度',
                        'sub_jitter2':'光源(%)',
                        'pwidth':'低周期粒度', 'pheight':'風向(°)'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*GRASS_COLOR)
    p.color_jitter = HI_CYCLE_INTENSITY
    p.sub_jitter = STRIPE_INTENSITY
    p.sub_jitter2 = TEXTURE_BRIGHTNESS
    p.pwidth = LOW_CYCLE
    p.pheight = ANGLE
    return p


# =========================
# 背景芝生
# =========================
def generate(p: Param):
    ow, oh = p.width, p.height
    basecolor = p.color1.ctoi()
    lc = p.pwidth
    angle = p.pheight  # degree
    hci = p.color_jitter
    sti = p.sub_jitter
    tex = p.sub_jitter2

    margin = lc*2
    w, h = ow+margin*2, oh+margin*2
    
    # 低周波ノイズ（大きなムラ）
    low = np.random.rand((h+lc-1)//lc, (w+lc-1)//lc).astype(np.float32)
    low = np.kron(low, np.ones((lc,lc)))
    low = low[:h, :w]

    # 高周波ノイズ（細かい粒）
    high = np.random.rand(h, w).astype(np.float32)

    # 縦方向の筋（草感）
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]

    angle_noise = (low - 0.5) * 20  # 15°の範囲で揺らぐ
    rad = np.deg2rad(angle+angle_noise)    
    dx = np.cos(rad)
    dy = np.sin(rad)

    #noise = np.random.rand(h, w) * 0.05
    noise = (low - 0.5) * 0.7  # 位相ゆらぎ
    t = x*dx + y*dy + noise

    freq = 15  # 小さいほど縞の幅が広くなる
    stripes = (np.sin(t * freq) * 0.6 + 0.5)

    # 合成
    hci = int(max(0,min(100, hci)))
    sti = int(max(0,min(100, sti)))
    lci = max(0,100 - hci - sti)
    sum = hci+sti+lci
    hci = hci/sum
    lci = lci/sum
    sti = sti/sum
    
    texture = (lci*low + hci*high + sti*stripes)
    texture = (texture-texture.min()) / (texture.max()-texture.min()+1e-6)

    # 明暗に方向性
    tex = max(0,min(1, tex/100))
    
    y = np.linspace(0, 1, h)[:, None]
    light = 0.8 + tex * (1 - y)
    texture *= light
    bness = 0.7 + texture*0.6

    # =====================
    # ベースカラーに変換
    # =====================
    cmatrix = np.array(basecolor, dtype=np.float32)
    img = cmatrix[None, None, :] * bness[..., None]
    img_out = img[margin:margin+oh, margin:margin+ow]
    img_out = np.clip(img_out, 0, 255)
    
    return Image.fromarray(img_out.astype(np.uint8))


# 実行
if __name__ == "__main__":
    p = Param()
    p = default_param(p)
    p.width, p.height = OUTPUT_SIZE
    img = generate(p)
    img.show()
