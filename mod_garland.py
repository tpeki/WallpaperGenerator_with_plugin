import numpy as np
from PIL import Image
from wall_common import *

COLOR1 = (40, 160, 180)  # 色1
COLOR2 = (40, 80, 120)  # 色2

RADIUS_A = 100  # サイズ1
CONVERGENCE_RATE = 30  # 収束率
OVERLAP_X = 25  # 重なり横
OVERLAP_Y = 50  # 重なり縦
JITTER = 10  # 色ジッタ

# 内部定数
GAMMA = 1.6  # 固定
AA_WIDTH = 1.04  # 固定

def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '垂れ幕 [重複率= -100～80]',
                       {'color1':'前景色', 'color2':'背景色',
                        'color_jitter':'色ゆらぎ',
                        'sub_jitter':'収束率(%)',
                        'pwidth':'円半径',
                        'pheight':'重複率横', 'pdepth':'重複率奥'})
    return module_name
    

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color_jitter = JITTER
    p.sub_jitter = CONVERGENCE_RATE
    p.pwidth = RADIUS_A
    p.pheight = OVERLAP_X
    p.pdepth = OVERLAP_Y
    return p


# ----
# 描画
# ----
def lerp(v0, v1, t):
    return v0 + (v1 - v0) * t


def generate(p: Param):
    width, height = p.width, p.height

    color1 = p.color1.ctoi()
    color2 = p.color2.ctoi()
    
    img_rgb = np.zeros((height, width, 3), dtype=np.float32)
    img_a   = np.zeros((height, width), dtype=np.float32)

    radius_a = p.pwidth if p.pwidth > 10 else 10
    
    c_rate = np.clip(p.sub_jitter, 0, 99.99)
    radius_b = radius_a * (100-c_rate) / 100  # 収束率/100 × サイズ
    if radius_b < 2.0:
        radius_b = 2.0

    jitter = p.color_jitter
    if jitter < 0:
        jitter_channel = 3
        jitter = -jitter / 10.0
    else:
        jitter_channel=1
        jitter = jitter / 10.0

    overlap_h = np.clip(p.pheight / 100.0, -1.0, 0.8)
    overlap_v = np.clip(p.pdepth / 100.0, -1.0, 0.8)
    aa_width = AA_WIDTH

    x_coords = np.arange(width)
    y = height + radius_b

    while y >= -radius_a:
        # 非線形補間
        t_lin = 1.0 - (y / height)
        t_lin = np.clip(t_lin, 0.0, 1.0)
        t = t_lin ** GAMMA

        radius = lerp(radius_b, radius_a, t)

        fg_color = np.array([
            lerp(color2[i], color1[i], t) for i in range(3)
        ], dtype=np.float32)

        diameter = radius * 2
        pitch_x = diameter * (1 - overlap_h)
        pitch_y = diameter * (1 - overlap_v)

        count = int((width + pitch_x) // pitch_x)
        used_width = (count - 1) * pitch_x
        start_x = (width - used_width) / 2

        centers_x = start_x + np.arange(count) * pitch_x

        # ★ 円ごとの色ジッター
        jitter_vals = np.random.uniform(
            -jitter, jitter, size=(count, jitter_channel)
        )
        circle_colors = np.clip(
            fg_color + jitter_vals, 0, 255
        )

        y_min = max(0, int(y - radius - AA_WIDTH))
        y_max = min(height, int(y + radius + AA_WIDTH) + 1)

        for yy in range(y_min, y_max):
            dy = yy - y
            dy2 = dy * dy

            # 各 x の最近傍中心までの距離
            dx = x_coords[:, None] - centers_x[None, :]
            d2 = dx * dx + dy2
            #d = np.sqrt(np.min(d2, axis=1))

            # 最近傍の円
            idx = np.argmin(d2, axis=1)
            d = np.sqrt(d2[np.arange(width), idx])

            # アンチエイリアス付き α
            alpha = (radius + AA_WIDTH - d) / (2 * AA_WIDTH)
            alpha = np.clip(alpha, 0.0, 1.0)

            if np.all(alpha <= 0):
                continue

            circle_color = circle_colors[idx]

            # αブレンド
            dst_rgb = img_rgb[yy]

            dst_a   = img_a[yy]
            src_a = alpha
            out_a = src_a + dst_a * (1 - src_a)
            
            out_rgb = (
                circle_color * src_a[:, None] +
                dst_rgb * dst_a[:, None] * (1 - src_a[:, None])
            )
            
            out_rgb /= np.maximum(out_a[:, None], 1e-6)
            
            img_rgb[yy] = out_rgb
            img_a[yy]   = out_a

        y -= pitch_y

    rgba = np.dstack([np.clip(img_rgb, 0, 255), img_a*255]).astype(np.uint8)
    fg = Image.fromarray(rgba, "RGBA")
    
    if p.h_img is None:
        bg = Image.new('RGB', (width, height), p.color2.ctox())
    else:
        bg = p.bg()
        
    bg.paste(fg, (0,0), fg.split()[3])
    return bg    


if __name__ == "__main__":
    p = Param()
    p = default_param(p)

    p.width, p.height = 1920, 1080

    img = generate(p)
    img.show()
