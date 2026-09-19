from wall_common import *
import numpy as np
from PIL import Image
import inspect
import TkEasyGUI as sg
import filedialog as fdi

TILE_SIZE = 160
TILE_RADIUS = 12
DEFAULT_COLORS = [(0xac, 0xd9, 0xec), (0xd8, 0xb7, 0xd8), (0x9e, 0xbd, 0x95),
                  (0xdd, 0xcb, 0x9f), (0xdd, 0x98, 0x73), (0x86, 0x73, 0xc8),]
BLACK = (0, 0, 0)
SHADOW = (0x48, 0x48, 0x4f)
MAX_COLORS = 6
USE_COLORS = 3
JITTER = 30
VARIETY = 0
JOINT_WIDTH = 10
JOINT_BRIGHTNESS = 0xd4

# 内部定数
# タイルのグラデーション
GRAD_STR = 30  # end_color = color*(1-GRAD_STR)
RAND_STR = 5  # 表面凹凸

# タイル影
SHADE_INT = 62
SHADE_THICK = 3

# パース/角度定数
ANGLE = 0
M3D = 0  # 0/1 OFF/ON
PERS = 0.27  # パース強度 0.01～0.3程度

# 目地の粒状感と粒の明るさ
JOINT_GRAIN = 0.1  # 砂目率
INT_BRT = 38  # 明るい地の時の減算率 8bit
INT_DRK = 128  # 暗い地の時の加算率 8bit
INT_BDR = 140  # 切替閾値 8bit

# タイル表面処理(scratched)
LINTERVAL = 20.0  # テクスチャ(斜線)密度 (d / LINTERVAL) 20.0だとd=60でも可
NOISE_THICK = 1.8  # 大きいほどnoiseが太目に出る
NOISE_RATE = 0.4  # 小さいほどnoise線の密度が上がる

# タイル表面処理(groovw)
GRVNUM = 3  # 溝数
GRVWIDTH = 60  # W/(NUM+1) * (GRVWIDTH/100)
GRVBOTTOM = 40  # 溝幅に対する溝底の幅%
GRVDEPTH = 25  # 溝の深さ(マイナスにすると盛り上がり)

tiles_preserv = {'color': {'ncolor': USE_COLORS, 'colors': DEFAULT_COLORS,
                           'jitter': JITTER, 'variety': 0,},
                 'common': {'tsize': TILE_SIZE, 'round': TILE_RADIUS,
                            '3d': M3D, 'pers': PERS, 'angle': ANGLE, },
                 'gradation': {'grad': GRAD_STR, 'color': BLACK,
                               'rand': RAND_STR},
                 'shade': {'intent': SHADE_INT, 'thick': SHADE_THICK,
                           'color': SHADOW},
                 'joint': {'color': None,
                           'thick': JOINT_WIDTH, 'grain': JOINT_GRAIN,
                           'bright':INT_BRT , 'dark': INT_DRK,
                           'boder': INT_BDR},
                 'surface': {'name': 'scratched'},
                 }

SURF = {}
DF = {}
def regi(func):
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    SURF[func.__name__] = func
    
    params = params[1:]  # 1つめの引数はSurfaceクラス
    defaults = {}
    for p in params:
        if p.default is not inspect._empty:
            defaults[p.name] = p.default
    DF[func.__name__] = defaults
    return func

                                               
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '正方形タイル',
                       {'color1':'色1', 'color2':'色2', 'color3':'色3',
                        'color_jitter':'色幅', 'sub_jitter':'目地明度',
                        'pwidth':'タイル幅', 'pheight':'角半径',
                        'pdepth':'目地幅(%)'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*DEFAULT_COLORS[0])
    p.color2.itoc(*DEFAULT_COLORS[1])
    p.color3.itoc(*DEFAULT_COLORS[2])
    p.pwidth = TILE_SIZE
    p.pheight = TILE_RADIUS
    p.pdepth = JOINT_WIDTH
    p.color_jitter = JITTER
    p.sub_jitter = JOINT_BRIGHTNESS
    return p


def get_hist(atname, catname, default=None, lo=None, hi=None):
    if catname in tiles_preserv:
        categ = tiles_preserv[catname]
    else:
        categ = {}
        tiles_preserv[catname] = categ
        
    if atname in categ:
        value = categ[atname]
        if value is None:
            value = default
            categ[atname] = value
    else:
        value = default
        categ[atname] = value

    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def set_hist(atname, catname, value):
    if catname not in tiles_preserv:
        tiles_preserv[catname] = {}
    tiles_preserv[catname][atname] = value
    
    return value

class Surface:
    def __init__(self, base):
        self.base = base  # line_base
        self.color = BLACK  # base_color
        self.sx = None  # x-array
        self.sy = None  # y-array
        self.dx = (0,0)  # dx0,dx1
        self.dy = (0,0)  # dy0,dy1
        self.row = 0
        self.col = 0

# ---
# 設定
# ---
def sg_modline(func, fsel):
    # ☑func    param[  ] ...
    line = [sg.Radio('', key=f'ts_{func}', group_id='surface',
                     default=(func==fsel)),
            sg.Text(func, size=(10,0))]

    if func not in tiles_preserv:
        tiles_preserv[func] = {}

    dflt = DF[func]
    if len(dflt) == 0:
        line.append(sg.Text('No Parameters'))
        return line
       
    for par in dflt.keys():
        line.append(sg.Text(f'{par}'))
        v = get_hist(par, func, dflt[par])
        line.append(sg.Input(f'{v}', key=f'-{func}_{par}-',width=5))

    return line


def read_modline(wn, func):
    dflt = DF[func]
    if func not in tiles_preserv:
        tiles_preserv[func] = {}

    for par in dflt.keys():
        s = wn[f'-{func}_{par}-'].get()
        v = stoi(wn[f'-{func}_{par}-'].get())
        
        # print(f'{v} <- [-{func}_{par}-] = {s}')
        if isinstance(dflt[par], int):
            v = int(v)
        elif isinstance(dflt[par], float):
            v = float(v)
        elif isinstance(dflt[par], bool):
            v = (v != 0)
        elif isinstance(dflt[par], list|tuple):
            if not isinstance(v, list|tuple):
                v = BLACK
        tiles_preserv[func][par] = v

    return len(dflt)        


    
def desc(p):
    W,H = p.width, p.height
    colors =  update_colors(p)
    num_colors = get_hist('ncolor', 'color', USE_COLORS)
    jitter = get_hist('jitter', 'color', p.color_jitter)
    cvar = get_hist('variety', 'color', VARIETY) == 1

    d = get_hist('tsize', 'common', p.pwidth)  #Tile size
    rr = get_hist('round', 'common', p.pheight)  # Tile radius
    persmode = get_hist('3d', 'common', 0) == 1  # Boolean
    pers_str = get_hist('pers', 'common', PERS)  # float
    angle = get_hist('angle', 'common', 0) % 360

    jw = get_hist('thick', 'joint', p.pdepth)
    jc = get_hist('color', 'joint')
    if not isinstance(jc, tuple|list):
        jb = clip8(p.sub_jitter)
        joint_color = ((jb,)*3)
    else:
        jb = clip8(sum(jc)/3)
        p.sub_jitter = jb
    jg = get_hist('grain', 'joint', JOINT_GRAIN)
    int_bdr = get_hist('border', 'joint', INT_BDR)
    int_brt = get_hist('bright', 'joint', INT_BRT)
    int_drk = get_hist('dark', 'joint', INT_DRK)

    grad = get_hist('grad', 'gradation', GRAD_STR)
    gradc = get_hist('color', 'gradation', BLACK)
    bump = get_hist('rand', 'gradation', RAND_STR)

    sh_i = get_hist('intent', 'shade', SHADE_INT)
    sh_c = get_hist('color', 'shade')
    if not isinstance(sh_c, tuple|list):
        sh_c = SHADOW
    sh_w = get_hist('thick', 'shade', SHADE_THICK)
    
    # サーフェス関数(動的メニュー)
    fsel = get_hist('name', 'surface', next(iter(SURF)))
    module_sect = []
    flag = True
    for fn in SURF:
        line = sg_modline(fn, fsel)
        flag = False
        if line is not None:
            module_sect.append(line)
    
    # 色設定項目の入力ボタン
    def color_cell(color, key):
        fgc,bgc = bg_and_font(color)
        return sg.Button(bgc[1:], key=key, width=6, text_color=fgc,
                         background_color=bgc, pad=((1,5),(1,1)))
    # 色設定項目の入力処理
    def get_color(key): # -> tuple|None
        oldc = '#' + wn[key].get()
        ci = to_rgb(sg.popup_color('Select Color',
                                   default_color=oldc))
        if ci is not None:
            fgc, bgc = bg_and_font(ci)
            wn[key].update(background_color=bgc, text_color=fgc,
                           text=f'{ci[0]:02X}{ci[1]:02X}{ci[2]:02X}')
        fdi.flush_ev(wn)
        return ci

    # tile spec
    common_sect = sg.Frame('Basic parameters',layout=[
        [sg.Text('Tile:', width=4),
         sg.Text('Size'), sg.Input(d, width=3, key='-common-tsize-'),
         sg.Text('  Coner%'), sg.Input(rr, width=3, key='-common-round-')],
        [sg.Text('Map:', width=4),
         sg.Text('Angle'), sg.Input(angle, width=3, key='-common-angle-'),
         sg.Text('  '),
         sg.Checkbox('3D', default=persmode, key='-common-3d-'),
         sg.Text('Pers'), sg.Input(pers_str, width=5, key='-common-pers-')],
        ], expand_x=True, expand_y=True)

    # color selector
    cp1 = []
    cp2 = []
    for i in range(3):
        cp1.append(sg.Text(f'{i+1}'))
        cp1.append(color_cell(colors[i], f'-c-{i}-'))
        cp2.append(sg.Text(f' {i+3}'))
        cp2.append(color_cell(colors[i+3], f'-c-{i+3}-'))
    color_sect = sg.Frame('Color', layout=[
        cp1, cp2,
        [sg.Text('Use colors'),
         sg.Input(num_colors, width=2, key='-colr-num_colors-'),
         sg.Text(' Jitter'), sg.Input(jitter, width=3, key='-colr-jitter-'),
         sg.Text(' Variety'),
         sg.Checkbox('', default=cvar, key='-colr-variety-')]
        ], expand_x=True, expand_y=True)

    # gradation
    gradation_sect = sg.Frame('Gradation', layout=[
        [sg.Text('Strength%'), sg.Input(grad, width=4, key='-g-grad-'),
         sg.Text('Shade'), color_cell(gradc, '-g-color-'),
         sg.Text('Bump'), sg.Input(bump, width=4, key='-g-rand-'),
         ]
        ], expand_x=True, expand_y=True)

    # shadow
    shade_sect = sg.Frame('Shadow', layout=[
        [sg.Text('Width'), sg.Input(sh_w, width=3, key='-shade-thick-'),
         sg.Text(' Intensity%'), sg.Input(sh_i, width=3, key='-shade-intent-'),
         sg.Text(' Color'), color_cell(sh_c, '-shade-color-'),]
        ], expand_x=True, expand_y=True)

    # Joint
    joint_sect = sg.Frame('Joint',layout=[
        [sg.Text('Width%'), sg.Input(jw, width=3, key='-joint-width-'),
         sg.Text(' Grain'), sg.Input(jg, width=3, key='-joint-grain-'),
         sg.Text(' Color'), color_cell(jc, '-joint-color-')],
        ], expand_x=True, expand_y=True)

    # Buttons
    button_sect = [sg.Text(expand_x=True),
                   sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
                   sg.Button('Done', key='-ok-', background_color='#ddffdd'),
                   ]
                   

    lo = [[sg.Column([[color_sect],
                      [gradation_sect]]
                     ),
           sg.Column([[common_sect],
                      [joint_sect],
                      [shade_sect]]
                     )],
           #           [sg.Text(expand_y=True)]],expand_y=True)],
          [sg.Frame('Surface', layout=module_sect, expand_x=True)],
          button_sect
          ]

    wn = sg.Window('Test', layout=lo)
    while True:
        ev, va = wn.read()

        if ev in ('-can-', sg.WINDOW_CLOSED):
            ev = '-can-'
            break
        elif ev.startswith('-c-'):
            no = int(ev[3])
            ci = get_color(ev)
            if ci is not None:
                colors[no] = ci
        elif ev.endswith('-color-'):
            ci = get_color(ev)
            if ci is not None:
                if ev.startswith('-g-'):
                    gradc = ci
                elif ev.startswith('-shade-'):
                    sh_c = ci
                elif ev.startswith('-joint-'):
                    jc = ci
        elif ev == '-ok-':
            break

    wn.close()
    # print(va)

    if ev == '-can-':
        return

    set_hist('ncolor', 'color', stoi(va['-colr-num_colors-'], lo=1, hi=6))
    p.color_jitter =  stoi(va['-colr-jitter-'], lo=0, hi=255)
    set_hist('jitter', 'color', p.color_jitter)
    set_hist('variety', 'color', 1 if va['-colr-variety-'] else 0)
    set_hist('colors', 'color', colors)
    p.color1 = RGBColor(colors[0])
    p.color2 = RGBColor(colors[1])
    p.color3 = RGBColor(colors[2])

    p.pwidth = stoi(va['-common-tsize-'], lo=1)
    set_hist('tsize', 'common', p.pwidth)
    p.pheight =  stoi(va['-common-round-'], lo=0, hi=50)
    set_hist('round', 'common', p.pheight)
    set_hist('3d', 'common', 1 if va['-common-3d-'] else 0)
    set_hist('pers', 'common', stoi(va['-common-pers-'], lo=0))
    set_hist('angle', 'common', stoi(va['-common-angle-']) % 360)

    p.pdepth = stoi(va['-joint-width-'], lo=0, hi=99)
    set_hist('thick', 'joint', p.pdepth)
    set_hist('grain', 'joint', stoi(va['-joint-grain-'], lo=0))
    set_hist('color', 'joint', jc)
    p.sub_jitter = clip8(sum(jc)/3)

    set_hist('grad', 'gradation', stoi(va['-g-grad-'], lo=0, hi=100))
    set_hist('color', 'gradation', gradc)
    set_hist('rand', 'gradation', stoi(va['-g-rand-'], lo=0, hi=99))

    set_hist('intent', 'shade', stoi(va['-shade-intent-'], lo=0, hi=100))
    set_hist('color', 'shade', sh_c)
    set_hist('thick', 'shade', stoi(va['-shade-thick-'], lo=0))

    for fname in SURF.keys():
         read_modline(wn, fname)

    if va['surface'].startswith('ts_'):
        set_hist('name', 'surface', va['surface'][3:])
    else:
        set_hist('name', 'surface', next(iter(SURF)))

    return generate(p)
                  

def update_colors(p):
    colors = get_hist('colors', 'color', DEFAULT_COLORS)
    colors.extend((BLACK,)*MAX_COLORS)
    colors = colors[:MAX_COLORS]

    colors[0] = p.color1.ctoi()
    colors[1] = p.color2.ctoi()
    colors[2] = p.color3.ctoi()
    for i in range(MAX_COLORS):
        if colors[i] is None or not isinstance(colors[i], tuple|list):
            colors[i] = BLACK

    set_hist('colors', 'color', colors)

    return colors


# ---
# タイルの質感設定 (拡張可)
# --- 関数定義
# @regi
# def function(s:Surface, anyparam1=any, anyparam2=any, ...)
#  -> s_rgb, s_mask, noise 各tileサイズのndarray
# --- 呼び出し
# メインからの呼び出しは function(s) だが、引数はsの属性に全部設定される
#  <基本パラメータ>
#  s.base = タイルの基本画像
#  s.color = タイルの表示色
#  s.sx, s.sy = x軸、y軸スライス
#  s.dx, s.dy = タイル座標 dx = (dx0, dx1), dy = (dy0, dy1)
#
#  <個別パラメータ>
#  s.any = 初期値つき引数で規定したパラメータの値
# ---
# - SURF[func] に関数ポインタ、DF[func][param]にパラメータ初期値が入る
# - GUIで設定した値はtiles_preserv[func]に一旦格納されるが、
#   pack_sf_params(s, func) で tiles_preserv[func]からsに値を詰め込んで呼び出し
#
@regi
def scratched(s: Surface,
                  pitch=LINTERVAL,
                  grain=NOISE_THICK,
                  density=NOISE_RATE):
    # エラー除け
    dx0, dx1 = s.dx
    dy0, dy1 = s.dy
    pitch = (dx1-dx0)/np.clip(s.pitch, 1, 100)
    grain = np.clip(s.grain, min=0)
    dens = np.clip(s.density, min=0)
    
    # ラインテクスチャ
    offset = np.random.rand() * pitch
    line_mask = ((s.base[s.sy, s.sx] + offset) % pitch) < grain
    noise = np.random.rand(dy1-dy0, dx1-dx0) > dens
   
    # ラインの色塗り (tile_rgbを直接書き換え)
    #line_rgb = s.color * np.random.uniform(0.7, 0.9)
    line_rgb = (
        s.color[None, None, :] *
        np.random.uniform(0.7, 0.9, (dy1-dy0, dx1-dx0, 1))
    ).astype(np.uint8)

    return line_rgb, line_mask, noise


@regi
def groove(s: Surface,
           num=GRVNUM, width=GRVWIDTH, bottom=GRVBOTTOM, depth=GRVDEPTH):
    dx0, dx1 = s.dx
    dy0, dy1 = s.dy
    w = dx1 - dx0
    h = dy1 - dy0
    ew = max(w, h)

    num = max(1, int(s.num))
    groove_width = max(1, int(ew/(num+1) * s.width/100))
    bwidth = np.clip(s.bottom/100, min=0, max=1-1E-5)
    dark = 1-s.depth/100
    slope = 0.9 - dark
    #print( f'{w}{s.dx}, {h}{s.dy}' )

    # タイルごとに縦・横を交替
    vertical = (s.row + s.col) % 2 == 0

    if vertical:
        pos = np.arange(w, dtype=np.float32) + s.sx.start
        centers = ew * (np.arange(num) + 1) / (num + 1)
        dist = np.min(np.abs(pos[:, None] - centers), axis=1)

        line_mask = (dist < groove_width / 2)[None, :]
        line_mask = np.broadcast_to(line_mask, (h, w))

        # 溝の中央からの距離
        r = dist / (groove_width / 2)

        # 中央bottom%は完全な濃色、外側は滑らかに明るくする
        shade = np.where(r <= bwidth, dark,
                         dark + slope * np.clip((r-bwidth) / (1-bwidth), 0, 1))
        shade = shade[None, :, None]
    else:
        #pos = np.arange(h, dtype=np.float32)
        #centers = h * (np.arange(num) + 1) / (num + 1)
        pos = np.arange(h, dtype=np.float32) + s.sy.start
        centers = ew * (np.arange(num) + 1) / (num + 1)
        dist = np.min(np.abs(pos[:, None] - centers), axis=1)

        line_mask = dist[:, None] < groove_width / 2
        line_mask = np.broadcast_to(line_mask, (h, w))

        r = dist / (groove_width / 2)
        shade = np.where(
            r <= bwidth, dark,
            dark + slope * np.clip((r-bwidth) / (1-bwidth), 0, 1)
        )
        shade = shade[:, None, None]

    # 色へ反映
    line_rgb = s.color[None, None, :] * shade
    line_rgb = np.broadcast_to(line_rgb, (h, w, 3))

    # ノイズ無し
    noise = np.ones((h, w), dtype=bool)
    
    return line_rgb, line_mask, noise

# ---
# 生成
# ---
def find_coeffs(pa, pb):
    """パース変換行列を計算するヘルパー関数"""
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
    A = np.matrix(matrix, dtype=float)
    B = np.array(pb).reshape(8)
    res = np.linalg.solve(A, B)

    return np.array(res).reshape(8)

def trans_pers(image, margin_w, margin_h, org_w, org_h, view):
    
    # --- パース変換の定義 ---
    # 大きな画像の中から、どの台形領域を抜き出して(width, height) に
    # フィットさせるか
    tilt = org_w * view  # パース強度 
    
    # ターゲット（台形）の4点座標
    # 奥（上辺）を狭くし、手前（下辺）を広く取る
    src_points = [
        (margin_w + org_w + tilt, margin_h + org_h), # 右下
        (margin_w - tilt, margin_h + org_h),      # 左下
        (margin_w + tilt, margin_h),              # 左上
        (margin_w + org_w - tilt, margin_h),     # 右上
    ]
    
    # 出力先の四隅
    dest_points = [
        (0, 0), (org_w, 0), (org_w, org_h), (0, org_h)
    ]

    coeffs = find_coeffs(dest_points, src_points)
    
    # 変形と同時に、指定サイズで切り出し
    image = image.transform((org_w, org_h), Image.PERSPECTIVE,
                            coeffs, Image.BICUBIC)

    return image


def pre_rotate_size(target_w, target_h, angle):
    """angle度回転した後targetが内接できるサイズ(W,H)を求める"""
    angle_rad = np.deg2rad(angle)
    s = abs(np.sin(angle_rad))
    c = abs(np.cos(angle_rad))

    # target を -angle 回転したときの外接矩形サイズ
    Bw = target_w * c + target_h * s
    Bh = target_w * s + target_h * c

    # 同じアスペクト比の外接矩形 temp_w,temp_h のスケール係数
    k = max(Bw / target_w, Bh / target_h)

    temp_w = k * target_w
    temp_h = k * target_h

    return int(temp_w), int(temp_h)  #, k


def make_shadow(mask_np, sintent=62, scolor=(0,0,0), sthick=1):
    if sintent == 0 or sthick == 0:
        return Image.new('RGBA', mask_np.shape[::-1], (0,0,0,0))

    sintent = clip8(sintent / 100 * 255)

    # 右下に1pxずらす
    shifted = np.zeros_like(mask_np)
    shifted[sthick:, sthick:] = mask_np[:-sthick, :-sthick]

    # 元のビットマップに上書き（必要なら合成ルールを変更）
    shadow_mask_np = np.where(mask_np == 0,  # 255 - shifted
                              shifted, 0).astype(np.uint8)

    
    # 影ビットマップ
    shadow_mask = Image.fromarray(shadow_mask_np).convert('L')
    shade = Image.new('RGBA', shadow_mask.size,
                      (*scolor, 255))
    shade.putalpha(shadow_mask.point(lambda x: x * sintent // 255))

    return shade


def pack_sf_params(s, fname):
    """s:SURF に,登録された関数fnameの引数に当たる値を詰め込む"""
    if fname not in SURF:
        return None
    params = DF[fname]
    for par in params.keys():
        v = get_hist(par, fname, params[par]) 
        setattr(s, par, v)
        # print(f'{fname}:{par} {v} default={params[par]}')
    return s


def generate(p: Param):
    org_w, org_h = p.width, p.height
    width, height = org_w, org_h

    # color
    colors =  update_colors(p)
    num_colors = get_hist('ncolor', 'color', USE_COLORS)
    jitter = set_hist('jitter', 'color', p.color_jitter)
    cvar = get_hist('variety', 'color', VARIETY) == 1
    for i in range(num_colors):
        colors[i] = to_rgb(rgb_random_jitter(RGBColor(colors[i]), jitter))

    # common
    tile_size = set_hist('tsize', 'common', p.pwidth)  #Tile size
    rr = set_hist('round', 'common', p.pheight)  # Tile radius
    persmode = get_hist('3d', 'common', 0) == 1  # bolean
    pers_str = get_hist('pers', 'common', PERS)
    if persmode:  # 3dにする場合は元画像を大きめに
        margin_w, margin_h = int(width*0.3), int(height*0.3)
        width = width + margin_w*2
        height = height + margin_h*2

    angle = get_hist('angle', 'common', 0) % 360  # degree
    if angle != 0:
        a_width, a_height = width, height
        width, height = pre_rotate_size(width, height, angle)
    
    # joint
    jw = set_hist('thick', 'joint', p.pdepth)
    joint_width = max(1, int(tile_size * jw / 100))
    d = tile_size + joint_width
    jb = clip8(p.sub_jitter)
    joint_color = get_hist('color', 'joint')
    if joint_color is None:
        joint_color = set_hist('color', 'joint', (jb,)*3)
    else:
        jb = clip8(sum(joint_color)/3)
        p.sub_jitter = jb
    
    joint_grain = get_hist('grain', 'joint', JOINT_GRAIN)
    int_bdr = get_hist('border', 'joint', INT_BDR, lo=0, hi=255)
    if jb > int_bdr:
        sand_intensity = (255 -
                          get_hist('bright', 'joint', INT_BRT, 0, 255))/256
        sand_int_add = 0
    else:
        sand_intensity = 0
        sand_int_add = (((int_bdr-jb)/int_bdr)**2 *
                        get_hist('dark', 'joint', INT_DRK))

    # shadow
    sintent = get_hist('intent', 'shade', SHADE_INT)
    scolor = get_hist('color', 'shade')
    if not isinstance(scolor, tuple):
        scolor = SHADOW
    sthick = get_hist('thick', 'shade', SHADE_THICK)

    # gradation
    grad = get_hist('grad', 'gradation', GRAD_STR) / 100
    gcolor = get_hist('color', 'gradation')
    if not isinstance(gcolor, tuple):
        gcolor = BLACK
    bump = 1.0 - get_hist('rand', 'gradation', RAND_STR, lo=0, hi=99) / 100.0

    # surface
    func = get_hist('name', 'surface', next(iter(SURF)))

    # 1. ベース作成（目地色）
    baseimg = p.bg(width, height)
    if baseimg is None:
        baseimg = Image.new('RGB', (width, height), joint_color)
    else:
        baseimg = baseimg.convert('RGB')

    img_array = np.asarray(baseimg, dtype=np.float32)
    tile_alpha = np.zeros((height, width), dtype=np.uint8)
    
    # 目地の砂目
    grain_mask = np.random.rand(height, width) < joint_grain
    img_array[grain_mask] *= sand_intensity
    img_array[grain_mask] += sand_int_add
    
    tile_size = d - joint_width
    rows = (height + d - 1) // d
    cols = (width + d - 1) // d
    total_h = rows * d
    total_w = cols * d
    offset_y = (height - total_h) // 2
    offset_x = (width - total_w) // 2

    # タイルごとの色インデックスを記録
    color_idx = np.full((rows, cols), -1, dtype=int)

    # --- 共通データの事前計算 ---
    ty, tx = np.meshgrid(np.arange(tile_size),
                         np.arange(tile_size), indexing='ij')
    
    # 角丸マスク
    mask_full = np.ones((tile_size, tile_size), dtype=bool)
    tr = min(max(0, int(tile_size * rr / 100)), tile_size//2)
    #print(f'tile:{d} round:{rr}% -> {tr}')
    
    corners = [(tr, tr), (tr, tile_size-1-tr), (tile_size-1-tr, tr),
               (tile_size-1-tr, tile_size-1-tr)]
    for i, (cy, cx) in enumerate(corners):
        dist_sq = (ty - cy)**2 + (tx - cx)**2
        if i == 0:
            region = (ty < tr) & (tx < tr)
        elif i == 1:
            region = (ty < tr) & (tx > cx)
        elif i == 2:
            region = (ty > cy) & (tx < tr)
        else:
            region = (ty > cy) & (tx > cx)
        mask_full[region] = dist_sq[region] <= tr**2

    # グラデーションマップ
    grad_map = ((ty + tx) / ((tile_size - 1) * 2)
                ).astype(np.float32)[:, :, np.newaxis]
    #print(grad_map.shape)

    surf = Surface((ty + tx).astype(np.float32))  # line_base
    pack_sf_params(surf, func)

    # --- 各タイルの描画 ---
    for row in range(rows):
        y0 = offset_y + row*d + joint_width//2
        dy0, dy1 = max(0, y0), min(y0 + tile_size, height)
        if dy1 <= dy0: continue
        sy = slice(dy0 - y0, dy1 - y0)
        surf.sy = sy
        surf.dy = (dy0, dy1)
        surf.row = row

        for col in range(cols):
            x0 = offset_x + col*d + joint_width//2
            dx0, dx1 = max(0, x0), min(x0 + tile_size, width)
            if dx1 <= dx0: continue
            sx = slice(dx0 - x0, dx1 - x0)
            surf.sx = sx
            surf.dx = (dx0, dx1)
            surf.col = col

            # 色の決定
            if num_colors < 2:
                c_idx = 0
            elif num_colors == 2:  # 2色の場合は市松模様
                c_idx = (row + col) % 2
            else:  # 3色以上の場合は、同色3枚隣接禁止のランダム
                possible_idx = list(range(num_colors))
                for e0,e1 in ((-2,0), (-1,-1), (-1,1)):
                    
                    if (0 <= col+e1 < cols) and \
                       0 <= row+e0 and \
                       color_idx[row-1, col] == color_idx[row+e0, col+e1]:
                        invalid = color_idx[row-1, col]
                        if invalid in possible_idx:
                            possible_idx.remove(invalid)
                for e0,e1 in ((-1,-1), (-1,0), (0,-2)):
                    if 0 <= col+e1 and \
                       (0 <= row+e0 < rows) and \
                       color_idx[row, col-1] == color_idx[row+e0, col+e1]:
                        invalid = color_idx[row, col-1]
                        if invalid in possible_idx:
                            possible_idx.remove(invalid)
                            
                c_idx = np.random.choice(possible_idx)

            color_idx[row, col] = c_idx
            if cvar:
                tmpc = to_rgb(rgb_random_jitter(RGBColor(colors[c_idx]),
                                                jitter//2))
                base_color = np.array(tmpc, dtype=np.float32)
            else:
                base_color = np.array(colors[c_idx], dtype=np.float32)
            
            # タイルテクスチャ  ###
            tile_rgb = np.broadcast_to(base_color, (dy1 - dy0, dx1 - dx0, 3)
                                       ).copy()
            surf.color = base_color
            s_rgb, s_mask, noise = SURF[func](surf)
            tile_rgb[s_mask & noise] = s_rgb[s_mask & noise]

            # グラデーション
            tile_rgb *= 1.0 - grad_map[sy, sx] * grad
            # 全面ノイズ
            tile_rgb *= np.random.uniform(bump, 1.0, (dy1 - dy0, dx1 - dx0, 1)
                                          ).astype(np.float32)

            # マスク適用
            m = mask_full[sy, sx]
            img_array[dy0:dy1, dx0:dx1][m] = tile_rgb[m]  # .astype(np.uint8)
            tile_alpha[dy0:dy1, dx0:dx1][m] = 255

    # ビットマップ化＋影付け
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    image = Image.fromarray(img_array).convert('RGBA')
    
    shadow = make_shadow(tile_alpha, sintent, scolor, sthick)
    image.alpha_composite(shadow)

    if angle != 0:
        image = image.rotate(angle, resample=Image.BICUBIC, expand=True)
        iw, ih = image.size
        sx, sy = (iw-a_width)//2,(ih-a_height)//2 
        # image.show()
        # print(iw,ih, '->', sx,sy, sx+a_width, sy+a_height)
        image = image.crop((sx,sy, sx+a_width, sy+a_height))

    if persmode:
        image = trans_pers(image, margin_w, margin_h,
                           org_w, org_h, pers_str)
                          
    return image

# --- 実行 ---
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width, p.height = 1920, 1080
    
    image = generate(p)
    image.show()
