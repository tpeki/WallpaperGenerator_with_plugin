import numpy as np
from PIL import Image
import TkEasyGUI as sg
from wall_common import *

# ストライプ設定
STRIPE_WIDTH = 40
BASE1 = (220, 180, 0)  # 基本色1
BASE2 = (160, 160, 240)  # 基本色2
DIFF_STRIPE = 8  # 色の揺らぎ

# グラデーション方向
GRAD_TOP_TO_BOTTOM = 0
GRAD_BOTTOM_TO_TOP = 1
GRAD_CENTER_DARK = 2
GRAD_EDGE_DARK = 3
NO_GRAD = 4
GRAD_STRENGTH = 40  # グラデーション強さ

chevron_preserv = {'gradation': [NO_GRAD, GRAD_STRENGTH]
                   }

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'ギザギザ模様(Chevlon)',
                       {'color1':'線色1', 'color2':'線色2',
                        'color_jitter':'色差分', 'pwidth':'線幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE1)
    p.color2.itoc(*BASE2)
    p.pwidth = STRIPE_WIDTH
    p.color_jitter = DIFF_STRIPE
    return p


def safeint(s, default=None, lo=None, hi=None):
    if not isinstance(s, str):
        r = default if default else 0
    else:
        try:
            r = int(s, 0)
        except ValueError:
            r =  default if default else 0

    if lo:
        r = max(r, lo)
    if hi:
        r = min(r, hi)
    return r


def desc(p: Param):
    itemdic = {'No Gradation': NO_GRAD,
               'TOP to BOTTOM': GRAD_TOP_TO_BOTTOM,
               'BOTTOM to TOP': GRAD_BOTTOM_TO_TOP,
               'CENTER Dark': GRAD_CENTER_DARK,
               'EDGE Dark': GRAD_EDGE_DARK,
               }
    items = [x for x in itemdic.keys()]

    orggrad, orgstr = chevron_preserv['gradation']
    orgitem = next(k for k, v in itemdic.items() if v == orggrad)
    jitter = p.color_jitter
    pwidth = p.pwidth

    lo = [[sg.Combo(items, default_value=orgitem, readonly=True, key='-grad-'), 
           sg.Text('Gradation Strength'),
           sg.Input(f'{orgstr}', size=(6,1), key='-str-'),],
          [sg.Text('Jitter'),
           sg.Input(f'{jitter}', size=(6,1), key='-jitter-'),],
          [sg.Text('Band Width'),
           sg.Input(f'{pwidth}', size=(6,1), key='-pwidth-'),],
          [sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Done', key='-ok-', background_color='#ddffdd'),
           ]]

    wn = sg.Window('Chevron Gradation', layout=lo)

    while True:
        ev, va = wn.read()

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            break
        if ev == '-ok-':
            grad = va['-grad-']
            gradv = itemdic[grad] if grad in itemdic else -1
            strength = safeint(va['-str-'], default=orgstr, lo=0)
            jitter = safeint(va['-jitter-'], default=jitter)
            pwidth = safeint(va['-pwidth-'], default=pwidth, lo=1)
            break
            
    wn.close()
    if 0<= gradv <= len(itemdic):
        chevron_preserv['gradation'] = [gradv, strength]
        p.color_jitter = jitter
        p.pwidth = pwidth
        return generate(p)
    
    return


def grad_func(pos, mode, strength):
    """pos: 0.0 - 1.0
    戻り値: 明るさ補正値（負もあり）"""

    if mode == GRAD_TOP_TO_BOTTOM:
        # 上:+strength, 下:-strength
        return (0.5 - pos) * 2.0 * strength

    elif mode == GRAD_BOTTOM_TO_TOP:
        # 上:-strength, 下:+strength
        return (pos - 0.5) * 2.0 * strength

    elif mode == GRAD_CENTER_DARK:
        # 中央:-strength, 上下:+strength
        return (np.abs(pos - 0.5) * 2.0 - 0.5) * 2.0 * strength

    elif mode == GRAD_EDGE_DARK:
        # 上下:-strength, 中央:+strength
        return (0.5 - np.abs(pos - 0.5) * 2.0) * 2.0 * strength

    else:
        return pos * 0.0


def generate(p: Param):
# def chevlon(width, height, swidth, color1, color2, jitter_width):
    # 座標グリッド生成
    width = p.width
    height = p.height
    swidth = min(max(p.pwidth,1),min(width, height))
    eps = p.color_jitter

    y, x = np.mgrid[0:height, 0:width]

    # 三角波
    period = swidth*2
    tri_x = np.abs((x % period) - swidth)

    # 赤・白マスク（同じ幅）
    v = tri_x + y
    t = v % period
    red_mask = t < swidth

    # 三角波ライン単位の色揺らぎ
    band = v // period
    max_band = int(band.max()) + 1
    rng = np.random.default_rng()

    # bandごとのランダム揺らぎ
    jitter_table = rng.integers(-eps, eps+1, size=(max_band, 3),
                                dtype=np.int16)

    # 領域ごとのグラデーション方向を決める
    grad_mode, grad_strength = chevron_preserv['gradation']

    # band位置 0..1
    band_pos = (np.linspace(0.0, 1.0, max_band, dtype=np.float32)
                if max_band > 1 else np.zeros(1, dtype=np.float32))

    grad_value_table = (grad_func(band_pos, grad_mode,
                                  grad_strength).astype(np.int16))

    # 各ピクセルに対応する揺らぎ
    jitter = jitter_table[band]
    grad = grad_value_table[band][:, :, None]  # RGB用

    base1 = np.array(p.color1.ctoi(), dtype=np.int16)
    base2 = np.array(p.color2.ctoi(), dtype=np.int16)

    redmask_flag = (band % 2 == 0)
    redmask = redmask_flag[:, :, None]

    # -------------------------
    # 色合成
    img_array = np.empty((height, width, 3), dtype=np.int16)

    img_array[red_mask] = base1 + jitter[red_mask] + grad[red_mask]
    img_array[~red_mask] = base2 + jitter[~red_mask] + grad[~red_mask]

    # clamp
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)

    # -------------------------
    # Bitmap生成
    # -------------------------
    img = Image.fromarray(img_array, "RGB")

    return img

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    image = generate(p)
    image.show()
