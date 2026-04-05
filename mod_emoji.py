import re
import math
from PIL import Image, ImageDraw, ImageFont
import TkEasyGUI as sg
from wall_common import *

# ----
# 絵文字設定画面定数
# ----
PAGE_FONT = 28
PAGE_SIZE = (640, 480)

# 絵文字初期設定 (不揮発変数)
emoji_preserv = {
    'chars': ['\U0001F62E',  # びっくり
              '\U0001F3D5',  # テント
              '\U0001F638',  # 犬
              None],
    'winding': 0.2,  # 巻きの強さ(char_numを増やした方が目立つが)
    'sp_lines': 24,  # 腕の数
    'sp_dense': 1.4,  # 腕に含まれる文字数の倍率 （×pwidth文字）
    'base_size': 12,  # 渦最小文字サイズ / 敷石サイズ係数(base/12)
    'large_size': 96,  # 渦最大文字サイズ
    'font': 'c:\\Windows\\Fonts\\seguiemj.ttf',
    'font-from': 0x1f000,  # 絵文字範囲先頭
    'font-to': 0x1f700,  # 絵文字範囲末尾
    'font-start': 0x1f300  # 最初に表示するページ
    }

# ----
# 壁紙用定数
# ----
BASE_COLOR = (30,120,30)
END_COLOR = 40
SATULATION = 80
CHAR_NUM = 12
FORM = 0

# 補助定数
X_PITCH = 2.2
Y_PITCH = 1.8

def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '絵文字 4文字時検討中',
                       {'color1':'基本色',
                        'color_jitter':'背景色幅',
                        'sub_jitter':'彩度(%)',
                        'pwidth':'文字数(横)',
                        'pheight':'形状(0/1)'})
    return module_name
    

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE_COLOR)
    p.color_jitter = END_COLOR
    p.sub_jitter = SATULATION
    p.pwidth = CHAR_NUM
    p.pheight = FORM
    return p


# 追加設定ダイアログ
def desc(p: Param):
    pix = [None]*4
    drw = [None]*4
    pixsiz = 40
    pixfont = 30
    cpbox = PAGE_FONT * 1.2  # chrmap()の文字ボックスサイズ

    codes = [0]*4
    for i in range(4):
        pix[i] = Image.new('RGB', (pixsiz,pixsiz),
                           '#404040')  # view 36pts
        drw[i] = ImageDraw.Draw(pix[i])
        if emoji_preserv['chars'][i] is None:
            codes[i] = None
        else:
            codes[i] = ord(emoji_preserv['chars'][i])

    font_name = emoji_preserv['font']
    font_area = [emoji_preserv['font-from'],
                 emoji_preserv['font-to'],
                 emoji_preserv['font-start']]
        
    right = [[sg.Text(f'Font= {font_name}')],
             [sg.Text('', expand_y=True)],
             [sg.Image(data=pix[0], size=(pixsiz,pixsiz),
                       key='-ch0_img-', enable_events=True),
              sg.Text(codestr(codes[0]), key='-ch0_id-', expand_x=True)],
             [sg.Image(data=pix[1], size=(pixsiz,pixsiz),
                       key='-ch1_img-', enable_events=True),
              sg.Text(codestr(codes[1]), key='-ch1_id-', expand_x=True)],
             [sg.Image(data=pix[2], size=(pixsiz,pixsiz),
                       key='-ch2_img-', enable_events=True),
              sg.Text(codestr(codes[2]), key='-ch2_id-', expand_x=True)],
             [sg.Image(data=pix[3], size=(pixsiz,pixsiz),
                       key='-ch3_img-', enable_events=True),
              sg.Text(codestr(codes[3]), key='-ch3_id-', expand_x=True)],
             [sg.Text('')],
             [sg.Text('基本文字サイズ(12)'),
              sg.Input(str(emoji_preserv['base_size']), key='-base_size-',
                       size=(4,1), expand_x=True), sg.Text('×', size=(1,1)),
              sg.Text('外周サイズ(96)'),
              sg.Input(str(emoji_preserv['large_size']), key='-large_size-',
                       size=(4,1),expand_x=True), sg.Text('', size=(1,1))],
             [sg.Text('渦文字密度(1.4)'),
              sg.Input(str(emoji_preserv['sp_dense']), key='-sp_dense-',
                       size=(4,1),expand_x=True), sg.Text('', size=(1,1))],
             [sg.Text('巻き強度(0.2)'),
              sg.Input(str(emoji_preserv['winding']), key='-winding-',
                       size=(4,1), expand_x=True), sg.Text('', size=(1,1)),
              sg.Text('巻き数(24)'),
              sg.Input(str(emoji_preserv['sp_lines']), key='-sp_lines-',
                       size=(4,1), expand_x=True), sg.Text('', size=(1,1))],
             [sg.Button('\U000023EA', key='-prev-', background_color='#ffffdd'),
             sg.Text('', expand_x=True),
             sg.Text('', key='-page-'), sg.Text('', expand_x=True),
             sg.Button('\U000023E9', key='-next-', background_color='#ffffdd')],
             [sg.Text('')],
             [sg.Text('',expand_x=True),
              sg.Button('Clear', key='-clr-', background_color='#ddddff'),
              sg.Text('',size=(2,1)),
              sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
              sg.Button(' Done ', key='-ok-', background_color='#ddffdd')
              ]
             ]
    
    cp_img = Image.new('RGB', PAGE_SIZE, '#c8c8c8')
    left = [[sg.Image(data=cp_img, key='-sel-', enable_events=True,
                      size=PAGE_SIZE)],
            ]

    cp = font_area[2]
    font = get_font(font_name, PAGE_FONT)
    cols, rows = chrmap(cp_img, font, PAGE_FONT, cp, bg='#c8c8c8')

    wn = sg.Window('Select Emoji', layout=[[sg.Column(left), sg.Column(right)]],
                   grab_anywhere=True, padding_x=0, padding_y=0, modal=True)
    
    for i in range(4):
        if codes[i] is None:
            one_chr(pix[i], font, pixfont, 0x20)
        else:
            one_chr(pix[i], font, pixfont, codes[i])
        wn[f'-ch{i}_img-'].update(data=pix[i])
    wn['-page-'].update(f'U+{cp:X} -')

    cur = 0
    drw[cur].rectangle((0,0,pixsiz-3,pixsiz-3), fill=None,
                       outline='#ff0000', width=3)
    wn[f'-ch{cur}_img-'].update(data=pix[cur])

    while True:
        ev, va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            break

        elif ev == '-sel-' and va['event_type'] == 'mousedown':
            # 文字一覧クリック → codes[cur]を指定絵文字に
            x, y = get_pos(str(va['event']))
            # det = wn[ev].get_event_details()  # バグってた
            # x,y = det.x, det.y
            col = int(x/cpbox)
            row = int((y-8)/cpbox)
            if row >= rows:
                code = None
            else:
                code = cp + col + row*cols
            codes[cur] = code
            if code is None:
                one_chr(pix[cur], font, pixfont, 0x20)
            else:
                one_chr(pix[cur], font, pixfont, code)
            wn[f'-ch{cur}_img-'].update(data=pix[cur])
            cur = min(3, max(cur+1, 0))
            drw[cur].rectangle((0,0,pixsiz-3,pixsiz-3), fill=None,
                               outline='#ff0000', width=3)
            wn[f'-ch{cur}_img-'].update(data=pix[cur])
            
        elif ev == '-prev-':
            cp = cp - 0x100  if cp > font_area[0]  else font_area[0]
            cols, rows = chrmap(cp_img, font, PAGE_FONT, cp, bg='#c8c8c8')
            wn['-sel-'].update(data=cp_img)
            wn['-page-'].update(f'U+{cp:X} -')

        elif ev == '-next-':
            cp = cp + 0x100  if cp < font_area[1] else font_area[1]
            cols, rows = chrmap(cp_img, font, PAGE_FONT, cp, bg='#c8c8c8')
            wn['-sel-'].update(data=cp_img)
            wn['-page-'].update(f'U+{cp:X} -')
        
        elif ev in ('-ch0_img-','-ch1_img-','-ch2_img-','-ch3_img-') and \
             va['event_type'] == 'mousedown':
            # 利用絵文字枠クリック→設定対象変更
            if codes[cur] is None:
                one_chr(pix[cur], font, pixfont, 0x20)
            else:
                one_chr(pix[cur], font, pixfont, codes[cur])
            
            wn[f'-ch{cur}_img-'].update(data=pix[cur])
            cur = int(ev[3])

            if codes[cur] is None:
                one_chr(pix[cur], font, pixfont, 0x20)
            else:
                one_chr(pix[cur], font, pixfont, codes[cur])
            drw[cur].rectangle((0,0,pixsiz-3,pixsiz-3), fill=None,
                               outline='#ff0000', width=3)
            wn[f'-ch{cur}_img-'].update(data=pix[cur])
            
        elif ev == '-ok-':
            lst = list(filter(None, codes))
            if len(lst) > 0:
                emoji_preserv['chars'] = [None]*4
                for i in range(len(lst)):
                    emoji_preserv['chars'][i] = chr(lst[i])
                    # print(i, emoji_preserv['chars'])
                break
            
    for x in ('winding', 'base_size', 'large_size', 'sp_dense', 'sp_lines'):
        val = wn[f'-{x}-'].get_text()
        try:
            vv = float(val)
        except ValueError:
            vv = 0.0
        if x == 'sp_lines':
            vv = clip8(int(vv))
        emoji_preserv[x] = vv
        # print(f'{x}: {val} -> {vv}')
    
    wn.close()

    image = generate(p)
    return image


# ----
# サポート関数
# ----
def codestr(x):
    '''文字コードxをユニコード表現(U+HHHHH)に変換'''
    if x is None:
        return ''
    return f'U+{x:X}'


def one_chr(image: Image.Image, font: ImageFont.FreeTypeFont, size,
           code, bg='#c8c8c8'):
    '''一文字をimageに描画'''
    w = image.width
    h = image.height
    font.size = size
    draw = ImageDraw.Draw(image)
    sx,sy,ex,ey = draw.textbbox((0,0),chr(code), font=font, embedded_color=True)
    draw.rectangle((0,0,w-1,h-1), fill=bg)
    xoffs = min(w, max((w-(ex-sx))//2, 0))
    yoffs = min(h, max((h-(ey-sy))//2, 0))
    draw.text((xoffs, yoffs), chr(code),
              font=font, embedded_color=True)
    return


def chrmap(image: Image.Image, font: ImageFont.FreeTypeFont, size,
           code_base, bg='#c8c8c8'):
    '''imageに文字一覧を描画'''
    w = image.width
    h = image.height
    font.size = size
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,w-1,h-1), fill=bg)
    
    box_size = int(font.size*1.2)
    cols = int(w/box_size)
    rows = int(h/box_size)

    for y in range(rows):
        for x in range(cols):
            code = code_base+y*cols+x
            draw.text((x*box_size, y*box_size+8), chr(code),
                   font=font, embedded_color=True)
        # print(f'{code:08x} ', end='')

    return cols, rows


def get_font(font_path, size):
    '''フォント構造体を取得'''
    try:
        font = ImageFont.truetype(font_path, size,
                                  layout_engine=ImageFont.Layout.BASIC)
    except  OSError:
        print('No Font')
        quit()

    return font

# ----
# 画像生成
# ----
def spiral(draw, width, height, font_name, char_num):
    char_num = int(char_num * emoji_preserv['sp_dense'])
    
    cx, cy = width//2, height//2
    lines = int(emoji_preserv['sp_lines'])

    r_max = max(width, height) * 0.5
    r_min = 40
    k = math.pi * emoji_preserv['winding']
    maxf = int(emoji_preserv['large_size'])
    minf = int(emoji_preserv['base_size'])

    text = ''.join(filter(None,emoji_preserv['chars']))

    for i in range(lines):
        theta0 = 2 * math.pi * i / lines
        ptr = 0
        for j in range(char_num):
            t = j / (char_num-1)
            t2 = t ** 0.65
            r = r_max * (1 - t2) + r_min * t2
            theta = theta0 + k*math.log(r_max/r)
            
            size = int(maxf * (1.0 - math.sqrt(t)) + minf * math.sqrt(t))
            font =  get_font(font_name, size)

            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)

            draw.text((x, y), text[ptr], anchor="mm",
                      font=font, embedded_color=True)

            ptr=(ptr+1)%len(text)

    return


def pave(draw, width, height, font_name, char_num):
    x_pitch = X_PITCH
    y_pitch = Y_PITCH

    # 画像サイズと1段に描画する文字数からフォントサイズを決定
    space = int(width/(char_num*x_pitch))
    font_size = int(width/(char_num*x_pitch) * emoji_preserv['base_size']/12)
    font = get_font(font_name, font_size)

    # 設定個数に応じた表示絵文字配列を生成
    disp_chars = list(filter(None, emoji_preserv['chars']))
    if len(disp_chars) == 3:
        disp_chars.append(disp_chars[2])
        disp_chars[2] = disp_chars[1]
    elif len(disp_chars) == 2:
        disp_chars.extend([disp_chars[0], disp_chars[1]])
    elif len(disp_chars) == 1:
        disp_chars = [disp_chars[0]]*4

    # 絵文字を配置
    for y in range(int(height/(font_size*y_pitch))+2):
        offset = y%2*(x_pitch/2)*space #font_size
        for x in range(char_num+1):
            c = disp_chars[(x+y%4//2)%2 + (y%2)*2]

            # embedded_color=True がカラー表示のポイント
            draw.text((x*space*x_pitch+offset, y*font_size*y_pitch),
                      c, font=font, embedded_color=True)
    return


def generate(p: Param):
    width = p.width
    height = p.height
    base_color = p.color1
    jitter = p.color_jitter
    satulation = np.clip(p.sub_jitter, 0, 100)
    char_num = min(max(p.pwidth, 1), 50)
    form = p.pheight

    # 背景となるimageを生成
    # image = Image.new("RGB", (width, height), base_color)
    if p.h_img is None:
        image = vertical_gradient_rgb(width, height,
                                      base_color,
                                      rgb_random_jitter(base_color, jitter))
    else:
        image = p.bg()

    draw = ImageDraw.Draw(image)
    font_name = emoji_preserv['font']

    if form != 0:
        spiral(draw, width, height, font_name, char_num)
    else:
        pave(draw, width, height, font_name, char_num)

    return sat_attenate(image, satulation)


if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    p.pheight = 0

    img = generate(p)
    img.show()
