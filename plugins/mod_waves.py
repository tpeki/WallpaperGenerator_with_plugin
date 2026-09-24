from PIL import Image, ImageDraw
from wall_common import *
import random
import colorsys

DEBUG = False
# ================= 定数 =================
WIDTH  = 1920
HEIGHT = 1080

WAVE_COLOR = (30, 90, 160)  # 藍
BG_COLOR = (245, 245, 240)  # 生成り
WAVE_JITTER = 5
GRADATION = 30  # 波毎の明度変更量％
LINE_WIDTH = 80  # ペン幅比 (%)  0.8
RADIUS = 50  # 基準半径 r
WAVE_COUNTS = 5 # 波の数
OBLATENESS = 90  # 扁平率 (%)  0.9
# =======================================

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       '青海波',
                       {'color1':'波色', 'color2':'地色',
                        'color_jitter':'色ゆらぎ',
                        'sub_jitter':'波グラデ',
                        'sub_jitter2':'線密度(%)',
                        'pwidth':'波半径', 'pheight':'波数',
                        'pdepth':'波高(%)'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    p.color1.itoc(*WAVE_COLOR)
    p.color2.itoc(*BG_COLOR)
    p.color_jitter = WAVE_JITTER
    p.sub_jitter = GRADATION
    p.sub_jitter2 = LINE_WIDTH
    p.pwidth = RADIUS
    p.pheight = WAVE_COUNTS
    p.pdepth = OBLATENESS
    return p


def strtoc(s):
    if isinstance(s, tuple):
        return s
    elif isinstance(s, str):
        return int(s[1:2], 16),int(s[3:5], 16),int(s[5:7], 16)
    else:
        return 0,0,0


def draw_arc(draw, center, radius, counts, width=0, scale=100,
             color=(0,0,0), bg=BG_COLOR, grad=0):
    # counts += 1
    if width == 0:  # 幅自動
        width = radius//(counts*2)
    else:
        width = int(radius/(counts*2) * width/100)
    if width < 1:
        width = 1

    angl_s = 180+30
    angl_e = angl_s+120

    col = [color]*counts
    if grad != 0:
        for i in range(counts):
            amount = max(100+i*grad, 0)
            col[i] = brightness(RGBColor(col[0]), f=amount/100,
                                bg=bg).ctoi()
    # print(f'Colors: {col}')

    bbox = (center[0]-radius, center[1]-radius*2*(scale/100),
            center[0]+radius, center[1])
    draw.pieslice(bbox, start=180, end=0, fill=bg)

    for i in range(counts):
        r = radius*(1-(i/counts/2))
        bbox = (center[0]-r, center[1]-r*2*(scale/100),
                center[0]+r, center[1])
        draw.arc(bbox, start=angl_s, end=angl_e, fill=col[i], width=width)


def generate(p: Param):
    width = p.width
    height = p.height
    c1 = p.color1.ctoi()  # 波色
    c2 = p.color2.ctoi()  # 地色
    jitter = p.color_jitter  # 波色変化
    grad = p.sub_jitter  # グラデーション
    lwidth = min(max(p.sub_jitter2,1),100)  # 線幅(%)
    radius = min(max(p.pwidth,10),int(min(width,height)/2))  # 波半径
    wcounts = min(max(p.pheight,0),radius-1)  # 波重畳数
    obl = min(max(p.pdepth,1),100)  # 扁平率(%)

    # 描画開始
    img = Image.new("RGB", (width, height), c2)
    draw = ImageDraw.Draw(img)

    row_height = int(radius * (obl/100) / 2)  # 帯幅
    rows = height//row_height + 4  # 画面内の帯数
    cols = width//(2*radius) + 2  # 帯内の円弧数

    if DEBUG:
        print(f'row_height:{row_height}, rows:{rows}  columns:{cols}')
        print(f'radius:{radius}, wcounts:{wcounts}, width:{lwidth}, '\
              'scale:{obl}, color:{c1}, bg:{c2}, grad:{grad}')

    for row in range(rows):
        # print(f'row {row} / {rows-1}')
        # 行のY座標値
        y = (row+1)*row_height
        x_offset = 0 if row%2 == 0 else radius

        for col in range(cols):
            x = col*radius*2+x_offset
            cc = rgb_random_jitter(p.color1, jitter).ctoi()
            # print(f'({x},{y})-{cc} ', end='')
            draw_arc(draw, (x,y), radius, wcounts, width=lwidth, scale=obl,
                 color=cc, bg=c2, grad=grad)
        # print('')
    return img


if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = WIDTH
    p.height = HEIGHT
    
    image = generate(p)
    image.show()
