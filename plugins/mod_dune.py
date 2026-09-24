import numpy as np
from PIL import Image
from wall_common import *

# --- 基本パラメータ ---
SAND_COLOR = (224, 196, 150)  # ベースカラー
JITTER = 5
DUNE_FREQ = 36  # 砂丘周期 整数 (内部で10で割る 2.4)
FREQ_JITTER = 8
RIPPLE_FREQ = 17  # 指定 freqとの比率 freq24なら60ぐらい
DIRECTION_DEG = 55
VIEW_TILT = 26  #度 rad=0.73


DUNE_HEIGHT = 1.7
RIPPLE_HEIGHT = 0.02
WARP_STRENGTH = 0.04
SLOPE_STRENGTH = 3.5
LIGHT_DIR=(0.8, 0.3, 0.81)  # 低めの太陽


# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '砂の惑星',
                       {'color1':'砂色',
                        'color_jitter':'色ゆらぎ',
                        'sub_jitter':'周期ゆらぎ',
                        'sub_jitter2':'方向(度)',
                        'pwidth':'砂丘', 'pheight':'風紋',
                        'pdepth':'視点角(～90度)'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*SAND_COLOR)
    p.color_jitter = JITTER
    p.sub_jitter = FREQ_JITTER
    p.sub_jitter2 = DIRECTION_DEG
    p.pwidth = DUNE_FREQ
    p.pheight = RIPPLE_FREQ
    p.pdepth = VIEW_TILT
    return p


# 投影
def normalize(arr):
    mn = arr.min()
    mx = arr.max()
    if mx - mn < 1e-8:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


# =========================
# 1D 移動平均（SIMD風）
# =========================
def blur_1d_axis(arr, radius, axis):
    if radius <= 0:
        return arr

    k = radius * 2 + 1

    pad = [(0, 0)] * arr.ndim
    pad[axis] = (radius, radius)

    arr_padded = np.pad(arr, pad, mode='reflect')

    # cumsum前に0パディングを1つ入れるのがポイント
    c = np.cumsum(arr_padded, axis=axis, dtype=np.float32)

    pad_shape = list(c.shape)
    pad_shape[axis] = 1
    c = np.concatenate(
        [np.zeros(pad_shape, dtype=c.dtype), c],
        axis=axis
    )

    sl1 = [slice(None)] * arr.ndim
    sl2 = [slice(None)] * arr.ndim

    sl1[axis] = slice(k, k + arr.shape[axis])
    sl2[axis] = slice(0, arr.shape[axis])

    result = (c[tuple(sl1)] - c[tuple(sl2)]) / k

    return result


# =========================
# Gaussian近似（Separable）
# =========================
def gaussian_simd(arr, radius, passes=2):
    arr = arr.astype(np.float32)

    for _ in range(passes):
        arr = blur_1d_axis(arr, radius, axis=1)
        arr = blur_1d_axis(arr, radius, axis=0)

    return arr


def generate(p: Param):
    width, height = p.width, p.height
    # base_color = p.color1.ctoi()
    jitter = p.color_jitter
    dune_freq = p.pwidth / 10
    freq_jitter = p.sub_jitter / 10
    dune_height = DUNE_HEIGHT
    ripple_freq = dune_freq * p.pheight
    ripple_height = RIPPLE_HEIGHT
    direction_deg = p.sub_jitter2 % 360
    warp_strength = WARP_STRENGTH
    slope_strength = SLOPE_STRENGTH
    view_tilt = p.pdepth/180*np.pi
    light_dir = LIGHT_DIR

    dune_freq = dune_freq + (np.random.uniform()-0.5)*freq_jitter
    dune_freq = max(0.5, dune_freq)
    base_color = rgb_random_jitter(p.color1, jitter).ctoi()

    #print(f'Dune   {dune_freq}, {dune_height}')
    #print(f'Ripple {ripple_freq}, {ripple_height}')
    #print(f'View   {view_tilt}, {light_dir}')

    # =========================
    # 座標（遠近）
    # =========================
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)

    # 遠くを圧縮
    y = 1 - (1 - y) ** (1.0 / (view_tilt+1E-5))

    X, Y = np.meshgrid(x, y)

    theta = np.deg2rad(direction_deg)
    Xr = X * np.cos(theta) + Y * np.sin(theta)

    # =========================
    # 地形ゆらぎ（自然さ）
    # =========================
    terrain_noise = gaussian_simd(
        np.random.randn(height, width),
        radius=60,
        passes=3
        )
    terrain_noise = normalize(terrain_noise)

    warped_X = Xr + warp_strength * (terrain_noise - 0.5)

    # =========================
    # 二層構造
    # =========================
    dunes = dune_height * np.sin(2 * np.pi * dune_freq * warped_X)

    # 風紋は丘の影響を受ける（強度変調）
    ripple_mask = normalize(np.abs(dunes))
    ripples = ripple_height * ripple_mask * \
        np.sin(2 * np.pi * ripple_freq * warped_X)

    # ---
    # 周波数ノイズ
    freq_noise = gaussian_simd(
        np.random.randn(height, width),
        radius=80,
        passes=3
        )
    freq_noise = normalize(freq_noise) - 0.5

    local_freq = ripple_freq * (1 + 0.35 * freq_noise)

    # 位相ノイズ
    #phase_noise = gaussian_filter(np.random.randn(height, width), 25)
    #phase_noise = normalize(phase_noise) - 0.5

    raw = np.sin(
        2 * np.pi * local_freq * warped_X
        #+ 4.0 * phase_noise
    )

    # 非対称化
    raw = np.sign(raw) * np.abs(raw) ** 1.6

    ripples = ripple_height * ripple_mask * raw
    # ---

    height_map = dunes + ripples

    # =========================
    # 法線
    # =========================
    dx, dy = np.gradient(height_map)

    # slope_strength = 4.5  # 写真的最適値
    normal = np.dstack((
        -dx * slope_strength,
        -dy * slope_strength,
        np.ones_like(height_map)
    ))

    norm = np.linalg.norm(normal, axis=2, keepdims=True)
    normal /= norm

    light = np.array(light_dir)
    light = light / np.linalg.norm(light)

    shading = np.dot(normal, light)
    shading = np.clip(shading, 0, 1)

    # =========================
    # 空気遠近（遠くを薄く）
    # =========================
    distance_fade = np.linspace(1.0, 0.7, height).reshape(height, 1)
    shading *= distance_fade

    # =========================
    # 微粒子感（控えめ）
    # =========================
    #grain = gaussian_filter(np.random.randn(height, width), 1.2)
    grain = np.random.randn(height, width)
    shading += 0.04 * grain
    shading = np.clip(shading, 0, 1)

    # =========================
    # カラー合成
    # =========================
    img_array = np.zeros((height, width, 3), dtype=np.uint8)

    for i in range(3):
        channel = base_color[i] * (0.35 + 0.9 * shading)
        img_array[:, :, i] = np.clip(channel, 0, 255)

    return Image.fromarray(img_array.astype(np.uint8))


if __name__ == "__main__":
    p = Param()
    p = default_param(p)
    p.width, p.height = 1920, 1080

    img = generate(p)
    img.show()
