"""wallpaper generator 共通クラス＆関数"""
from dataclasses import dataclass
import random
import re
import copy
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageColor
import os.path as pa
import colorsys

def clip8(x):
    """clip8(x) -> {x | 0 <= x <= 255}の整数に制限する"""
    return min(255, max(int(x), 0))


def stoi(s, default=0, lo=None, hi=None, multi=False):
    """文字列を数値に プレフィクス、実数対応
       省略可パラメータ default:変換失敗時の値, lo,hi:下限、上限
       multi=False:先頭の値、True:階層リスト(list と ','区切り文字列)対応"""
    if isinstance(s, list):  # リストだったら各要素を変換
        ret = [stoi(x, default, lo, hi, multi=multi) for x in s]
        return ret if multi else ret[0]

    if isinstance(s, (int, float)):  # 数値だったらすぐ返す
        ret = s
        
    elif isinstance(s, str):
        s = s.strip().lower()
        if ',' in s:  # カンマ区切り文字列はリストにして再変換
            return stoi(s.split(','), default, lo, hi, multi=multi)

        try:
            if s.startswith(('0x','0o','0b')):  # プレフィクス付き
                ret = int(s, 0)
            elif '.' in s or 'e' in s:  # 実数
                ret = float(s)
            else:  # 整数
                ret = int(s)
        except ValueError or SyntaxError:
            ret = float(default) if '.' in s or 'e' in s else int(default)
    else:  # よくわからない型だったらデフォ
        ret = default

    if lo is not None:
        ret = max(lo, ret)
    if hi is not None:
        ret = min(ret, hi)

    return ret


def rgb_string(*args):
    """文字列、タプル、RGBColorの値を'#rrggbb'に変換"""
    x = args[0] if len(args)==1 else args
    if isinstance(x, str):
        try:
            _ = ImageColor.getrgb(x)
            return x
        except ValueError:
            return None
    rgb = to_rgb(x)
    if rgb is None:
        return None
    else:
        s = '#'
        for d in rgb[:min(len(rgb),4)]:
            s += f'{d:02X}'
        return s


def to_rgb(*args):
    """文字列、タプル、RGBColorの値を(r,g,b)に変換"""
    x = args[0] if len(args)==1 else args
    if isinstance(x,(list,tuple)):
        if len(x)==3:
            return tuple(clip8(int(t,0))
                         if isinstance(t,str) else clip8(int(t))
                         for t in x[:3])
        elif len(x)==4:
            return tuple(clip8(int(t,0))
                         if isinstance(t,str) else clip8(int(t))
                         for t in x[:4])
    elif isinstance(x,str):
        try:
            return ImageColor.getrgb(x)
        except ValueError:
            return None
    elif isinstance(x, RGBColor):
        return x.ctoi()
    else:
        return None


class RGBColor:
    """色を格納するクラス"""
    def __init__(self, *args):
        l = len(args) 
        if l == 3 or l == 4:
            val = args
        elif l == 1:
            val = args[0]
        else:
            raise ValueError('Invalid argument format')

        rgb =  to_rgb(val)
        if rgb is None:
            raise ValueError('Invalid color format')

        self.r, self.g, self.b = rgb[:3]

    def ctox(self):
        return f'#{self.r & 0xff:02x}{self.g & 0xff:02x}{self.b & 0xff:02x}'

    def ctoi(self):
        return self.r & 0xff, self.g & 0xff, self.b & 0xff

    def black(self):
        self.r, self.g, self.b = 0,0,0
        return self.r, self.g, self.b

    def xtoc(self, s: str):
        s = s.lstrip('#')
        try:
            self.r, self.g, self.b = (int(s[i:i+2], 16) & 0xff for i in (0,2,4))
        except ValueError:
            self.r, self.g, self.b = 0,0,0
        return self.r, self.g, self.b
        
    def itoc(self, r, g, b):
        self.r = clip8(r)
        self.g = clip8(g)
        self.b = clip8(b)
        return self.r, self.g, self.b


SAVE_NUM=9
PARAMVALS = ['color1', 'color2', 'color3',
             'color_jitter', 'sub_jitter', 'sub_jitter2',
             'pwidth', 'pheight', 'pdepth']

@dataclass
class Param:
    """モジュールに渡すパラメータ"""
    width: int = 1920
    height: int = 1080
    wwidth: int = 0  # tk makes automatically
    wheight: int = 0
    wposx: int = 0  # tk locates automatically
    wposy: int = 0
    color1: RGBColor = RGBColor(220,214,96)
    color2: RGBColor = RGBColor(0,0,0)
    color3: RGBColor = RGBColor(0,0,0)
    color_jitter:int = 48  # 色ゆらぎ(主色)
    sub_jitter: int = 27  # 色ゆらぎ(パターン)
    sub_jitter2: int = 0  # 色ゆらぎ(パターン2)
    pwidth: int = 17
    pheight: int = 140
    pdepth: int = 0
    pattern: str = ''  # module名
    savefile: str = ''
    h_img = None  # hold image
    h_state = {}  # hold state

    def file_name(self):
        if len(self.savefile) < 1:
            self.savefile = self.pattern+'.png'
        base = pa.splitext(self.savefile)[0]
        if pa.exists(self.savefile):
            for i in range(SAVE_NUM-1):
                if not pa.exists(f'{base}{i}.png'):
                    break
                elif i == SAVE_NUM-2:
                    print('Already saved enough...')
            fname = f'{base}{i}.png'
            self.savefile = fname
        return self.savefile

    def keep(self, modname: str='', image=None):  # 現在の設定を保持(画像も)
        self.h_img = None
        self.h_state['module'] = modname
        if modname is not None and modname != '':
            list = ['width', 'height', *PARAMVALS]
            for x in list:
                self.h_state[x] = copy.deepcopy(getattr(self, x))
            self.h_state['width'] = self.width
            self.h_state['height'] = self.height
            if image is not None:
                self.h_img = image.copy()
            else:
                w = max(1, self.width)
                h = max(1, self.height)
                self.h_img = Image.new('RGB', (w,h), 0)

    def unkeep(self):  # keepしたものをクリア
        self.h_img = None
        self.h_state = {}

    def retrieve(self):
        if 'module' in self.h_state:
            list = ['width', 'height', *PARAMVALS]
            for x in list:
                if x in self.h_state:
                    setattr(self, x, copy.deepcopy(self.h_state[x]))
            return  self.h_state['module']
        else:
            return None

    def bg(self, width=0, height=0):
        """keepしたimageを取得(リサイズ有り): 第1引数=Noneにするとresizeなし
           width,heightが無指定の場合、(self.width, self.height)にリサイズ
        """
        if self.h_img is None:
            return None
        w = self.width if width == 0 else width
        h = self.height if height == 0 else height
        iw, ih = self.h_img.size
        img = self.h_img.copy()
        if w is not None and h is not None and (iw != w or ih != h):
            return img.resize((w,h),resample=Image.LANCZOS)
        else:
            return img


# プラグインのspec()で、モジュール名、説明、利用パラメータを返すように
# して、それをModulesに保存
# モジュールファイル名は mod_ で始めるが、モジュール名はmod_なし
# 利用パラメータリストは、利用するパラメータ名のリスト(入っているものは利用)
#  (例) mod_gui['stripe'] = ['color1', 'color_jitter', 'pwidth', ...]
class Modules:
    """プラグインモジュール情報"""
    def __init__(self):
        self.modules = []
        self.mod_desc = {}
        self.mod_gui = {}

    def add_module(self, module_name: str, module_desc: str,
                   using_gui_list):
        if module_name.startswith('mod_'):
            module_name = module_name.split('mod_')[1]
        if module_name not in self.modules:
            self.modules.append(module_name)
            self.mod_desc[module_name] = module_desc
            self.mod_gui[module_name] = using_gui_list


def is_param(x:str):
    return x in PARAMVALS


class EfxModules:
    """AfterEffectモジュール情報"""
    def __init__(self):
        self.modules = []
        self.mod_desc = {}
        self.mod_type = {}

    def add_module(self, module_name: str, module_desc: str,
                   spec_dict):
        if module_name.startswith('efx_'):
            module_name = module_name[4:]
            module_name = 'AE_'+module_name
        if module_name not in self.modules:
            self.modules.append(module_name)
            self.mod_desc[module_name] = module_desc
            self.mod_type[module_name] = spec_dict


# 色演算  color -> color etc.
def rgb_random_jitter(color, jitter):
    """(R,G,B)に対してそれぞれ±jitterの幅でランダムに変化"""
    rgb = to_rgb(color)
    rgb = tuple(clip8((c + random.randint(-jitter, jitter))) for c in rgb)
    return RGBColor(rgb)


def rated_jitter(color, jitter_r):
    """jitter_rで元の色に対して何%の変動かを与える"""
    j = min(1.0, max(jitter_r/100.0, 0.0))
    rgb = to_rgb(color)
    rgb = tuple(clip8(c*(1+random.uniform(-j, j))) for c in rgb)
    return RGBColor(rgb)


def brightness(color, f=1.0, h=0.0, s=1.0, bg=None):
    """色をHSL値で調整 → retruns: RGBColor
    f: lightness darken if f < l.0, lighten if f > 1.0 (multiply)
    s: satulation cahge in s (multiply)
    h: hue change in h (add)
    bg: returns default color when result is (0,0,0)
    """
    crgb = to_rgb(color)
    r_norm, g_norm, b_norm = [c / 255.0 for c in crgb]
    ch, cl, cs = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)

    new_h = ch+h if (ch+h)<=1.0 else round(ch+h - int(ch+h),6) 
    new_l = max(0.0, min(1.0, cl*f))
    new_s = max(0.0, min(1.0, cs*s))
    r_new, g_new, b_new = colorsys.hls_to_rgb(new_h, new_l, new_s)

    if r_new+g_new+b_new <= 0.0:
        return bg if isinstance(bg, RGBColor) else RGBColor(0,0,0)

    return RGBColor(round(r_new * 255),
                    round(g_new * 255),
                    round(b_new * 255))


def rgb_lerp(c1, c2, t):
    """ RGB値の線形補完 c1,c2=tuple(r,g,b), t=比率(0..1)"""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def bg_and_font(color):
    """色指定文字列かRGBColorで色を受け取り、前景テキストと色指定文字列を返す"""
    if isinstance(color,(str,RGBColor)):
        color = to_rgb(color)
    rgb = color         

    l = (0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2])/255
    # ガンマ補正なし,閾値0.89が一般的らしいがおじさんの目にやさしく閾値を低く
    if l > 0.70:
        f = '#000000'
    else:
        f = '#ffffff'
    return f, rgb_string(rgb)


# 色調調整 Image -> Image
def sat_attenate(image, ratio):
    """彩度の変更： 0 < ratio(%) < 200 """
    enhancer = ImageEnhance.Color(image)
    return enhancer.enhance(min(2.0, max(0.0, ratio/100.0)))

def bri_attenate(image, ratio):
    """明度の変更： 0 < ratio(%) < 200 """
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(min(2.0, max(0.0, ratio/100.0)))

def con_attenate(image, ratio):
    """コントラストの変更： 0 < ratio(%) < 200 """
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(min(2.0, max(0.0, ratio/100.0)))


# 背景パターン
def vertical_gradient_rgb(width, height, cstart, cend):
    """縦グラデーションのImage.Imageビットマップ"""
    cs = to_rgb(cstart)  # 開始色 (上)
    ce = to_rgb(cend)   # 終端色 (下)
    
    y_axis = np.linspace(0, 1, height).reshape(-1, 1)
    r = np.tile(y_axis, (1, width))
    r, g, b = [(cs[i] * (1 - r) + ce[i] * r) for i in range(3)]
    
    return Image.fromarray(np.dstack((r, g, b)).astype(np.uint8), 'RGB')


def horizontal_gradient_rgb(width, height, cstart, cend):
    """横グラデーションのImage.Imageビットマップ"""
    cs = to_rgb(cstart)  # 開始色(左)を(r,g,b)に変換
    ce = to_rgb(cend)  # 終端色(右)を(r,g,b)に変換
    
    x_axis = np.linspace(0, 1, width)
    r = np.tile(x_axis, (height, 1))
    r,g,b = [(cs[i] * (1 - r) + ce[i] * r) for i in range(3)]
    return Image.fromarray(np.dstack((r, g, b)).astype(np.uint8), 'RGB')


def diagonal_gradient_rgb(width, height, cstart, cend):
    """対角(右上－左下)グラデーションのImage.Imageビットマップ"""
    y, x = np.mgrid[0:height, 0:width]  # 座標グリッド
    t = (x + y) / (width + height)  # 正規化パラメータ t

    # RGB を配列化
    cs = to_rgb(cstart)
    ce = to_rgb(cend)
    cs = np.array(cs, dtype=np.float32)
    ce = np.array(ce, dtype=np.float32)

    img = cs + (ce - cs) * t[..., None]  # 線形補完（ブロードキャスト）

    return Image.fromarray(img.astype(np.uint8), 'RGB')


# グラデーション背景の生成テンプレ
#   bg_start = rgb_random_jitter(bg_color, jitter)
#   bg_end   = rgb_random_jitter(bg_color, jitter)
#   image = diagonal_gradient_rgb_np(width, height,
#                                    bg_start, bg_end)
#   draw = ImageDraw.Draw(image)


def get_pos(event_str: str):
    """Mouse Event文字列から座標を取り出す"""
    # print(event_str)   
    x_match = re.search(r"x=(\d+)", event_str)
    y_match = re.search(r"y=(\d+)", event_str)

    mouse_x = int(x_match.group(1)) if x_match else -1
    mouse_y = int(y_match.group(1)) if y_match else -1

    return (mouse_x, mouse_y)


