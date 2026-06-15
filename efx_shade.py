import TkEasyGUI as sg
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np
import math
import os.path as pa
from wall_common import *

def intro(efxlist: EfxModules, module_name):
    efxlist.add_module(module_name, '前景＋影貼り付け',
                       {'mask': ['draw_wiremesh_mask',
                                 'draw_chair_table_mask',
                                 'draw_ladder_mask'],
                        'proc': [('add_silhouette', 'mask'),
                                 ('add_foreimage', 'mask'),
                                 ]
                        })
    # proc: [(<function>, <usable_subs>),...]
    return module_name


# MASK functions
def draw_wiremesh_mask(W, H, position=None):
    '''W,H: base size, position: for compatibility-> retrun mask'''
    # パラメータ
    PITCH = 135        # 線間隔
    THICKNESS = 53     # 線の太さ

    ANGLE1 = 72
    ANGLE2 = -ANGLE1
    # =========================

    mask1 = create_stripe_mask(W, H, PITCH, THICKNESS, ANGLE1)
    mask2 = create_stripe_mask(W, H, PITCH, THICKNESS, ANGLE2)

    mesh_mask = mask1 | mask2

    img_array = (mesh_mask * 255).astype(np.uint8)
    mask = Image.fromarray(img_array, mode="L")

    return mask


def create_stripe_mask(width, height, pitch, thickness, angle_deg):
    theta = np.deg2rad(angle_deg)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    # 座標生成
    y, x = np.mgrid[0:height, 0:width]

    # ===== 中央を原点にする =====
    cx = width / 2
    cy = height / 2
    x = x - cx
    y = y - cy

    # 斜め方向へ射影
    u = x * cos_t + y * sin_t

    # 中央対称にするために絶対値を使う方法もあるが、
    # 今回は周期を中央基準にする
    stripe = np.mod(u + pitch/2, pitch)

    mask = stripe < thickness

    return mask


def draw_chair_table_mask(W, H, position=None):
    '''W,H: base size, bbox: 4point of mask region -> retrun mask'''
    # マスクベース
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)

    # 配置領域
    if position is not None:
        x0, y0 = position
    else:
        x0 = int(W*1/12)
        y0 = int(H*2/3)
    region_w = int(W*5/12)
    region_h = int(H*1/3)

    # ====================
    # 椅子
    # ====================
    chair_w = int(region_w * 0.3)
    chair_h = region_h
    cx0 = x0
    cx1 = x0 + chair_w
    
    leg_h = int(region_h * 0.4)  # 脚長 2/5
    back_h = int(region_h * 0.6)   # 背板長 3/5
    seat_h = int(region_h * 0.1)  # 座面厚

    seat_y1 = y0 + region_h - leg_h
    seat_y0 = seat_y1 - seat_h
    back_y0 = seat_y0 - back_h
    back_y1 = seat_y0

    # 背板
    back_shift = int(math.cos(math.radians(85))*chair_w)
    back_thick = chair_w * 0.13
    md.polygon((cx0, back_y0, cx0+back_thick, back_y0,
                cx0+back_thick+back_shift, back_y1,
                cx0+back_shift, back_y1), fill=255)

    # 座面（L字）
    md.rectangle((cx0, seat_y0, cx0+chair_w*0.9, seat_y1), fill=255)

    # 脚
    leg_shift = int(math.cos(math.radians(87))*chair_w)
    leg_w = chair_w*0.15

    # 左脚
    lleg_x0 = cx0 + leg_w*0.08
    md.polygon((lleg_x0+leg_shift, seat_y1,
                lleg_x0+leg_shift+leg_w, seat_y1,
                lleg_x0+leg_w, y0+region_h,
                lleg_x0, y0+region_h), fill=255)
    
    # 右脚
    rleg_x1 = cx0 + chair_w*0.9 - leg_w*0.08
    md.polygon((rleg_x1-leg_w-leg_shift, seat_y1,
                rleg_x1-leg_shift, seat_y1,
                rleg_x1, y0+region_h,
                rleg_x1-leg_w, y0+region_h), fill=255)

    # ====================
    # 机
    # ====================
    table_w = int((region_w - chair_w)*0.9)
    tx0 = int(cx1 + table_w * 0.1)
    tx1 = tx0+table_w
    
    # 天板
    table_top_y = int((back_y0 + seat_y0) / 2)  # 天板上面(背板と座面の中間)
    table_top_h = int(region_h * 0.14)  # 天板厚さ

    # 天板
    md.rectangle((tx0, table_top_y, tx1, table_top_y+table_top_h), fill=255)

    # 脚
    leg_shift = int(math.cos(math.radians(89))*table_w)
    leg_w = int(table_w * 0.11)  # 脚幅
    leg_off = int(table_w * 0.1)  # 脚繰込み
    leg_top = table_top_y + table_top_h  # 脚上端Y
    leg_h = y0 + region_h - leg_top  # 脚高さ

    # 左脚
    lleg_x = int(tx0 + leg_off)
    md.polygon((lleg_x+leg_shift, leg_top,
                lleg_x+leg_shift+leg_w, leg_top,
                lleg_x+leg_w, y0+region_h,
                lleg_x, y0+region_h), fill=255)
    
    # 右脚
    rleg_x = tx0 + table_w - leg_off - leg_w
    md.polygon((rleg_x-leg_shift, leg_top,
                rleg_x-leg_shift+leg_w, leg_top,
                rleg_x+leg_w, y0+region_h,
                rleg_x, y0+region_h), fill=255)

    # 筋交い
    md.line((lleg_x+leg_shift+leg_w//2,leg_top,
             rleg_x-leg_shift+leg_w//2,leg_top+leg_h//3),
            fill=255, width=leg_w//2)
    md.line((rleg_x-leg_shift+leg_w//2,leg_top,
             lleg_x+leg_shift+leg_w//2,leg_top+leg_h//3),
            fill=255, width=leg_w//2)

    return mask


def draw_ladder_mask(W, H, position=None):
    steps=8
    set_width = int(W/6)
    ladder_width_ratio=0.7
    rung_height_ratio=0.18
    rail_width_ratio=0.1
    
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)

    if position is not None:
        x0, y0 = position
        y1 = H
    else:
        x0 = W - set_width
        y0 = 0
        y1 = H

    ladder_w = int(set_width * ladder_width_ratio)
    rail_w = int(ladder_w * rail_width_ratio)
    step_h = H / steps
    rung_h = step_h * rung_height_ratio


    #base = base.convert("RGBA")
    #W, H = base.size

    # shadow_w = int(W * shadow_width_ratio)
    # x0 = W - shadow_w
    # xL = x0 + ladder_w


    # 梯子
    md.rectangle((x0, y0, x0 + rail_w, y1), fill=255)
    md.rectangle((x0 + ladder_w - rail_w, y0, x0 + ladder_w, y1), fill=255)

    for i in range(steps):
        cy = step_h * (i + 0.5)
        y0 = int(cy - rung_h / 2)
        y1 = int(cy + rung_h / 2)
        md.rectangle((x0, y0, x0 + ladder_w, y1), fill=255)

    return mask


# PROC functions
def add_foreimage(base, mask):
    filename = sg.popup_get_file('Read file [FG]',
                                 file_types=[('PNG','*.png'),('Any','*.*'),])
    if pa.exists(filename):
        base2 = Image.open(filename)
        image = add_silhouette(base, mask, base2)
        return image
    return None


# 前景を切り抜いて影付きで貼る(numpy版)
def add_silhouette(base, mask, base2=None,
                   shift=30,
                   shadow_alpha=90, blur_radius=8,
                   sharp_radius=0, sharp_percent=180, sharp_threshold=3,
                   W=1920, H=1080):

    if base is not None:
        base = base.convert("RGBA")
        W, H = base.size
    else:
        base = Image.new('RGBA', (W, H), color='#ffffff')

    if mask is None:
        mask = draw_chair_table_mask(W, H)

    # ====================
    # 影
    # ====================
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, shadow_alpha), mask=mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

    # ====================
    # NumPyで周期シフト
    # ====================
    dx = -shift
    dy = -shift

    if isinstance(base2, Image.Image):
        base_np = np.array(base2.convert('RGBA'))
    else:
        base_np = np.array(base)
    shifted_np = np.roll(base_np, shift=(dy, dx), axis=(0, 1))
    shifted = Image.fromarray(shifted_np, mode="RGBA")

    # ====================
    # マスクで切り抜き
    # ====================
    fg = Image.composite(
        shifted,
        Image.new("RGBA", (W, H), (0, 0, 0, 0)),
        mask
    )

    if sharp_radius > 0:
        fg = fg.filter(
            ImageFilter.UnsharpMask(
                radius=sharp_radius,
                percent=sharp_percent,
                threshold=sharp_threshold
            )
        )

    # ====================
    # 合成
    # ====================
    result = base.copy()
    result = Image.alpha_composite(result, shadow)
    result = Image.alpha_composite(result, fg)

    return result


# --------------------
# main
# --------------------
MASKS = {'Chair and Table': draw_chair_table_mask,
         'Ladder': draw_ladder_mask,
         'Mesh': draw_wiremesh_mask,
         }

def shadowed_img(base_file, mask_name, default_size=(800,450)):
    if base_file is not None:
        try:
            img = Image.open(base_file)
        except FileNotFoundError:
            img = Image.new('RGBA', default_size, 'white')
    else:
        img = Image.new('RGBA', default_size, 'white')

    W,H = img.size
    try:
        mask = MASKS[mask_name](W,H)
    except KeyError:
        mask = None

    sample = add_silhouette(img, mask)
    return sample


def test_gui():
    test_x, test_y = 800, 450
                
    menu = list(MASKS.keys())
    menu_lo = []
    for x in menu:
        menu_lo.append([sg.Radio(x, group_id='-item-')])
    lo = [[sg.Text('Flavor Type'), sg.Column(menu_lo)],
          [sg.Image(size=(test_x, test_y), key='-timg-')],
          [sg.Button('File', key='-file-'),
           sg.Text('', key='-fn-', expand_x=True),
           sg.Button('File2', key='-file2-'),
           sg.Text('', key='-fn2-', expand_x=True),
           sg.Button('Test', key='-test-'),
           sg.Button('Ok', key='-ok-'),sg.Button('Cancel', key='-can-'),]]

    file_types = [('PNG','*.png'),('JPG','*.jpg'),('Any','*.*'),]
    src_path, src_path2 = None, None
    mask_name = None
    
    wn = sg.Window('Add Flavor', layout=lo)

    while True:
        ev, va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            break
        elif ev == '-file-':
            src_path = sg.popup_get_file('Read file', file_types=file_types)
            wn['-fn-'].update(pa.basename(src_path))
            if pa.exists(src_path):
                sample = shadowed_img(src_path, va['-item-'], (test_x, test_y))
                wn['-timg-'].update(data=sample)
            continue
        elif ev == '-file2-':
            src_path2 = sg.popup_get_file('Read file [FG]',
                                          file_types=file_types)
            wn['-fn2-'].update(pa.basename(src_path2))
            if pa.exists(src_path2):
                sample = shadowed_img(src_path2, va['-item-'], (test_x, test_y))
                wn['-timg-'].update(data=sample)
            continue
        elif ev == '-test-':
            sample = shadowed_img(src_path, va['-item-'], (test_x, test_y))
            wn['-timg-'].update(data=sample)
            continue
        elif ev == '-ok-':
            for x in menu:
                if va[x]:
                    mask_name = x
            if mask_name is not None:
                break

    wn.close()
    return src_path, src_path2, mask_name


if __name__ == "__main__":
    src_path, src_path2, mask_name = test_gui()
    if src_path != '' and src_path is not None:
        img = Image.open(src_path)
        W,H = img.size
        if mask_name is not None and mask_name != '':
            mask = MASKS[mask_name](W,H)
        else:
            mask = None
        if src_path2 is not None:
            img2 =  Image.open(src_path2)
        else:
            img2 = None
        result = add_silhouette(img, mask, base2=img2)
        # , sharp_radius=1, sharp_percent=100, sharp_threshold=3)
        result.show()
        result.save('add_shade.png')
