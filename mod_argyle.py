import numpy as np
from PIL import Image
import TkEasyGUI as sg
from wall_common import *

WIDTH = 1920
HEIGHT = 1080

COLOR1 = (120,30,40)
COLOR2 = (30,50,120)
BGCOLOR = (135,135,224)
COLOR_JITTER=3
PITCH = 160
ASPECT = int((10/7)*100)
DASH_PERIOD = 7

TEX_JITTER = 3
TEX_BLOCK = 2
CELL_JITTER = 4

argyle_preserv = {'stitch_color': [(248, 248, 197, 255),   # Aセル用ステッチ
                                   (248, 248, 197, 255),   # Bセル用ステッチ
                                   (248, 248, 197, 255)],  # Cセル用ステッチ
                  'stitch_ratio': 80,  # stitch_width = pitch//stitch_ratio
                  }

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'アーガイル',
                       {'color1':'色1', 'color2':'色2',
                        'color3':'共通(背景)色',
                        'color_jitter':'ゆらぎ',
                        'pwidth':'基本幅',
                        'pheight':'縦横比(%)',
                        'pdepth':'ステッチ周期(%)'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1 = RGBColor(COLOR1)
    p.color2 = RGBColor(COLOR2)
    p.color3 = RGBColor(BGCOLOR)
    p.color_jitter = COLOR_JITTER
    p.pwidth = PITCH
    p.pheight = ASPECT
    p.pdepth = DASH_PERIOD
    return p

def basic_color_line(n, color: RGBColor, caption):
    fg,bg = bg_and_font(color)
    r,g,b = color.ctoi()
    text = f'{r},{g},{b}'
    line = [sg.Text(f'{caption}', size=(12,1)),
            sg.Text(text, key=f'-base_{n}_1', size=(9,1),
                    text_color=fg, background_color=bg),
            sg.Button('...', key=f'-base_{n}_2')]
    return line

def stitch_color_line(n, color: tuple, caption):
    r,g,b,a = color
    fg,bg = bg_and_font(RGBColor(r,g,b))
    text = f'{r},{g},{b}'
    alpha = f'{a}'
    line = [sg.Text(f'{caption}', size=(6,1)),
            sg.Text(text, key=f'-stitch_{n}_1', size=(9,1),
                    text_color=fg, background_color=bg),
            sg.Button('...', key=f'-stitch_{n}_2'),
            sg.Text('Alpha:', size=(5,1)),
            sg.Input(alpha, key=f'-stitch_{n}_3', size=(4,1)),
            ]
    return line
    

def desc(p):
    base_colors = [p.color1, p.color2, p.color3]
    stitch_colors = [[argyle_preserv['stitch_color'][_][__]
                      for __ in range(4)]
                     for _ in range(3)]
    params = [p.pwidth, p.pheight, p.pdepth]
    
    base_colors_section = [[sg.Text('Diamond', font=('',14,'bold'))],
                           basic_color_line(1, base_colors[0], 'Color1:'),
                           basic_color_line(2, base_colors[1], 'Color22:'),
                           basic_color_line(3, base_colors[2], 'BackGround:'),
                           ]
    stitch_colors_section = [[sg.Text('Stitch', font=('',14,'bold')),
                              sg.Text('', expand_x=True),
                              sg.Button('Fit all to 1st', key='-fit-',
                                        background_color='#ffffdd')],
                             stitch_color_line(1, stitch_colors[0], 'Cell 1:'),
                             stitch_color_line(2, stitch_colors[1], 'Cell 2:'),
                             stitch_color_line(3, stitch_colors[2], 'BG Cell:'),
                             ]
    basic_section = [[sg.Text('Pitch', size=(12,1)),
                      sg.Input(f'{params[0]}', key='-bas1-', size=(4,1))],
                     [sg.Text('Aspect', size=(12,1)),
                      sg.Input(f'{params[1]}', key='-bas2-', size=(4,1))],
                     [sg.Text('Stitch Period', size=(12,1)),
                      sg.Input(f'{params[2]}', key='-bas3-', size=(4,1))],
                     ]
    button_section = [[sg.Text(''),],
                      [sg.Text(''),],
                      [sg.Text('',expand_x=True),
                       sg.Button('OK', key='-ok-',
                                 background_color='#ddffdd'),
                       sg.Button('Cancel', key='-can-',
                                 background_color='#ffdddd'),]
                      ]
    lo = [[sg.Column(base_colors_section, pad=(20,0)),
           sg.Column(stitch_colors_section,pad=(20,0))],
          [sg.Column(basic_section, pad=(20,0)),
           sg.Column(button_section, pad=(20,0), expand_x=True)],
          ]
    
    wn = sg.Window('アーガイル設定', layout=lo)

    while True:
        ev, va = wn.read()
        #print(ev, va)

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            break
        elif ev == '-ok-':
            break
        elif ev.startswith('-base_'):
            n = int(ev.split('_')[1])-1
            s = rgb_string(base_colors[n])
            colr = sg.popup_color(default_color=s)
            if colr is not None and colr != s:
                fg,bg = bg_and_font(colr)
                r,g,b = to_rgb(colr)
                wn[f'-base_{n+1}_1'].update(f'{r},{g},{b}',text_color=fg,
                                            background=bg)
                base_colors[n] = RGBColor(colr)
        elif ev.startswith('-stitch_'):
            n = int(ev.split('_')[1])-1
            s = rgb_string(stitch_colors[n][:3])
            a = stitch_colors[n][3]
            colr = sg.popup_color(default_color=s)
            if colr is not None and colr != s:
                fg,bg = bg_and_font(colr)
                r,g,b = to_rgb(colr)
                wn[f'-stitch_{n+1}_1'].update(f'{r},{g},{b}',
                                              text_color=fg, background=bg)
                stitch_colors[n] = (r,g,b,a)
        elif ev == '-fit-':
            ss = wn['-stitch_1_1'].get().split(',')
            r,g,b = [int(ss[_]) for _ in range(3)]
            s = f'#{r:02X}{g:02X}{b:02X}'
            txt = f'{r},{g},{b}'
            fg,bg = bg_and_font(s)
            for i in range(2):
                wn[f'-stitch_{i+2}_1'].update(txt, text_color=fg, background=bg)
                try:
                    a = int(va[f'-stitch_{i+2}_3'])
                except ValueError:
                    a = 255
                stitch_colors[i+1] = (r,g,b,a)

    wn.close()
    if ev == '-can-' or ev == sg.WINDOW_CLOSED:
        return

    p.color1, p.color2, p.color3 = base_colors

    for i in range(3):
        try:
            alp = int(va[f'-stitch_{i+1}_3'])
        except ValueError:
            alp = 255
        if alp != stitch_colors[i][3]:
            stitch_colors[i] = (*stitch_colors[i][:3], alp)
    argyle_preserv['stitch_color'] = [[stitch_colors[_][__]
                                       for __ in range(4)] for _ in range(3)]
    
    params = []
    for i in range(3):
        try:
            params.append(int(va[f'-bas{i+1}-']))
        except ValueError:
            params.append(0)
    p.pwidth, p.pheight, p.pdepth = params
    
    return generate(p)
    

def alpha_blend(dst_rgb, src_rgba, mask):
    """
    dst_rgb : (H,W,3) uint8
    src_rgba: (H,W,4) uint8
    mask    : (H,W) bool
    """

    dst = dst_rgb.astype(np.float32)

    src = src_rgba[..., :3].astype(np.float32)
    alpha = src_rgba[..., 3].astype(np.float32) / 255.0

    a = alpha[mask][:, None]

    dst[mask] = (
        dst[mask] * (1.0 - a)
        + src[mask] * a
    )

    return np.clip(dst, 0, 255).astype(np.uint8)


def argyle(p: Param):
    
    W = p.width
    H = p.height
    pitch = p.pwidth
    aspect = p.pheight / 100
    dash_period = p.pdepth / 100
    jitter = p.color_jitter
    A = rgb_random_jitter(p.color1, jitter).ctoi()
    B = rgb_random_jitter(p.color2, jitter).ctoi()
    D = argyle_preserv['stitch_color'][0]
    E = argyle_preserv['stitch_color'][1]
    F = argyle_preserv['stitch_color'][2]
    stitch_ratio = 1.0 / argyle_preserv['stitch_ratio']

    yy, xx = np.mgrid[:H, :W]

    # ---------------------------------------
    # 回転格子座標
    # ---------------------------------------

    u = xx/pitch + yy/(pitch*aspect)
    v = xx/pitch - yy/(pitch*aspect)

    iu = np.floor(u).astype(np.int32)
    iv = np.floor(v).astype(np.int32)

    pattern = np.array([
        [0, 2],   # A C
        [2, 1],   # C B
    ], dtype=np.uint8)

    idx = pattern[iu & 1, iv & 1]

    # ---------------------------------------
    # A/B描画、Cは透明
    # ---------------------------------------

    rgba_palette = np.array([
        (*A, 255),       # A
        (*B, 255),       # B
        (0, 0, 0, 0),    # C: 透明
    ], dtype=np.uint8)

    rgba = rgba_palette[idx]

    rgb = rgba[..., :3].copy()

    # ---------------------------------------
    # ステッチ
    # ---------------------------------------

    stitch_w = max(2, int(pitch * stitch_ratio))
    w = stitch_w / pitch

    fu = u % 1.0
    fv = v % 1.0

    line1 = np.abs(fu - 0.5) < w
    line2 = np.abs(fv - 0.5) < w

    #dash_period = 0.25
    dash_ratio = 0.5

    # 必要なら位相調整
    phase_shift = dash_period / 2

    phase1 = ((v + phase_shift) / dash_period) % 1.0
    phase2 = ((u + phase_shift) / dash_period) % 1.0

    dash1 = phase1 < dash_ratio
    dash2 = phase2 < dash_ratio

    stitch = (line1 & dash1) | (line2 & dash2)

    # ---------------------------------------
    # ステッチ色
    # ---------------------------------------

    stitch_palette = np.array([
        D,   # Aセル
        E,   # Bセル
        F,   # Cセル
    ], dtype=np.uint8)

    stitch_rgba = stitch_palette[idx]
    alpha = rgba[..., 3]

    alpha[stitch] = np.maximum(
        alpha[stitch],
        stitch_rgba[...,3][stitch]
    )

    stitch_rgba[...,3] = alpha
    rgb = alpha_blend(rgb, stitch_rgba, stitch)

    # テクスチャ
    rgb = rgb.astype(np.int16)

    # セル単位ノイズ
    seed = (iu * 73856093) ^ (iv * 19349663)
    cell_noise = (seed % (CELL_JITTER*2+1)) - CELL_JITTER
    rgb += cell_noise[..., None]

    # 2x2布地ノイズ
    bx = xx // TEX_BLOCK
    by = yy // TEX_BLOCK

    seed2 = (bx * 83492791) ^ (by * 29765729)
    tex = (seed2 % (TEX_JITTER*2+1)) - TEX_JITTER

    rgb += tex[..., None]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    # 元のアルファを保持
    rgba[..., :3] = rgb

    return Image.fromarray(rgba, 'RGBA')


def generate(p):
    W, H = p.width, p.height
   
    if p.h_img is not None:
        bg = p.bg().convert('RGBA')
    else:
        bgcolor = rgb_random_jitter(p.color3, p.color_jitter)
        bg = Image.new('RGBA',(W,H),bgcolor.ctoi())
        np_bg = np.array(bg, dtype=np.int16)

        # 2x2布地ノイズ
        yy, xx = np.mgrid[:H, :W]
        bx = xx // 2
        by = yy // 2

        seed2 = (bx * 83492791) ^ (by * 29765729)
        tex = (seed2 % 5) - 2

        np_bg += tex[..., None].astype(np.int16)

        np_bg = np.clip(np_bg, 0, 255).astype(np.uint8)
        bg = Image.fromarray(np_bg, 'RGBA')
   
    fg = argyle(p)
    bg.paste(fg,(0,0),fg)

    return bg
    
    
# ==========
# TEST
# ==========
if __name__ == '__main__':
    p = Param()
    p = default_param(p)

    p.width = WIDTH
    p.height = HEIGHT

    img = generate(p)
    img.show()
