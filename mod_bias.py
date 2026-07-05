import numpy as np
from PIL import Image
import TkEasyGUI as sg
from wall_common import *
import filedialog as fdi
import os.path as pa
import re

# ===== 定数 =====
COLOR1 = (188, 220, 227)
COLOR2 = (191, 224, 208)
COLOR3 = (194, 163, 200)
C_JITTER = 20      # 色ゆらぎ
S_JITTER = 100     # 彩度

BAND_WIDTH = 60    # 帯の幅（px）
ANGLE_DEG = 60     # 0～180（度）
MAX_BAND_NUM = 10  # 最大バンド数
# ================
M_ADD = 1
M_MUL = 2
M_RAD = 3
M_SINGLE = 0

bias_preserv = {'colors':[],
                'bandnum': 3,
                'method': M_SINGLE,
                }

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'バイアス(斜め線)＋交差編み',
                       {'color1':'線色1', 'color2':'線色2',
                        'color3':'線色3',
                        'color_jitter':'色差分', 'sub_jitter':'彩度変更(%)',
                        'pwidth':'線幅', 'pheight':'勾配(0-180)'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color3.itoc(*COLOR3)
    p.color_jitter = C_JITTER
    p.sub_jitter = S_JITTER
    p.pwidth = BAND_WIDTH
    p.pheight = ANGLE_DEG
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


def get_colors(p):
    o_colors = bias_preserv['colors']
    if len(o_colors) < MAX_BAND_NUM:
        o_colors = ([None]*MAX_BAND_NUM)[:MAX_BAND_NUM]
        for i in range(3):
            o_colors[i] = getattr(p, f'color{i+1}').ctoi()
        for i in range(3, MAX_BAND_NUM):
            o_colors[i] = o_colors[i%3]
        bias_preserv['colors'] = o_colors.copy()
        
    k = 255 // MAX_BAND_NUM
    for i in range(MAX_BAND_NUM):
        if o_colors[i] is None or not isinstance(o_colors[i], tuple):
            o_colors[i] = o_colors[i%3] if i > 2 else (i*k,i*k,i*k)
                     
    return o_colors


def color_selector(n, color):
    fg,bg = bg_and_font(color)
    r,g,b = to_rgb(color)
    ctext = f'{r},{g},{b}'
    line = [sg.Text(f'Color {n}', text_align='right', size=(7,1)),
            sg.Text(ctext, key=f'-color_{n}', size=(9,1),
                    text_color=fg, background_color=bg),
            sg.Button('...', key=f'-cpick_{n}')]
    return line


def color_update(n, color, wn):
    fg,bg = bg_and_font(color)
    r,g,b = to_rgb(color)
    ctext = f'{r},{g},{b}'
    wn[f'-color_{n}'].update(ctext, text_color=fg, background_color=bg)
    
    return


def showpal(colors, Caption='Debug'):
    print(f'{Caption}: num={len(colors)}\nColors>  {colors}\n',
          f'Preserv> {bias_preserv["colors"]}\n') 


def desc(p):
    itemdic = {'Normal': M_SINGLE,
               'Cross': M_ADD,
               'Block': M_MUL,
               'Radius': M_RAD,
               }
    fname = 'default.pal'
    cjit = p.color_jitter
    sjit = p.sub_jitter
    colors = get_colors(p)

    bandwidth = p.pwidth
    angle = p.pheight % 360
    bandnum = bias_preserv['bandnum']
    method = bias_preserv['method']
    orgmethod = next(k for k, v in itemdic.items() if v == method)

    col1 = []
    col2 = []
    lno = MAX_BAND_NUM // 2
    for i in range(lno):
        col1.append(color_selector(i, colors[i]))
        if i < MAX_BAND_NUM:
            col2.append(color_selector(i+lno, colors[i+lno]))

    col0 = [[sg.Column(col1, vertical_alignment='top'),
             sg.Column(col2, vertical_alignment='top'),]]

    col3 = [[sg.Text('Draw method'),
             sg.Combo(list(itemdic.keys()), default_value=orgmethod,
                      size=(10,1), key='-method-', readonly=True),],
            [sg.Text('Band width'),
             sg.Input(f'{bandwidth}',size=(4,1), key='-pwidth-'),
             sg.Text(expand_x=True),
             sg.Text('Angle'),
             sg.Input(f'{angle}',size=(4,1), key='-angle-')],
            [sg.Text('Jitter'),
             sg.Input(f'{cjit}',size=(4,1), key='-cjit-'),
             sg.Text(expand_x=True),
             sg.Text('Satul.'),
             sg.Input(f'{sjit}',size=(4,1), key='-sjit-')],
            [sg.Text('Num of Bands'),
             sg.Input(f'{bandnum}',size=(4,1), key='-bandnum-'),
             sg.Text(f'(max {MAX_BAND_NUM})', text_color='#444466'),],
            ]

    buttons = [sg.Text('Color set'),
               sg.Button('Load', key='-ld-', background_color='#ffffdd'),
               sg.Button('Save', key='-sv-', background_color='#ffffdd'),
               sg.Text(size=(20,1), key='-fname-'),
               sg.Text(expand_x=True),
               sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
               sg.Button('Done', key='-ok-', background_color='#ddffdd'),
               ]

    lo = [[sg.Column(col1, vertical_alignment='top'),
           sg.Column(col2, vertical_alignment='top'),
           sg.Text(size=(1,1)),
           sg.Column(col3, vertical_alignment='top', expand_y=True),
           ],
          buttons,
          ]

    wn = sg.Window('BIAS config', layout=lo)
    
    while True:
        ev,va = wn.read()

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            break
        elif ev.startswith('-cpick_'):
            n = int(ev.split('_')[1])
            s = rgb_string(colors[n])
            colr = sg.popup_color(default_color=s)
            if colr is not None and colr != s:
                fg,bg = bg_and_font(colr)
                r,g,b = to_rgb(colr)
                wn[f'-color_{n}'].update(f'{r},{g},{b}',text_color=fg,
                                            background=bg)
                colors[n] = to_rgb(colr)
            fdi.flush_ev(wn)
        elif ev == '-ld-':
            n_colors = load_palette(fname)
            # showpal(n_colors, 'load')
            if n_colors is None:
                continue
            for i in range(MAX_BAND_NUM):
                 color_update(i, n_colors[i], wn)
            colors = n_colors
            fdi.flush_ev(wn)
        elif ev == '-sv-':
            fname = save_palette(colors)
            if fname is not None:
                wn['-fname-'].update(pa.basename(fname))
            fdi.flush_ev(wn)
        elif ev == '-ok-':
            break

    wn.close()
    if ev == '-ok-':
        p.color_jitter = safeint(va['-cjit-'], default=cjit, lo=0)
        p.sub_jitter = safeint(va['-sjit-'], default=sjit, lo=-100, hi=400)
        p.pwidth = safeint(va['-pwidth-'], default=bandwidth,
                           lo=1, hi=min(p.width, p.height))
        p.pheight = safeint(va['-angle-'], default=angle) % 360
        bias_preserv['bandnum'] = safeint(va['-bandnum-'], default=bandnum,
                                          lo=2, hi=MAX_BAND_NUM) 
        if va['-method-'] in itemdic:
            method = itemdic[va['-method-']]
        bias_preserv['method'] = method

        for i in range(3):
            setattr(p, f'color{i+1}', RGBColor(colors[i]))
        bias_preserv['colors'] = colors.copy()
        # showpal(colors, 'load')

        return generate(p)       

    return


def color_jitter(colors, cjit, sjit):
    newc = []
    for i in range(MAX_BAND_NUM):
        newc.append(to_rgb(brightness(
            rgb_random_jitter(RGBColor(colors[i]), cjit), s=sjit)))
                     
    return newc
    

def save_palette(colors):
    fname = fdi.get_savefile('default.pal', filetypes=[('palette', '*.pal')],
                             init_dir='samples')
    if fname is None:
        return None
    try:
        with open(fname, mode='w', encoding='sjis') as f:
            f.write('[Colors]\n')
            for i, (r,g,b) in enumerate(colors):
                f.write(f'Color{i}=({r},{g},{b})\n')
        return fname
    except Excewption as e:
        print('Error:', e)
        return None


def load_palette(fname='default.pal'):
    filetypes = [('palette', '*.pal'),
                 ('tartan set', '*.ttn')]
    fname = fdi.get_openfile(fname, filetypes=filetypes,
                             init_dir='samples')
    if fname is None:
        return None
    with open(fname, mode='r', encoding='sjis') as f:
        buf = f.read().splitlines()

    p = 0
    while True:
        if buf[p].startswith('[Colors]'):
            break
        p += 1
        if p == len(buf):
            return None
    p += 1
    colors = ([None]*MAX_BAND_NUM)
    c = 0
    while True:
        m = re.match(r'Color(\d+)=\(\s*(\d+),\s*(\d+),\s*(\d+)\)', buf[p])
        if m:
            cno = int(m.group(1))
            r = int(m.group(2))
            g = int(m.group(3))
            b = int(m.group(4))
            if 0<= cno < MAX_BAND_NUM:
                colors[cno] = (r,g,b)
                c += 1
                if c == MAX_BAND_NUM:
                    break
            else:
                print(f'no match: {p[buf]}')
                
        p += 1
        if p == len(buf):
            break

    k = 255 // MAX_BAND_NUM
    for i in range(MAX_BAND_NUM):
        if colors[i] is None or not isinstance(colors[i], tuple):
            colors[i] = colors[i%3] if i > 2 else (i*k,i*k,i*k)

    return colors


# バイアス生成
def generate(p: Param):
    w = p.width
    h = p.height
    cjit = p.color_jitter
    sjit = min(max(p.sub_jitter, -100),400) / 100
    colors = get_colors(p)
    # showpal(colors, 'Generate')
    
    colors = color_jitter(colors, cjit, sjit)

    bandwidth = min(max(p.pwidth,1),max(w,h))
    angle = p.pheight % 360
    bandnum = bias_preserv['bandnum']
    method = bias_preserv['method']
    bias_preserv['bandwidth'] = bandwidth
    bias_preserv['angle'] = angle
    
    # 座標グリッド
    y, x = np.mgrid[0:h, 0:w]

    # 角度（ラジアン）
    theta = np.deg2rad(angle)
    iota = np.deg2rad(angle+90)

    # 帯に垂直な方向への射影
    s = x * np.cos(theta) + y * np.sin(theta)
    t = x * np.cos(iota) + y * np.sin(iota)

    # print(bandnum, colors)
    # 色インデックス生成
    ss = s // bandwidth
    if method == M_ADD:
        idx = ((ss + t // bandwidth) % bandnum).astype(np.int32)
    elif method == M_MUL:
        idx = ((ss * (t // bandwidth)) % bandnum).astype(np.int32)
    elif method == M_RAD:
        idx = ((ss**2 + (t // bandwidth)**2) % bandnum).astype(np.int32)
    else:  # M_SINGLE == 直交成分なし
        idx = (ss % bandnum).astype(np.int32)
    
    # 色テーブルを NumPy 配列に
    color_table = np.array(colors, dtype=np.uint8)
    # showpal(colors, 'set array')

    # インデックスで一発変換（H×W×3）
    img_np = color_table[idx]
    img = Image.fromarray(img_np, "RGB")

    return img


# テスト
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    img = generate(p)
    
    img.show("stripe.png")

