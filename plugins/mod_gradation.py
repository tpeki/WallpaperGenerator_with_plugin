if __name__ == '__main__':
    import _4debug

from wall_common import *
import numpy as np
from PIL import Image
import TkEasyGUI as sg
import filedialog as fdi
import os.path as pa


# 外部定数
START_COLOR = (100, 100, 230)
END_COLOR = (36, 124, 136)
MID_COLOR = (224, 120, 54)
ANGLE = 90
MIDDLE_POINT1 = 70
MIDDLE_POINT2 = 50

# 内部定数
Scheme = [
    #type 0  /Desc 1     /colors 2/Angle 3 /Mid1 4   /Mid2 5'○''×'
    ['flat', 'Flat plain'    , 1,   False, '－',         '－'     ],  # 0
    ['2gra', '2colors Linear', 2,   True,  'MidPos(%)',  '－'     ],  # 1
    ['3gra', '3colors Linear', 3,   True,  'MidPos(%)',  '－'     ],  # 2
    ['2rad', '2colors Radial', 2,   True,  'Hpos(%)',    'Vpos(%)'],  # 3
    ['shpe', 'Shaped Radial' , 2,   False, 'Hpos(%)',    'Vpos(%)'],  # 4
    ['2glt', '2colors+Lattice',3,   True,  'MidPos(%)',  'Slit W' ],  # 5
    ]

Palette_set = {'Asayake': ['#183068', '#1f6000', '#e07836'],
               'Bondi':   ['#0cd8aa', '#21a78f', '#76ecef'],
               'Green':   ['#8eb92b', '#1f6000', '#3aad3a'],
               'Pinky':   ['#e877f4', '#ff7dbe', '#e6e6e6'],
               'Sands':   ['#e4d8a5', '#c2aa6b', '#dbc7ac'],
               'Sunflower':   ['#2d7bfd', '#fff74d', '#413cff'],
             }

Default_scheme = 2
Default_palette = 'Asayake'

DATA_DIR = 'samples'
ZIP_FILE = 'gradation.zip'
Cdis = '#f0f0f0'
Csel = '#ffffdd'
Nsel = Cdis
Chdr = '#989898'
INTERNAL = '*GUI*'  # internal palette name must include '*'

# 不揮発変数
gradation_preserv = {'scheme': Default_scheme,
                     'palette': Default_palette,
                     'palette_set': Palette_set.copy(),
                     'found_pal': []
                     }

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       '三色染め分け(グラデーション)',
                       {'color1':'始色', 'color2':'終色', 'color3':'中間色',
                        'pwidth':'角度', 'pheight':'中間位置1%',
                        'pdepth':'中間位置2%'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    pal = Palette_set[Default_palette]
    p.color1 = RGBColor(pal[0])  # Start
    p.color2 = RGBColor(pal[1])  # End
    p.color3 = RGBColor(pal[2])  # Midpoint
    p.pwidth = ANGLE
    p.pheight = MIDDLE_POINT1
    p.pdepth = MIDDLE_POINT2
    return p


def get_hist(attr):
    return gradation_preserv.get(attr)

def set_hist(attr, v):
    if attr in gradation_preserv:
        gradation_preserv[attr] = v
        return v
    return None


# 詳細設定
def desc(p):
    def cbutton(n):
        r,g,b = to_rgb(colset[n][0])
        return sg.Button(f'{r},{g},{b}', key=f'-col{n+1}-', width=10,
                     text_color=colset[n][1], background_color=colset[n][0])

    def change_color(palette):
        """palette = [color1, color2, color3]"""
        for n in range(3):
            color = palette[n]
            r,g,b = to_rgb(color)
            fgc, bgc = bg_and_font(color)
            colsno = [0,2,1][n]
            colset[colsno] = [bgc, fgc]

            wn[f'-col{n+1}-'].update(text=f'{r},{g},{b}',
                                     text_color=fgc, background_color=bgc)

        cpattern = [[colset[0][0], Cdis, Cdis],
                    [colset[0][0], colset[2][0], Cdis],
                    [colset[0][0], colset[2][0], colset[1][0]]]
        for sno in range(len(Scheme)):
            sc = Scheme[sno]
            if 0< sc[2] < 4:
                cpat = cpattern[sc[2]-1]
            else:
                cpat = [Cdis,Cdis,Cdis]

            for n in range(3):
                wn[f'-c{n+1}_s{sno}-'].update(background_color=cpat[n])

    def pcolor_to_current():
        colors = [rgb_string(p.color1),
                  rgb_string(p.color2), rgb_string(p.color3)]  # start, mid, end
        return INTERNAL, colors
        
    # desc本体
    cur_pal = get_hist('palette')
    tmp_colors = get_pal(cur_pal)
    if tmp_colors is None:
        cur_pal, tmp_colors = pcolor_to_current()
    colors = tmp_colors.copy()
    
    colset = []
    for x in range(3):
        fg, bg = bg_and_font(colors[x])
        colset.append([bg, fg])
        
    init_sc = get_hist('scheme')
    if len(Scheme) <= init_sc or init_sc < 0:
        init_sc = 2
    angle = p.pwidth
    mid1 = min(max(p.pheight, 0), 100)  # 中間位置1(相対位置を%で指定)
    mid2 = min(max(p.pdepth, 0), 100)  # 中間位置2(相対位置を%で指定)

    sheme_sect =  [scheme_selector(n, colset, True if n == init_sc else False)
                   for n in range(len(Scheme))]

    header_sect = [sg.Text(width=2), sg.Text(width=14),
                   sg.Text('Start', width=10),
                   sg.Text('Midpoint', width=10),
                   sg.Text('End', width=10),
                   sg.Text('Angle', width=4),
                   sg.Text('Param1', width=10),
                   sg.Text('Param2', width=10),
                   ]

    top_sect = [sg.Text(width=2),
                sg.Text('Scheme', width=14, background_color=Chdr,
                        text_color='white'),
                cbutton(0),
                cbutton(2),
                cbutton(1),
                sg.Input(f'{angle}', key='-angl-', width=4),
                sg.Input(f'{mid1}', key='-mid1-', width=10),
                sg.Input(f'{mid2}', key='-mid2-', width=10),
                ]

    func_sect = [[sg.Text('')],
                 [sg.Button('Revert', key='-frevt-', width=5,
                            background_color='#ddddff')],
                 [sg.Button('M <> E', key='-fswap-', width=5,
                            background_color='#ddddff')],
                 [sg.Button('S -> E', key='-fcopy-', width=5,
                            background_color='#ddddff')],
                 [sg.Button('Dim', key='-fdimm-', width=5,
                            background_color='#ddddff')],
                 [sg.Button('Bright', key='-fbrgt-', width=5,
                            background_color='#ddddff')],
                 [sg.Text(expand_y=True)]]
                 

    pal_items = update_pal_items()
    button_sect=[sg.Text(width=2),
                 sg.Text('Load Palette', background_color='#ffffdd'),
                 sg.Combo(values=pal_items, default_value=cur_pal,
                          enable_events=True, key='-pal-', readonly=True,
                          width=9),
                 sg.Text(' '),
                 sg.Button('Save Palette', key='-sv-',
                           background_color='#ffffdd'),
                 sg.Text('', key='-fname-', expand_x=True),
                 sg.Button('Cancel', key='-can-', width=5,
                           background_color='#ffdddd'),
                 sg.Button('Done', key='-ok-', width=5,
                           background_color='#ddffdd'),
                 ]
    left_part = sg.Column(layout=[header_sect,
                                  top_sect,
                                  *sheme_sect,])
    right_part = sg.Column(layout=func_sect, expand_y=True)

    lo = [[left_part, right_part],
          button_sect
          ]

    wn = sg.Window('Gradation config', lo)
    while True:
        fdi.flush_ev(wn)
        ev,va = wn.read()

        #print(ev, f'{colors}, pal={cur_pal}\n', get_hist('palette_set')['Asayake'])

        if ev in ('-can-', sg.WINDOW_CLOSED):
            ev = '-can-'
            break
        elif ev == '-ok-':
            break
        elif ev.startswith('-col'):
            n = int(ev[4])
            # print(n, rgb_string(colors[n-1]))
            cc = colors[n-1]
            nc = sg.popup_color(f'Select Color{n}', cc, format='tuple')
            fdi.flush_ev(wn)
            if nc != cc:
                colors[n-1] = nc
                change_color(colors)
                cur_pal = INTERNAL
        elif ev.startswith('-sc_'):
            s = ev[4:-1]
            # sno = sum(i+1 if x[0] == s else 0 for i,x in enumerate(Scheme))
            # scs = sno - 1
            scs = scheme_index(s)
            for i in range(len(Scheme)):
                c = Csel if i == scs else Nsel
                wn[f'-sct_s{i}-'].update(background_color=c)
            wn.refresh()
        elif ev == '-pal-':
            tmp_colors = get_pal(va['-pal-'])
            if tmp_colors == None:
                cur_pal, tmp_colors = pcolor_to_current()
                wn['-pal-'].update(value=cur_pal)
            else:
                cur_pal = va['-pal-']
            colors = tmp_colors.copy()
            change_color(colors)
            if cur_pal != INTERNAL:
                set_hist('palette', cur_pal)
            #print('-- end pal --')
        elif ev == '-sv-':
            fname = fdi.save_palette(colors, init_dir=DATA_DIR, mode='o')
            fdi.flush_ev(wn)
            if fname is not None:
                cur_pal = pa.splitext(pa.basename(fname))[0]
                wn['-fname-'].update(cur_pal)
                pal_items = update_pal_items()  # プルダウン更新
                wn['-pal-'].update(values=pal_items, value=cur_pal)
                set_hist('palette', cur_pal)  # 現在のパレット名更新
                pset = get_hist('palette_set')  # キャッシュからは削除
                if (cur_pal in pset) and\
                   (cur_pal not in Palette_set.keys()):
                    pset.pop(cur_pal)
                set_hist('palette_set', pset)
        elif ev == '-frevt-':
            nc = colors[0]
            colors[0] = colors[1]
            colors[1] = nc
            change_color(colors)
            cur_pal = INTERNAL
        elif ev == '-fswap-':
            nc = colors[1]
            colors[1] = colors[2]
            colors[2] = nc
            change_color(colors)
            cur_pal = INTERNAL
        elif ev == '-fcopy-':
            colors[1] = colors[0]
            change_color(colors)
            cur_pal = INTERNAL
        elif ev == '-fdimm-':
            for i in range(3):
                colors[i] = to_rgb(brightness(RGBColor(colors[i]), f=0.9))
            change_color(colors)
            cur_pal = INTERNAL
        elif ev == '-fbrgt-':
            for i in range(3):
                colors[i] = to_rgb(brightness(RGBColor(colors[i]), f=1.1))
            change_color(colors)
            cur_pal = INTERNAL

        # print(ev, va, wn['-pal-'].get())

    wn.close()
    if ev == '-ok-':
        set_hist('palette', cur_pal)
        s = va['-scheme-']
        if s.startswith('-sc_'):
            s = s[4:-1]
        # sno = sum(i+1 if x[0] == s else 0 for i,x in enumerate(Scheme))
        # scheme = sno - 1 if sno > 0 else Default_scheme 
        set_hist('scheme', scheme_index(s))

        #print(va)
        #print(f'{scheme}: {Scheme[scheme][0]}')

        angl = stoi(va['-angl-'], lo=0, hi=360)
        mid1 = stoi(va['-mid1-'], lo=0, hi=100)
        mid2 = stoi(va['-mid2-'], lo=0, hi=100)

        for x in range(3):
            xx = [0,1,2][x]
            setattr(p, f'color{x+1}', RGBColor(colors[xx]))
        p.pwidth = angl
        p.pheight = mid1
        p.pdepth = mid2

        return generate(p)
    else:
        return


def scheme_selector(sno, cols, default):
    sc = Scheme[sno]
    cpat = [[cols[0][0], Cdis, Cdis],
            [cols[0][0], cols[1][0], Cdis],
            [cols[0][0], cols[1][0], cols[2][0]]]
    if 0< sc[2] < 4:
        cpat = cpat[sc[2]-1]
    else:
        cpat = [Cdis,Cdis,Cdis]
    
    line = [sg.Radio('', group_id='-scheme-', key=f'-sc_{sc[0]}-',
                     default=default),  #enable_events=True
            sg.Text(f'{sc[1]}', size=(14,1), key=f'-sct_s{sno}-',
                    background_color=Csel if default else Nsel),
            sg.Button('', key=f'-c1_s{sno}-', width=10,
                      background_color=cpat[0], disabled=True),
            sg.Button('', key=f'-c3_s{sno}-', width=10,
                      background_color=cpat[2], disabled=True),
            sg.Button('', key=f'-c2_s{sno}-', width=10,
                      background_color=cpat[1], disabled=True),
            sg.Text('○' if sc[3] else '×', key=f'-angl_s{sno}-', width=4),
            sg.Text(sc[4], key=f'-midl_s{sno}-', width=10),
            sg.Text(sc[5], key=f'-mid2_s{sno}-', width=10),
            ]
    return line

    
def scheme_index(name):
    for i, sc in enumerate(Scheme):
        if sc[0] == name:
            return i
    return Default_scheme


def palfile_list(directory=DATA_DIR, zfile=ZIP_FILE):
    patn = directory+pa.sep+'*.pal'
    files = [fn.replace('.pal','') \
             for fn in fdi.glob_filelistz(patn, add_zip=zfile)]
    return files


def update_pal_items(directory=DATA_DIR, zfile=ZIP_FILE):
    flist = palfile_list(directory, zfile)
    set_hist('found_pal', flist)

    pal_items = list(Palette_set.keys())
    pal_items.extend(flist)
    pal_items = list(dict.fromkeys(pal_items))
    pal_items.sort()

    pal_items.append(INTERNAL)
    return pal_items


def get_pal(palette_name):
    pset = get_hist('palette_set')
    #print(palette_name, '\n', pset)
    if palette_name in pset:
        pal = pset[palette_name]
    elif palette_name in get_hist('found_pal'):
        pal = load_pal(palette_name)
        if pal is not None:
            gradation_preserv['palette_set'][palette_name] = pal
    else:
        pal = None

    return pal
    

def load_pal(file):
    file = fdi.sanitize_filename(file, ext='.pal')
    file = DATA_DIR + pa.sep + file
    source = fdi.read_filez(file, add_zip=ZIP_FILE)

    return fdi.decode_palette(source, 3)
    

# 三色リニアグラデーション
def tricolor(W, H, color1, color2, color3, mid, angle):
    """
    3色を指定した比率で経由するグラデーションを生成する。
    :param mid: color3が配置される位置(%)
    """
    angle_rad = np.deg2rad(angle)
    y, x = np.ogrid[:H, :W]
    
    # 投影距離の計算
    projection = x * np.cos(angle_rad) + y * np.sin(angle_rad)
    
    # 0.0 ～ 1.0 に正規化
    p_min, p_max = projection.min(), projection.max()
    norm_projection = (projection - p_min) / (p_max - p_min)
    
    result = np.zeros((H, W, 3), dtype=np.uint8)
    
    # 補間ポイントの定義 xp: 投影比率 [0.0, midポイント, 1.0]
    xp = [0.0, mid / 100.0, 1.0]
    
    for i in range(3):
        # 各色の成分を取り出し、補間に使う
        fp = [color1[i], color3[i], color2[i]]
        result[..., i] = np.interp(norm_projection, xp, fp)
        
    return Image.fromarray(result, 'RGB')


def radial(W, H, color1, color2, mid1=None, mid2=None, angle=90):
    if mid1 is None:
        cx = W / 2
    else:
        cx = W * mid1/100
    if mid2 is None:
        cy = H / 2
    else:
        cy = H * mid2/100

    angle_rad = np.deg2rad(angle-90)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    y, x = np.ogrid[:H, :W]

    dx = x - cx
    dy = y - cy

    rx = (dx*cos_a + dy*sin_a) / (W / 2)
    ry = (-dx*sin_a + dy*cos_a) / (H / 2)

    d = np.clip(np.sqrt(rx * rx + ry * ry), 0.0, 1.0)

    c1 = np.asarray(color1)
    c2 = np.asarray(color2)

    result = c2 + (c1 - c2) * d[..., None]

    return Image.fromarray(np.round(result).astype(np.uint8), 'RGB')


def shaped(W, H, color1, color2, mid1=None, mid2=None):
    if mid1 is None:
        cx = W / 2
    else:
        cx = W * mid1/100
    if mid2 is None:
        cy = H / 2
    else:
        cy = H * mid2/100

    y, x = np.ogrid[:H, :W]

    dx = np.abs(x - cx)
    dy = np.abs(y - cy)

    rx = max(1, max(cx, W - 1 - cx))
    ry = max(1, max(cy, H - 1 - cy))

    # Lp距離
    p = 6
    d = ((dx / rx) ** p + (dy / ry) ** p) ** (1 / p)

    # 外周を1にする
    edge = 2 ** (1 / p)  # = ((rx/rx)**p + (ry/ry)**p) ** (1/p) 
    d /= edge
    
    d = np.clip(d, 0.0, 1.0)

    c1 = np.asarray(color1, dtype=float)
    c2 = np.asarray(color2, dtype=float)

    result = c2 + (c1 - c2) * d[..., None]

    return Image.fromarray(np.round(result).astype(np.uint8), 'RGB')


# 形状5 グラデーションに幅d・間隔dの格子状スリットを入れる
def slit(image, d=1, angle=0.0):
    arr = np.array(image.convert("RGBA"))
    h, w = arr.shape[:2]
    ys, xs = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")

    # (x, y) → (u, v) に逆回転
    a = np.deg2rad(angle)
    ca, sa = np.cos(a), np.sin(a)

    cx, cy = w / 2, h / 2
    x = xs - cx
    y = ys - cy

    u =  ca * x + sa * y
    v = -sa * x + ca * y

    # 格子判定（周期 2d）した位置のalphaを0に
    mask = ((u % (2*d)) < d) | ((v % (2*d)) < d)
    arr[mask, 3] = 0

    return Image.fromarray(arr, mode="RGBA")


# wallpaper 共通エントリ
def generate(p: Param):
    """指定した角度で2～3色のグラデーション画像を生成する。"""

    width, height = p.width, p.height
    color1 = p.color1.ctoi()
    color2 = p.color2.ctoi()
    color3 = p.color3.ctoi()
    angle = p.pwidth  # degree(整数)を指定
    mid1 = min(max(p.pheight, 0), 100)  # 中間色位置(相対位置を%で指定)
    mid2 = min(max(p.pdepth, 0), 100)  # 中間色位置(相対位置を%で指定)

    scheme = gradation_preserv['scheme']
    if scheme < 0 or len(Scheme) <= scheme:
        scheme = Default_scheme
    
    if scheme == 1:
        # 2色グラデは、color1,color2とcolor1,2の平均値の3色グラデで代替
        c3 = list(clip8((color1[i]+color2[i])/2) for i in range(3))
        return tricolor(width, height, color1, color2, c3, mid1, angle)
    elif scheme == 2:
        return tricolor(width, height, color1, color2, color3, mid1, angle)
    elif scheme == 3:
        return radial(width, height, color1, color2, mid1, mid2,  angle)
    elif scheme == 4:
        return shaped(width, height, color1, color2, mid1, mid2)
    elif scheme == 5:
        c3 = list(clip8((color1[i]+color2[i])/2) for i in range(3))
        im = tricolor(width, height, color1, color2, c3, mid1, angle)
        if mid2 < 1:  # 間隔1以下の場合はNG
            return im

        # 2色グラデに格子状にalpha=0で線を引く
        im = slit(im, mid2, angle)
        
        # 隙間が出来たimageをcolor3/BGに合成
        base = p.bg()
        if base is None:
            base = Image.new('RGBA', (width, height), color3)
        base.paste(im, (0,0), im)
        
        return base
    else:
        return Image.new('RGB', (width, height), color1)


if __name__ == '__main__':
    p = Param()
    p.width = 1920
    p.height = 1080
    p = default_param(p)
    img = generate(p)
    img.show()
