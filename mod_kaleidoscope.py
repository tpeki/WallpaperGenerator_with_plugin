import numpy as np
from PIL import Image
from wall_common import *

# ==========================================
# 定数
# ==========================================
WIDTH = 1920
HEIGHT = 1080
COLOR1 = (0x98, 0xac, 0x57)
COLOR2 = (0x32, 0x3f, 0x66)
ANGLE = 35
SIDE_LENGTH = 400
JITTER = 120
DENSITY = 12
ATTENATE = 4

def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'カレイドスコープ',
                       {'color1':'基本色', 'color2':'背景',
                        'color_jitter':'シード色幅',
                        'sub_jitter':'シード密度',
                        'sub_jitter2':'減衰(‰)',
                        'pwidth':'基本幅', 'pheight':'角度'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.pwidth = SIDE_LENGTH
    p.pheight = ANGLE
    p.color_jitter = JITTER
    p.sub_jitter = DENSITY
    p.sub_jitter2 = ATTENATE
    return p


def kaleidoscope(img, L, angle, atten):
    ow, oh = img.size
    L = min(max(ow,oh), max(L, min(ow, oh)//10))
    angle = min(max(0, angle), 360)
    eximg = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    max_iter=12
    src = np.array(eximg)
    h, w = src.shape[:2]
    sx = min((w-ow)//2, L//2)
    sy = min((h-oh)//2, L//2)
    cx = w/2 + np.random.randint(sx)
    cy = h/2 + np.random.randint(sy)

    # --- 正三角形（底辺水平） ---
    h_tri = np.sqrt(3) / 2 * L

    A = np.array([0.0, -2*h_tri/3])
    B = np.array([-L/2, h_tri/3])
    C = np.array([ L/2, h_tri/3])

    # 辺（法線付き）
    edges = [
        (A, B),
        (B, C),
        (C, A),
    ]

    def reflect_points(px, py, p1, p2, counts):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        L = np.sqrt(dx*dx + dy*dy)
        dx /= L
        dy /= L

        # 法線
        nx = -dy
        ny = dx

        vx = px - p1[0]
        vy = py - p1[1]

        dist = vx * nx + vy * ny

        # 外側だけ反射
        mask = dist > 0

        px[mask] -= 2 * dist[mask] * nx
        py[mask] -= 2 * dist[mask] * ny
        counts[mask] += 1  # ← これ追加

        return mask

    # --- 座標 ---
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    px = xx - cx
    py = yy - cy
    counts = np.zeros_like(px, dtype=np.int32)

    # --- 収束反射 ---
    for _ in range(max_iter):
        moved = np.zeros_like(px, dtype=bool)

        for p1, p2 in edges:
            m = reflect_points(px, py, p1, p2, counts)
            moved |= m

        if not moved.any():
            break
    
    # --- 元画像座標へ ---
    X = px + cx
    Y = py + cy

    # --- バイリニア ---
    X = np.clip(X, 0, w - 1)
    Y = np.clip(Y, 0, h - 1)

    x0 = np.floor(X)
    y0 = np.floor(Y)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)

    x0 = x0.astype(np.int32)
    y0 = y0.astype(np.int32)
    x1 = x1.astype(np.int32)
    y1 = y1.astype(np.int32)

    dx = (X - x0)[..., None]
    dy = (Y - y0)[..., None]

    out = (
        (1 - dx) * (1 - dy) * src[y0, x0] +
        dx * (1 - dy) * src[y0, x1] +
        (1 - dx) * dy * src[y1, x0] +
        dx * dy * src[y1, x1]
    )

    counts = np.minimum(counts, 50)
    reflect = (1-atten/100) ** counts
    out = out * reflect[..., None]
    out = np.clip(out, 0, 255).astype(np.uint8)

    eximg = Image.fromarray(out)
    eximg = eximg.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    W, H = eximg.size
    dx, dy = (W-ow)//2, (H-oh)//2
    return eximg.crop((dx,dy,dx+ow, dy+oh))


def seed(w, h, color1, color2, jitter, L, density=25):
    img = Image.new("RGB", (w, h), color2)
    draw = ImageDraw.Draw(img)

    cx, cy = w / 2, h / 2

    l_particle = max(min(1,L//3),40)  # 粒子径=窓サイズ/3 (最低長40)
    area_ratio = (w*h)/(np.sqrt(3)/4*L**2)
    n_particle = int(area_ratio*density)  # 粒子数=面積比*密度係数
    # print(area_ratio, n_particle)
    
    len2 = max(1, l_particle//5)    # line長 最短保証値
    len1 = max(1, l_particle-len2)  # line長 変動分
    len3 = min(150,len1*2)          # arc半径 最大値(最小はlen2)
    wmax = int(len2 * 3.0)          # 最大幅
    wmin = max(1, len2//2)          # 最小幅
    n_arcs = max(1, n_particle//3)      # arc配置数(切り取り前)
    n_lines = max(1, n_particle-n_arcs) # line配置数(切り取り前)
    # print(f'line {len1}+{len2} arc {len2}..{len3} width {wmin}..{wmax}')

    def jitter_color(base, jitter):
        j = int(np.random.normal(0,1)*jitter)
        j = abs(j)
        # print(f'{j} ', end='')
        if j == 0:
            return base
        return tuple(
            int(np.clip(c + np.random.randint(-j, j), 0, 255))
            for c in base
        )

    for _ in range(n_lines):
        # 始点
        x0 = np.random.uniform(0, w)
        y0 = np.random.uniform(0, h)

        # 中心方向ベクトル
        dx_c = cx - x0
        dy_c = cy - y0
        angle_center = np.arctan2(dy_c, dx_c)
        angle = angle_center + np.random.normal(scale=1.0) 
        # ランダム角 + 中心寄りに少しバイアス

        length = np.random.exponential(len1) + len2
        x1 = x0 + np.cos(angle) * length
        y1 = y0 + np.sin(angle) * length

        draw.line((x0, y0, x1, y1),
                  fill=jitter_color(color1, jitter),
                  width=random.randint(wmin, wmax),
                  joint='curve')

    for _ in range(n_arcs):
        cx = random.randint(-w//4, w + w//4)
        cy = random.randint(-h//4, h + h//4)

        r = random.randint(len2, len3)

        start = random.uniform(0, 360)
        span = random.uniform(15, 60)

        bbox = [
            cx - r, cy - r,
            cx + r, cy + r
        ]

        draw.arc(
            bbox,
            start=start,
            end=start + span,
            fill=jitter_color(color1, jitter),
            width=random.randint(wmin, wmax)
        )

    # img.show()
    return img


def generate(p: Param):
    w,h = p.width, p.height
    color1 = p.color1.ctoi()
    color2 = p.color2.ctoi()
    jitter = p.color_jitter
    density = p.sub_jitter
    atten  = p.sub_jitter2
    sidelength = p.pwidth
    angle = p.pheight / 2
    if p.h_img is None:
        bg = seed(w, h, color1, color2, jitter, sidelength, density)
    else:
        bg = p.bg()

    return kaleidoscope(bg, sidelength, angle, atten)

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width, p.height = WIDTH, HEIGHT

    out = generate(p)
    out.show()
