import numpy as np
from PIL import Image
from wall_common import *
import TkEasyGUI as sg
import copy

#--------------------
# 定数
#--------------------
WIDTH = 1920
HEIGHT = 1080

TILE = 110
COLOR1 = (140, 100, 50)
COLOR2 = (30, 80, 120)
JITTER = 48  # c1,c2共通でrgbに加算(ただしclipされる)
BGCOLOR = (190, 195, 190)

DEFAULT_WEIGHTS = [
    # Name,         reverse_flag,   probability
    ["half_circle", 'r2', 0.8],
    ['half_dbl',    'r',  0.1],
    ["quarter",     'r',  1.0],
    ["quad_quarter",'r',  0.05],
    ["leaf",        'r2', 0.2],
    ["dbl_circle",  'r',  0.1],
    ["quad_circle", 'r',  0.05],
    ["haxa_circle", 'r',  0.02],
    ["ring",        'r1', 0.1],
    ["dbl_ring",    'r1', 0.1],
    ["triangle",    'n',  1.0],
    ['dbl_triangle','r',  0.5],
    ["box",         'n',  0.3],
    ["mesh",        'n1', 0.1],
    ["half_stripe", 'n',  0.1],
    ["stripe",      'n2', 0.1],
    ["circle",      'n1', 9.1],
]

FN = {}

bauhaus_preserv = {}

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'バウハウス風 (基本2色+明度加算2色)',
                       {'color1':'色1', 'color2':'色2', 'color3':'背景色',
                        'color_jitter':'明度加算',
                        'pwidth':'パターン幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color3.itoc(*BGCOLOR)
    p.color_jitter = JITTER
    p.pwidth = TILE
    return p


"""
build_tile_bank_aa 内のマスクパターン関数 pattern(x, y, S) の仕様
    x, y : np.ndarray (座標グリッド)
    S    : スケール後サイズ（s * scale）

    return:
        bool配列
        True  = 塗り
        False = 地

    マスク関数内では、タイルサイズはスケール後になるので以下に注意
    - 関数内のサイズ基準はすべて S に依存する必要あり
    - 中心座標は S 基準 cx, cy = S // 2, S // 2
    
"""

def register(func):
    FN[func.__name__] = func
    return func

@register
def triangle(x, y, S):
    return y >= x

@register
def circle(x, y, S):
    r = S // 2
    return ((x-r)**2 + (y-r)**2 <= r**2)

@register
def dbl_triangle(x, y, S):
    h = S // 2
    top = (y <= h) & (np.abs(x - h) <= y)
    bottom = (y >= h) & (np.abs(x - h) <= (y-h))
    return top | bottom

@register
def half_circle(x, y, S):
    r = S // 2
    left  = (x - 0)**2 + (y - S//2)**2 <= r**2
    right = (x - S)**2 + (y - S//2)**2 <= r**2
    return left | right

@register
def half_dbl(x, y, S):
    r = S // 2
    top = ((x - S//2)**2 + (y - S//2)**2 <= r**2) & (y < S//2)
    bottom = (x - S//2)**2 + (y - S)**2 <= r**2
    return top | bottom

@register
def quarter(x, y, S):
    return (x**2 + y**2 <= S**2)

@register
def quad_quarter(x, y, S):
    r = S // 2
    q1 = (x-S)**2 + y**2 <= r**2
    q2 = (x-S)**2 + (y-S)**2 <= r**2
    q3 = x**2 + (y-S)**2 <= r**2
    q4 = x**2 + y**2 <= r**2
    return q1|q2|q3|q4

@register
def leaf(x, y, S):
    return (x**2 + y**2 <= S**2) & ((x-S)**2 + (y-S)**2 <= S**2)

@register
def dbl_circle(x, y, S):
    r = S // 4
    q1 = (x - S//4)**2 + (y - S//4)**2 <= r**2
    q2 = (x - S//4)**2 + (y - 3*S//4)**2 <= r**2
    return q1 | q2

@register
def quad_circle(x, y, S):
    r = S // 4
    q1 = (x - S//4)**2 + (y - S//4)**2 <= r**2
    q2 = (x - S//4)**2 + (y - 3*S//4)**2 <= r**2
    q3 = (x - 3*S//4)**2 + (y - S//4)**2 <= r**2
    q4 = (x - 3*S//4)**2 + (y - 3*S//4)**2 <= r**2
    return q1 | q2 | q3 | q4

@register
def haxa_circle(x, y, S):
    r = S // 8
    q = np.zeros((S,S), dtype=bool)
    step = S // 4
    offset = step // 2
    for c in range(15):
        cx = (c % 4) * step + offset
        cy = (c // 4) * step + offset
        q |= (x - cx)**2 + (y - cy)**2 <= r**2
    return q

@register
def ring(x, y, S):
    cx, cy = S // 2, S // 2
    r_out = S // 2
    r_inn = S // 4
    dist = (x - cx)**2 + (y - cy)**2
    return (dist <= r_out**2) & (dist >= r_inn**2)

@register
def dbl_ring(x, y, S):
    cx, cy = S // 2, S // 2
    r_out = S // 2
    r_mid = S * 2 // 6
    r_inn = S // 6
    dist = (x - cx)**2 + (y - cy)**2
    return (dist <= r_out**2) ^ (dist <= r_mid**2) ^ (dist <= r_inn**2)

@register
def box(x, y, S):
    return (x < S//2)

@register
def mesh(x, y, S):
    sw = S//9
    return ((x % (2*sw)) < sw) ^ ((y % (2*sw)) < sw)

@register
def half_stripe(x, y, S):
    sw = S//8
    return ((x % (2*sw)) < sw) & (y < S//2)

@register
def stripe(x, y, S):
    sw = S//8
    return (x % (2*sw)) < sw


# =========================
# AA付きマスク生成
# =========================
def aa_mask(mask_func, s, scale=4):
    S = s * scale

    y, x = np.ogrid[:S, :S]
    mask_hi = mask_func(x, y, S)

    # float化して縮小
    img = Image.fromarray((mask_hi * 255).astype(np.uint8), 'L')
    img = img.resize((s, s), Image.Resampling.LANCZOS)

    return np.asarray(img) / 255.0  # 0.0〜1.0


# =========================
# タイルパターン生成（AA）
# =========================
def build_tile_bank_aa(s):
    bank = []
    weights = []
    names = []

    def add_pattern(name, base, reverse, weight, inv_ratio=0.25):
        for k in range(4):
            if (k > 1 and '2' in reverse) \
               or (k > 0 and '1' in reverse):
                break
            rot = np.rot90(base, k)

            bank.append(rot)
            weights.append(weight)
            names.append(name)

            if  'n' in reverse:
                continue
            bank.append(1.0 - rot)
            weights.append(weight * inv_ratio)
            names.append(name + '_inv')

    if 'funcs' not in bauhaus_preserv:
        bauhaus_preserv['funcs'] = copy.deepcopy(DEFAULT_WEIGHTS)
    
    for name, rvs, w in bauhaus_preserv['funcs']:
        base = aa_mask(FN[name], s)
        add_pattern(name, base, rvs, w)
    
    weights = np.array(weights, dtype=np.float32)
    weights /= weights.sum()

    return bank, weights, names

# =========================
# 詳細設定
# =========================
def item_sw(itm):
    # Name,         func_id,    reverse_flag,   probability
    name, flag, prob = itm
    line = [
        sg.Checkbox('', default=(prob>0), key=f'en_{name}',
                    group_id='switch'),
        sg.Text(name.ljust(12), size=(12,1)),
        sg.Combo(['r','r1','r2','n','n1','n2'], default_value=flag,
                 key=f'fl_{name}', width=3),
        sg.Input(key=f'pr_{name}', default_text=f'{prob:.2f}',
                 size=(5,1)),
        ]
    return line
    


def desc(p: Param):
    s = p.pwidth

    lines = []
    for itm in bauhaus_preserv['funcs']:
        lines.append(item_sw(itm))

    inum = len(lines)
    ilist = []
    row = 8
    for v in range((inum+row-1)//row):  # 1かラムrow行
        clayout = [[sg.Text('Mask Name', size=(14,1)),
                     sg.Text('Flag', size=(6,1)),
                     sg.Text('Prob.', size=(6,1))],]
        for w in range(row):
            k = v*row + w
            if k >= inum:
                break
            clayout.append(lines[k])
            
        ilist.append(sg.Column(layout=clayout, vertical_alignment='top'))
        #print(clayout)
        
    lo = [[sg.Text('Bauhaus風テキスタイル：タイルリスト')],
          [sg.Text('Flag: r/n=反転パターンのenable/disable　　　',
                   expand_x=True, text_align='right')],
          [sg.Text('1,2=回転パターンの制限(省略時4方向)',
                   expand_x=True, text_align='right')],
          ilist,
          [sg.Button('Reset', key='-reset-', background_color='#ffffdd'),
           sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button(' Done ', key='-ok-', background_color='#ddffdd'),
           ]]
    #print(lo)

    touched = False
    wn = sg.Window('mod Bauhaus', layout=lo, modal=True)
    while True:
        ev, va = wn.read()
        #print(va)

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            break
        if ev == '-ok-':
            if len(va['switch']) == 0:
                print('No patterns')
                continue
            
            ll = len(bauhaus_preserv['funcs'])
            for i in range(ll):
                itm = bauhaus_preserv['funcs'][i]
                name = itm[0]
                #print(name)
                if itm[1] != va['fl_'+name]:
                    itm[1] = va['fl_'+name]
                    touched = True
                if va['en_'+name]:
                    if itm[2] != float(va['pr_'+name]):
                        itm[2] = float(va['pr_'+name])
                        touched = True
                    elif itm[2] == 0.0:
                        itm[2] = 1.0
                        touched = True
                else:
                    if itm[2] != 0.0:
                        itm[2] = 0.0
                        touched = True
            break
        if ev == '-reset-':
            bauhaus_preserv['funcs'] = copy.deepcopy(DEFAULT_WEIGHTS)
            ll = len(bauhaus_preserv['funcs'])
            for i in range(ll):
                itm = bauhaus_preserv['funcs'][i]
                name = itm[0]
                if not 'en_'+name in va:
                    continue
                wn['en_'+name].update(True if itm[2] > 0 else False)
                wn['fl_'+name].update(value=itm[1])
                wn['pr_'+name].update(str(itm[2]) if itm[2] > 0 else '0.0')
            touched = True
            continue

    wn.close()
    if touched:
        bank, weights, names = build_tile_bank_aa(s)

        return generate(p)
    else:
        return


# =========================
# 描画色生成
# =========================
def pick_color(c, delta):
    if np.random.rand() < 0.5:
        base = np.array(c)
    else:
        base = np.array(c) + delta

    return np.clip(base, 0, 255).astype(np.uint8)

# =========================
# パターン生成（RGBA）
# =========================
def generate_pattern(w, h, s, c1, c2, delta):
    grid_w = (w + s - 1) // s + 1
    grid_h = (h + s - 1) // s + 1

    W = grid_w * s
    H = grid_h * s

    img = np.zeros((H, W, 4), dtype=np.uint8)

    bank, weights, names = build_tile_bank_aa(s)
    endur = len(bank) // 2

    for gy in range(grid_h):
        for gx in range(grid_w):
            pname = ''
            prgb = (0,0,0)
            for _ in range(endur):
                idx = np.random.choice(len(bank), p=weights)
                alpha = bank[idx]

                base = c1 if np.random.rand() < 0.5 else c2
                r, g, b = pick_color(base, delta)
                if pname != names[idx] and prgb != (r,g,b):
                    break
                pname = names[idx]
                prgb = (r,g,b)
            

            y0 = gy * s
            x0 = gx * s

            sub = img[y0:y0+s, x0:x0+s]

            a = (alpha * 255).astype(np.uint8)

            sub[..., 0] = r
            sub[..., 1] = g
            sub[..., 2] = b
            sub[..., 3] = a

    return img


# =========================
# crop
# =========================
def center_crop(img, w, h):
    H, W = img.shape[:2]
    x0 = (W - w) // 2
    y0 = (H - h) // 2
    return img[y0:y0+h, x0:x0+w]

# =========================
# 生成
# =========================
def generate(p: Param):
    w, h = p.width, p.height
    c1 = p.color1.ctoi()
    c2 = p.color2.ctoi()
    bgcolor = p.color3.ctoi()
    delta = p.color_jitter
    s = p.pwidth

    # パターン生成（RGBA）
    pattern_big = generate_pattern(w, h, s, c1, c2, delta)
    pattern = center_crop(pattern_big, w, h)
    fg = Image.fromarray(pattern, 'RGBA')

    # 背景（RGB）
    if p.h_img is not None:
        bg = p.bg(w, h)
    else:
        bg = Image.new('RGB', (w, h), bgcolor)

    # α付きで貼り付け
    bg.paste(fg, (0, 0), fg)
    return bg


# =========================
# テスト
# =========================
if __name__ == '__main__':
    p = Param()
    p = default_param(p)

    p.width, p.height = WIDTH, HEIGHT
    im = generate(p)

    im.show()
