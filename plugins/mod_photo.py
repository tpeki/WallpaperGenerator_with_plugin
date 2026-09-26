from wall_common import *
from PIL import Image
import os.path as pa
import math
import TkEasyGUI as sg
import filedialog as fdi

# 外部定数
BGCOLOR = (64, 64, 64)
SCALE = 100
ANGLE = 0

photo_preserv = {'file_name': ''}

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       '画像読み込み ファイル指定は詳細画面で',
                       {'color1':'背景色',
                        'pwidth':'スケール', 'pheight':'角度'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    p.color1.itoc(*BGCOLOR)
    p.pwidth = SCALE
    p.pheight = ANGLE
    return p


def image_open(file, fallback=(800,600), bg='gray'):
    try:
        im = Image.open(file)
    except Image.UnidentifiedImageError:
        im = None

    if im is None and isinstance(fallback, tuple):
        im = Image.new('RGB', fallback, bg)

    return im


# 詳細設定
def desc(p):
    W,H = p.width, p.height
    oldc = get_hist('bgc', p.color1.ctoi())
    ang = get_hist('angle', p.pheight)
    scl = get_hist('scale', p.pwidth)
    fgc,bgc = bg_and_font(oldc)
    oldf = photo_preserv['file_name']
    if not pa.exists(oldf):
        oldf = ''

    lo = [[sg.Text('Load File'),
           sg.Input(pa.basename(oldf), width=30, key='-fname-',
                    readonly=True, readonly_background_color='#ffffdd'),
           sg.Button('...', key='-fget-', background_color='#ffffdd')
           ],
          [sg.Text('BGColor'),
           sg.Button(bgc[1:], key='-bgc-', text_color=fgc,
                     background_color=bgc),
           sg.Text(width=2),
           sg.Text('Angle'),
           sg.Input(ang, width=4, key='-angle-'),
           sg.Text(expand_x=True)
           ],
          [sg.Text('Scale'),
           sg.Input(scl, width=8, key='-scale-'),
           sg.Text(width=2),
           sg.Button('Full zoom', key='-full-'),
           sg.Button('Fit inner', key='-fit-'),
           ],
          [sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Done', key='-ok-', background_color='#ddffdd')
           ]
          ]
 
    wn = sg.Window('Photo config', layout=lo)
    while True:
        ev,va = wn.read()

        if ev in ('-can-', sg.WINDOW_CLOSED):
            ev = '-can-'
            break
        elif ev == '-bgc-':
            nc = sg.popup_color('Backdrop color', oldc, format='tuple')
            if nc != oldc:
                fgc, bgc = bg_and_font(nc)
                wn['-bgc-'].update(text=bgc[1:],
                                   text_color=fgc, background_color=bgc)
                oldc = to_rgb(nc)
            fdi.flush_ev(wn)
            
        elif ev == '-fget-':
            idir = pa.dirname(oldf)
            if idir == '':
                idir = '.'
            fname = fdi.get_openfile(pa.basename(oldf),
                                     filetypes=[('Any', '*.*'),],
                                     init_dir=idir)
            fdi.flush_ev(wn)
            if fname != '':
                im = image_open(fname, fallback=(W,H))
                    
                sw, sh = im.size
                ang = stoi(wn['-angle-'].get(), default=0) % 360
                oldf = fname
                wn['-fname-'].update(pa.basename(oldf))
                rw, rh = calc_scale_inscribed(W, H, sw, sh, ang)
                scl = max(rw, rh) *100.0
                wn['-scale-'].update(scl)
        
        elif ev == '-fit-':
            if pa.exists(oldf):
                im = image_open(oldf, fallback=(W,H))
                sw, sh = im.size
                ang = stoi(va['-angle-'], default=0) % 360
                rw, rh = calc_scale_inscribed(W, H, sw, sh, ang)
                scl = min(rw, rh) *100.0
                wn['-scale-'].update(scl)
        elif ev == '-full-':
            if pa.exists(oldf):
                im = image_open(oldf, fallback=(W,H))
                sw, sh = im.size
                ang = int(stoi(va['-angle-'], default=0) % 360)
                rw, rh = calc_scale_inscribed(W, H, sw, sh, ang)
                scl = max(rw, rh) *100.0
                wn['-scale-'].update(scl)
                
        elif ev == '-ok-':
            break

        wn.refresh()

    wn.close()
    
    if ev == '-ok-':
        scl = stoi(wn['-scale-'].get(), lo=1E-8)
        ang = stoi(wn['-angle-'].get())
        
        photo_preserv['file_name'] = oldf
        photo_preserv['scale'] = scl
        p.pwidth = scl
        photo_preserv['angle'] = ang
        p.pheight = ang
        photo_preserv['bgc'] = oldc
        p.color1 = RGBColor(oldc)

        return generate(p)
    else:
        return

# 標準拡大率の取得
def calc_scale_inscribed(W, H, w1, h1, d):
    """(W,H)に(w1,h1)の画像をd度回転して張り付ける際に余白を生じない拡大率
        貼り付け画像の内接矩形が(W,H)になるようにする"""
    rad = math.radians(d)
    sin = abs(math.sin(rad))
    cos = abs(math.cos(rad))

    Win = (w1 * h1) / (w1 * sin + h1 * cos)
    Hin = (w1 * h1) / (w1 * cos + h1 * sin)

    #r = max(W / Win, H / Hin)
    return W / Win, H / Hin


def get_hist(atname, default):
    if atname in photo_preserv:
        return photo_preserv[atname]
    else:
        photo_preserv[atname] = default
        return default
    
        
# wallpaper 共通エントリ
def generate(p: Param):
    """イメージファイル読み込み"""
    W, H = p.width, p.height

    bgcolor = p.color1.ctoi()
    scale = p.pwidth  #相対値, 100=余白無し・アスペクト維持で画像をload
    angle = p.pheight  # degree(整数)を指定

    file_name = photo_preserv['file_name']
    
    if not pa.exists(file_name):
        fixed_image = Image.new('RGBA', (W, H), bgcolor)
    else:
        img = image_open(file_name, fallback=(W,H),
                         bg=bgcolor).convert('RGBA')
        sx,sy = img.size
        sr = scale / 100

        # print('r=', sr, '->', int(sx*sr), int(sy*sr))
        sxr = max(1, int(sx*sr))
        syr = max(1, int(sy*sr))
        rimage = img.resize((sxr, syr), resample=Image.LANCZOS)
        rimage = rimage.rotate(angle, resample=Image.BICUBIC,
                               expand=True, fillcolor=bgcolor)
        pw, ph = rimage.size
        px, py = (W-pw)//2, (H-ph)//2

        fixed_image = p.bg()
        if fixed_image is None:
            fixed_image = Image.new('RGBA', (W,H), bgcolor)
        fixed_image.paste(rimage, (px, py), rimage)

    return fixed_image


if __name__ == '__main__':
    p = Param()
    p.width = 1920
    p.height = 1080
    p = default_param(p)
    img = generate(p)
    img.show()
