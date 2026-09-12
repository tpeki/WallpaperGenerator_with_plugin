from wall_common import *
import TkEasyGUI as sg
from PIL import Image, ImageDraw, ImageFont, ImageFilter
    #, ImageOps, ImageTk, ImageChops
import numpy as np
import datetime
import copy
import io
import os
import os.path as pa
import filedialog as fdi
import calendar
import textwrap
from fontTools.ttLib import TTFont
import zipfile
import threading
#import time

# FONT・ファイル関連SG
SysFont_Dir = r'c:\Windows\Fonts'
Font_Dir = SysFont_Dir
FONT_EXT=('.ttf', '.otf', '.ttc')  #, '.fon')
Font_Dic = {}
ExceptList = ['CRCGHankoin.ttc']  # 読み込み時エラーが発生するFONTファイル
Image_Files = [('PNG','*.png'),('JPG','*.jpg'),('Any','*.*'),]
Cramped = False  # True -> 画面サイズが小さい場合はLoremモジュールを割愛

# メニュー定数
POS = ['nw', 'n', 'ne', 'w', 'c', 'e', 'sw', 's', 'se']
GRADTYPE = ['None', 'Linear', 'Stripe']
FgMenu = ['FG', 'BG', 'File', 'Plain']
FgInd = ['*frontimage*', '*internal*', '*file*', '*plain*']
Mask_Code = {'cal': 'calendar', 'txt': 'text', 'lor': 'lorem'}
T_FX = ['None', 'Layerd', 'HollowStack']

# 描画SG
Preview_Size = (498,279)
Alert_Color = '#772222'
FontList_Size = 8
Init_Color = (48, 128, 192)
WDAY_INT = 0xff
PADDING = 32

# 不揮発メモ
impose_preserv = {'shade': {'shift':8, 'alpha':40, 'blur':10, 'enbri':0.0,
                            'color':(0,0,0)},
                  'fontset': {'key':None, 'fontdir': Font_Dir},
                  'fontex': {'size':64, 'half':238, 'grad':0, 'mid':35},
                  'common': {'pos':8, 'lspc':1.4, 'spc':1.3,
                             'xpad':32, 'ypad':60},
                  'fgsel': {'color': Init_Color, 'jit':63, 'path':'',
                            'mode':FgMenu[3], 'swap':0},
                  'calendar': {'year':2026, 'month':1, 'multi':1,
                               'wend':1, 'holi':1, 'tate':0},
                  'text': {'msg1$': 'Lorem ipsum','msg2$': '',
                           'effect':0, 'stack':0, 'upper':0},
                  'lorem': {'width':30, 'path':'', 'lmax':66, 'ensp':0},
                  }

# マスクモジュール定数
SP_HOLIDAY = [(1, 1),   # 元日
              (2, 11),  # 建国記念の日
              (2, 23),  # 天皇誕生日
              (4, 29),  # 昭和の日
              (5, 3),   # 憲法記念日
              (5, 4),   # みどりの日
              (5, 5),   # こどもの日
              (8, 11),  # 山の日
              (11, 3),  # 文化の日
              (11, 23), # 勤労感謝の日
              ]

HM_HOLIDAY =[(1, 2),  # 成人の日     1月 第2月曜
             (7, 3),  # 海の日       7月 第3月曜
             (9, 3),  # 敬老の日     9月 第3月曜
             (10, 2), # スポーツの日 10月第2月曜
             ]

LOREM = 'Lorem ipsum dolor sit amet, consectetur adipiscing '+\
        'elit, sed do eiusmod tempor incididunt ut labore et '+\
        'dolore magna aliqua. Ut enim ad minim veniam, quis '+\
        'nostrud exercitation ullamco laboris nisi ut aliquip '+\
        'ex ea commodo consequat. Duis aute irure dolor in '+\
        'reprehenderit in voluptate velit esse cillum dolore '+\
        'eu fugiat nulla pariatur. Excepteur sint occaecat '+\
        'cupidatat non proident, sunt in culpa qui officia '+\
        'deserunt mollit anim id est laborum.'
ENCODING = 'utf-8'

# --------------------
# EFX登録
# --------------------
def intro(efxlist: EfxModules, module_name):
    efxlist.add_module(module_name, 'カレンダー貼り付け',
                       {'proc': ['add_calendar',
                                 ]
                        })
    # proc: [(<function>, <usable_subs>),...]
    return module_name


class ShadeP:
    def __init__(self, preserv):
        self.shift = preserv.get('shift', 8)
        self.alpha = preserv.get('alpha', 40)
        self.blur = preserv.get('blur', 10)
        self.enbri = preserv.get('enbri', 0.0)
        self.color = preserv.get('color', None)

        if not isinstance(self.color, tuple):
            self.color = (0,0,0)

    def to_dict(self, preserv=None):
        retv = {
            'shift': self.shift,
            'alpha': self.alpha,
            'blur': self.blur,
            'enbri': self.enbri,
            'color': self.color,
            }
        if preserv:
            preserv =  retv
        return retv

    def sub_layout(self):
        sfgc, sbgc = bg_and_font(self.color)
        return [[sg.Text('Shift='),
                 sg.Input(f'{self.shift}', key='-sshift-', width=4),
                 sg.Text('Blur='),
                 sg.Input(f'{self.blur}', key='-sblur-', width=4),],
                [sg.Text('Intent'),
                 sg.Input(f'{self.alpha}', key='-salpha-', width=4),
                 sg.Text('Color'),
                 sg.Button('...', text_color=sfgc, background_color=sbgc,
                           key='-scolor-', width=3),
                 ],
                [],
                [sg.Text('Fg-Enbright'),
                 sg.Input(f'{self.enbri}', key='-senbri-', width=4),],
                ]

    def scan(self, wn):
        self.shift = stoi(wn['-sshift-'].get())
        self.blur = stoi(wn['-sblur-'].get())
        self.alpha = stoi(wn['-salpha-'].get())
        self.enbri = stoi(wn['-senbri-'].get())
        # self.color = to_rgb(wn['-scolor-'].props['bg'])
       

class FontsetP:
    def __init__(self, preserv):
        global Font_Dic
        
        self.key = preserv.get('key', None)
        self.font_dir = preserv.get('fontdir', None)

        if Font_Dic == {}:
            print(f'Fontset init')
            if self.font_dir is None or not pa.exists(self.font_dir):
                self.font_dir = Font_Dir  # 存在しなければデフォルト
            fk, self.font_dic = make_font_dic(self.font_dir)
            if not self.key in fk:
                self.key = fk[0]
            Font_Dic = self.font_dic
        else:  # Font_Dicが生きてる
            self.font_dic = Font_Dic
            if self.font_dir is None or not pa.exists(self.font_dir):
                self.font_dir = '*'  # font_dirが壊れてた
            if self.key is None:  # keyが消えてた
                self.key = list(Font_Dic.keys())[0]

    def to_dict(self, preserv=None):
        global Font_Dic
        
        retv = {
            'key': self.key,
            'fontdir': self.font_dir,
            }
        if preserv:
            preserv = retv

        Font_Dic = self.font_dic
        return retv


class FontexP:
    def __init__(self, preserv):
        self.size =  preserv.get('size', 64)
        self.half = preserv.get('half', 238)
        self.grad = preserv.get('grad', 0)
        self.mid = preserv.get('mid', 35)

    def to_dict(self, preserv=None):
        retv = {
            'size': self.size,
            'half': self.half,
            'grad': self.grad,
            'mid':  self.mid,
            }
        if preserv:
            preserv = retv
        return retv
            
    def sub_layout(self):
        return [
            sg.Text('Size'),
            sg.Input(f'{self.size}', key='-fsize-', width=3),
            sg.Text('Halftone'),
            sg.Input(f'{self.half}', key='-chalf-', width=4),
            sg.Text(' '),
            sg.Text('Gradient'),
            sg.Combo(GRADTYPE, key='-cgrad-', size=(6,1), readonly=True,
                     default_value=GRADTYPE[self.grad], enable_events=True),
            sg.Text('boundary(%)'),
            sg.Input(f'{self.mid}', key='-cmid-', width=3),
            sg.Text(expand_x=True),
            ]

    def scan(self, wn):
        self.size = stoi(wn['-fsize-'].get(), default=64, lo=5)
        self.half = stoi(wn['-chalf-'].get(), default=238, lo=0, hi=255)
        try:
            self.grad = GRADTYPE.index(wn['-cgrad-'].get())
        except ValueError:
            self.grad = 0
            wn['-cgrad-'].update(GRADTYPE[0])
        self.mid = stoi(wn['-cmid-'].get(), default=35, lo=0, hi=100)


class CommonP:
    def __init__(self, preserv):
        self.pos = preserv.get('pos', 8)
        self.lspc = preserv.get('lspc', 1.4)
        self.spc = preserv.get('spc', 1.3)
        self.xpad = preserv.get('xpad', 32)
        self.ypad = preserv.get('ypad', 60)

    def to_dict(self, preserv=None):
        retv = {
            'pos':  self.pos,
            'lspc': self.lspc,
            'spc':  self.spc,
            'xpad': self.xpad,
            'ypad': self.ypad,
            }
        if preserv:
            preserv = retv
        return retv
            
    def sub_layout(self):
        return [
            [sg.Text('BlockSpace', expand_x=True),
             sg.Input(f'{self.spc}', key='-cspc-', width=4),],
            [sg.Text('LineSpace', expand_x=True),
             sg.Input(f'{self.lspc}', key='-clspc-', width=4),],
            [sg.Text('X-pad'),
             sg.Input(f'{self.xpad}', key='-cxpd-', width=4),
             sg.Text('Y-pad'),
             sg.Input(f'{self.ypad}', key='-cypd-', width=4),],
            [sg.Text(expand_x=True),
             sg.Text('Block Align'),
             sg.Combo(POS, key='-cpos-', size=(4,1), readonly=True,
                      default_value=POS[self.pos], enable_events=True),]
            ]

    def scan(self, wn):
        self.spc = stoi(wn['-cspc-'].get(), default=1.3, lo=0.0)
        self.lspc = stoi(wn['-clspc-'].get(), default=1.4, lo=0.0)
        self.xpad = stoi(wn['-cxpd-'].get(), default=32, lo=0)
        self.ypad = stoi(wn['-cypd-'].get(), default=60, lo=0)
        try:
            self.pos = POS.index(wn['-cpos-'].get())
        except ValueError:
            self.pos = 8
            wn['-cspc-'].update(POS[self.pos])


class FgselP:
    def __init__(self, preserv):
        self.color = preserv.get('color',  None)
        if not isinstance(self.color, tuple):
            self.color = Init_Color
        self.jit = preserv.get('jit', 0)
        self.path = preserv.get('path', '')
        self.mode = preserv.get('mode', FgMenu[3])
        self.swap = preserv.get('swap', 0)

    def to_dict(self, preserv=None):
        retv = {
            'color': self.color,
            'jit': self.jit,
            'path': self.path,
            'mode': self.mode,
            'swap': self.swap,
            }
        if preserv:
            preserv =  retv
        return retv

    def sub_layout(self):
        fgc, bgc = bg_and_font(self.color)
        try:
            n = FgMenu.index(self.mode)
        except ValueError:
            n = 3
            self.mode = FgMenu[n]
        fname = pa.basename(self.path) if n == 2 else FgInd[n]

        return [
            [sg.Combo(FgMenu, default_value=self.mode, key='-fgsel-',
                      width=5, readonly=True, enable_events=True),
             sg.Checkbox('Swap FG/BG', default=False, key='-swap-'),
             sg.Text(' Plain:'),
             sg.Button('BaseColor', key='-bgc-', text_color=fgc,
                       background_color=bgc),
             sg.Text('Jitter'), sg.Input(f'{self.jit}',
                                         key='-badd-', width=4),
             sg.Text(' '),
             sg.Text('File:'),
             sg.Text(fname, key='-fn1-', background_color='#f8f8f8',
                     expand_x=True),
             sg.Button('< File', key='-file1-', background_color='#ffffdd'),
             ],
            ]

    def scan(self, wn, bg):
        sel = wn['-fgsel-'].get()
        self.swap = 1 if wn['-swap-'].get() else 0
        self.jit = stoi(wn['-badd-'].get())
        # self.fname = set by behaviour
        #self.color = to_rgb(wn['-bgc-'].props['bg'])

        if sel == FgMenu[0]:  # 'FG'
            if self.mode != FgMenu[0]:
                self.mode = FgMenu[0]
                wn['-fn1-'].update(FgInd[0])
        elif sel == FgMenu[1]:  # 'BG'
            if self.mode != FgMenu[1]:
                if bg:
                    self.mode = FgMenu[1]
                    wn['-fn1-'].update(FgInd[1])
                else:
                    wn['-fgsel-'].update(self.mode)
        elif sel == FgMenu[2]:  # 'File'
            if self.mode != FgMenu[2]:
                if pa.exists(self.path):
                    self.mode = FgMenu[2]
                    fname = pa.basename(self.path)
                    wn['-fn1-'].update(fname)
                else:
                    self.path = ''
                    wn['-fgsel-'].update(self.mode)
        else:  # 'Plain'
            wn['-fn1-'].update(FgInd[3])
            self.mode = FgMenu[3]

        return FgMenu.index(self.mode)


class CalendarP:
    def __init__(self, preserv):
        if not 'calendar' in preserv.keys():
            preserv['calendar'] = {}
        ps = preserv['calendar']
        self.year = ps.get('year', 1980)
        self.month = ps.get('month', 1)
        self.multi = ps.get('multi', 1)
        self.wend = ps.get('wend', 1)
        self.holi = ps.get('holi', 1)
        self.tate = ps.get('tate', 0)

    def to_dict(self, preserv=None):
        retv = {
            'year': self.year,
            'month': self.month,
            'multi': self.multi,
            'wend': self.wend,
            'holi': self.holi,
            'tate': self.tate,
            }
        if preserv:
            preserv =  retv
        return retv

    def sub_layout(self, activate=False):
        return [
            sg.Column(size=(120,40), layout=[
                [sg.Radio('', group_id='-shpg-', default=activate,
                     key='-shpcal-', enable_events=True),
                 sg.Text('Calendar', size=(11,1)),],
                [sg.Text(expand_y=True)]], expand_y=True),
            sg.Column(layout=[
                [sg.Text('Year'),
                 sg.Input(f'{self.year}', key='-calyear-', width=5),
                 sg.Text('Month'),
                 sg.Input(f'{self.month}',key='-calmonth-', width=3),
                 sg.Text('Num of month'),
                 sg.Combo(['1','2','3','6','9','12'], key='-calmulti-',
                          width=3, default_value=f'{self.multi}',
                          readonly=True),],
                [sg.Checkbox('WeekEnd', key='-calwend-',
                             default=(self.wend==1)),
                 sg.Checkbox('Holiday', key='-calholi-',
                             default=(self.holi==1)),
                 sg.Checkbox('Vertical', key='-caltate-',
                             default=(self.tate==1)),]
                ]),
            ]


class TextP:
    def __init__(self, preserv):
        if not 'text' in preserv.keys():
            preserv['text'] = {}
        ps = preserv['text']
        self.msg1 = ps.get('msg1$', '')
        self.msg2 = ps.get('msg2$', '')
        self.effect = ps.get('effect', 0)
        self.stack = ps.get('stack', 0)
        self.upper = ps.get('upper', 0)

    def to_dict(self, preserv=None):
        retv = {
            'msg1$': self.msg1,
            'msg2$': self.msg2,
            'effect': self.effect,
            'stack': self.stack,
            'upper': self.upper,
            }
        if preserv:
            preserv =  retv
        return retv

    def sub_layout(self, activate=False):
        return [
            sg.Column(size=(120,40), layout=[
                [sg.Radio('', group_id='-shpg-', default=activate,
                     key='-shptxt-', enable_events=True),
                 sg.Text('Text', size=(11,1)),],
                [sg.Text(expand_y=True)]], expand_y=True),
            sg.Column([
                [sg.Text('Line 1'),
                 sg.Input(self.msg1, key='-txtmsg1$-', width=30),],
                [sg.Text('Line 2'),
                 sg.Input(self.msg2, key='-txtmsg2$-', width=30),],
                [sg.Combo(T_FX, key='-t_efx-', readonly=True,
                          default_value=T_FX[self.effect], width=12),
                 sg.Text('Stack'),
                 sg.Input(self.stack, key='-txtstack-', width=3),
                 sg.Text('Upper'),
                 sg.Input(self.upper, key='-txtupper-', width=3),
                 sg.Text(expand_x=True)
                 ]
                ]),
            ]


class LoremP:
    def __init__(self, preserv):
        if not 'lorem' in preserv.keys():
            preserv['lorem'] = {}
        ps = preserv['lorem']
        self.width = ps.get('width', 30)
        self.fname = ps.get('path', '')
        self.lmax = ps.get('lmax', '')
        self.ensp = ps.get('ensp', '')

    def to_dict(self, preserv=None):
        retv = {
            'width': self.width,
            'path': self.fname,
            'lmax': self.lmax,
            'ensp': self.ensp,
            }
        if preserv:
            preserv =  retv
        return retv

    def sub_layout(self, activate=False):
        return [
            sg.Column(size=(120,40), layout=[
                [sg.Radio('', group_id='-shpg-', default=activate,
                     key='-shplor-', enable_events=True),
                 sg.Text('LoremIpsum', size=(11,1)),],
                [sg.Text(expand_y=True)]], expand_y=True),
            sg.Column(layout=[
                [sg.Text('Width'),
                 sg.Input(f'{self.width}',key='-lorwidth-', width=3),
                 sg.Text('MaxL'),
                 sg.Input(f'{self.lmax} ',key='-lorlmax-', width=3),
                 sg.Checkbox('Space', key='-lorensp-',
                             default=(self.ensp==1)),
                 sg.Text(expand_x=True),],
                [sg.Checkbox('', key='-lfflg-',
                             default=(self.fname != '')),
                 sg.Text('File name'),
                 sg.Input(f'{self.fname} ',key='-lfpath-', expand_x=True),
                 sg.Button('...', key='-lfopen-'),
                 sg.Text(expand_x=True)]
                ], expand_x=True)
            ]
                

# --------------------
# 保存パラメータがあれば返す
def prevset(name, funcname, default=None, lo=None, hi=None):
    retv = impose_preserv.get(funcname, {}).get(name, default)
    
    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)
    
    return retv

# 不揮発パラメータ保存
def storehist(name, funcname, value):
    if impose_preserv.get(funcname,None) is None:
        impose_preserv[funcname] = {}
    impose_preserv[funcname][name] = value

    return


# --------------------
# フォント管理
font_data_cache = {}   # ZIP展開済み bytes
font_info_cache = {}   # フォント情報

# fontファイルのリストを取得する
def list_fonts(font_dir):
    fonts = []

    for file in os.listdir(font_dir):
        if file.lower().endswith(FONT_EXT):
            if file in ExceptList:
                continue
            fonts.append((os.path.join(font_dir,file), None))

        elif file.lower().endswith(".zip"):
            zipname = os.path.join(font_dir, file)
            try:
                with zipfile.ZipFile(zipname) as z:
                    for name in z.namelist():
                        if name.lower().endswith(FONT_EXT):
                            if name in ExceptList:
                                continue
                            fonts.append((zipname,name))
            except Exception:
                continue
    return sorted(fonts)


# fontを展開する
def open_font_source(source):
    path, inner = source

    if inner is None:
        return path

    key = (path, inner)

    if key not in font_data_cache:
        try:
            with zipfile.ZipFile(path) as z:
                font_data_cache[key] = z.read(inner)
        except Exception as e:
            print(f'Skipped {path} / {inner} as {e}')
            return path

    return io.BytesIO(font_data_cache[key])


# fontファイル名(base)の取り出し(未使用)
def basenm(source):
    if isinstance(source, str):
        return pa.basename(source)
    path, inner = source
    if inner:
        return pa.basename(inner)
    return pa.basename(path)
    

# fontの情報を返す
def get_font_info(source, textsize=48):
    """TTF/OTF/TTC の内部名とスタイルを返す。非対応なら None。
    戻り値: [(index, family, jp_family, style), ...]
    """
    if source in font_info_cache:
        return font_info_cache[source]

    faces = []
    index = 0

    while True:
        try:
            # PIL でフォントを開く
            font = ImageFont.truetype(open_font_source(source), textsize, index=index)
            family, style = font.getname()

            # nameID=1 の日本語名を取得
            try:
                tt = TTFont(open_font_source(source), fontNumber=index)
                jp_family = None
                fallback = None

                for rec in tt["name"].names:
                    if rec.nameID != 1:
                        continue
                    try:
                        name = rec.toUnicode()
                    except Exception:
                        continue

                    fallback = fallback or name
                    if (rec.platformID, rec.langID) in ((3, 0x0411), (0, 0)):
                        jp_family = name
                        break

                jp_family = jp_family or fallback or family

            except Exception:
                jp_family = family

            faces.append((index, family, jp_family, style))
            index += 1

        except OSError:
            break

    font_info_cache[source] = faces or None
    
    return font_info_cache[source]


# fontlistの再取得
def make_font_dic(directory):
    global font_data_cache, font_info_cache
    font_data_cache = {}   # data_cache クリア
    font_info_cache = {}   # フォント情報 クリア

    fonts = list_fonts(directory)
    fflist = []
    for source in fonts:
        info = get_font_info(source)
        if info is None:
            #print(f'Purge {source}.')
            continue
        for ff in info:
            idx, family, jp_family, face = ff
            fflist.append([jp_family, face, family, source, idx])
    fflist = sorted(fflist)

    font_key = []
    font_dic = {}
    for fontface in fflist:
        key = f'{fontface[0]}|{fontface[1]}'
        font_dic[key] = fontface
        font_key.append(key)

    return font_key, font_dic


# textを指定fontでビットマップに書き出す
def text_image(text, source, index=0, size=48, color=255,
               enable_space=False):
    try:
        font = ImageFont.truetype(open_font_source(source), size,
                                  index=index)
    except (OSError, ValueError, IOError):
        font = ImageFont.load_default()
        
    img = Image.new('L',(1,1))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0,0), text, font=font)

    temp_w = bbox[2]-bbox[0] + 1
    temp_h = (bbox[3]-bbox[1])*3

    if temp_w * temp_h == 0:
        return Image.new('L', (1, 1), 0)

    img = Image.new('L', (temp_w, temp_h), 0)
    draw = ImageDraw.Draw(img)

    draw.text((0, temp_h//2), text, font=font, fill=color)

    if enable_space:
        sp = font.getlength(' ')
        w = sp*text.count(' ') + font.getlength(text.lstrip(' '))
        bb = img.getbbox()
        x1,y1,x2,y2 = bb if bb is not None else (0,0,1,1) 
        img = img.crop((0, y1, w, y2))
    else:
        bb = img.getbbox()
        x1,y1,x2,y2 = bb if bb is not None else (0,0,1,1) 
        img = img.crop((x1, y1, x2, y2))

    return img  # was ImageTk.PhotoImage(img)


# --------------------
# マスク生成
# --------------------
# カレンダー (引数はpreserv経由)
def calendar_mask():
    # calendar param
    calendar_info = CalendarP(impose_preserv)
    year = calendar_info.year
    month = calendar_info.month
    multi = calendar_info.multi
    weekend = calendar_info.wend == 1
    holiflag = calendar_info.holi == 1
    tate = calendar_info.tate == 1

    # font param
    fonts = FontsetP(impose_preserv['fontset'])
    fontex = FontexP(impose_preserv['fontex'])
    common = CommonP(impose_preserv['common'])
    
    fkey = fonts.key
    fdic = fonts.font_dic
    size = fontex.size
    source = fdic[fkey][3]
    index = fdic[fkey][4]
    # print(fkey, fdic[fkey])  #####
    # print(impose_preserv['calendar'], '\n', year, month, holiflag)
    lspc = common.lspc
    spc = int(lspc*size)

    if 0 < multi < 4:
        # print('caller', year, month, multi)
        if tate and multi > 1:
            calimg = multi_calendar(year, month, 1, source, index, size,
                                    weekend=weekend, holiday=holiflag)
            for i in range(multi-1):
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                addimg = multi_calendar(year, month, 1, source, index, size,
                                        weekend=weekend, holiday=holiflag)
                w1,h1 = calimg.size
                w2,h2 = addimg.size
                newimg = Image.new('L', (max(w1,w2), h1+h2+spc), 0)
                newimg.paste(calimg, (0,0))
                newimg.paste(addimg, (0,h1+spc))
                calimg = newimg
        else:
            calimg = multi_calendar(year, month, multi, source, index, size,
                                    weekend=weekend, holiday=holiflag)
    elif 3 < multi < 13:

        wi = int(multi-0.5) // 3
        #wi = -(-multi // 3)
        calimg = multi_calendar(year, month, 3, source, index, size,
                                weekend=weekend, holiday=holiflag)
        for j in range(wi):
            month += 3
            if month > 12:
                month = month % 12
                year += 1
            sur = min(multi - (j+1)*3, 3)
            # print('add', year, month, sur, 'wi=', j)
            addimg = multi_calendar(year, month, sur, source, index, size,
                                weekend=weekend, holiday=holiflag)
            w1,h1 = calimg.size
            w2,h2 = addimg.size
            newimg = Image.new('L', (max(w1,w2), h1+h2+spc), 0)
            newimg.paste(calimg, (0,0))
            newimg.paste(addimg, (0,h1+spc))
            calimg = newimg
    else:
        calimg = monthly_calendar(year, month, source, index, size,
                     weekend=True, holiday=True)

    return calimg.crop(calimg.getbbox())


# 複数月横並び生成
def multi_calendar(year, month, num, fontsrc, index, size,
                   weekend=True, holiday=True):
    """numカ月分の横並びカレンダーユニット"""
    common = CommonP(impose_preserv['common'])
    dspc = common.spc
    spc = int(dspc*size)
    
    calimg = monthly_calendar(year, month, fontsrc, index, size,
                 weekend, holiday)

    for mm in range(1,num):
        month += 1
        if month > 12:
            month = 1
            year += 1
        addimg = monthly_calendar(year, month, fontsrc, index, size,
                                  weekend, holiday)
        w1,h1 = calimg.size
        w2,h2 = addimg.size
        newimg = Image.new('L', (w1+w2+spc, max(h1,h2)), 0)
        newimg.paste(calimg, (0,0))
        newimg.paste(addimg, (w1+spc,0))
        calimg = newimg
            
    return calimg


# 1 month
def monthly_calendar(year, month, fontsrc, index, size,
                     weekend=True, holiday=True):
    """1カ月分のカレンダーユニット"""
    fontex = FontexP(impose_preserv['fontex'])
    common = CommonP(impose_preserv['common'])

    body = calendar_body(year, month)
    if holiday:
        holidays = holiday_map(year)[month-1]
    else:
        holidays = []

    # test_cell
    tim = text_image(' 39', fontsrc, index=index, size=size, color=WDAY_INT)
    std_w = tim.width
    std_h = tim.height
    std_w = int(std_w * common.spc)
    std_h = int(std_h * common.lspc)
    hdr = text_image(f'{year}/{month}', fontsrc, index=index,
                     size=int(size*1.2), color=WDAY_INT)
    hdr_w, hdr_h = hdr.size

    if fontex.grad == 1:  # gradation linear
        maskhdr = linear_line_mask(hdr_w, hdr_h, fontex.mid)
        maskpat = linear_line_mask(std_w*7, std_h, fontex.mid)
    elif fontex.grad == 2:  # gradation stripe line
        maskhdr = stripe_line_mask(hdr_w, hdr_h, fontex.mid)
        maskpat = stripe_line_mask(std_w*7, std_h, fontex.mid)
    else:
        maskhdr = Image.new('L', (hdr_w, hdr_h), 255)
        maskpat = Image.new('L', (std_w*7, std_h), 255)
        
    calimg = Image.new('L', (std_w*7, int(std_h*6.5)+hdr_h), 0)
    calimg.paste(maskhdr, ((std_w*7-hdr_w)//2,0), hdr)


    for j, line in enumerate(body):
        lpat = Image.new('L', (std_w*7, std_h), 0)
        for i, day in enumerate(line):
            if day is None:
                continue
            color = WDAY_INT
            if weekend and i in (0, 6):
                color = fontex.half
            elif holiday and day in holidays:
                color = fontex.half
            tim = text_image(f'{day}', fontsrc, index=index, size=size,
                             color=color)
            pos = ((i+1)*std_w-tim.width, 0)
            lpat.paste(tim, pos, tim)

        calimg.paste(maskpat, (0, int((j+0.5)*std_h)+hdr_h), lpat)

    return calimg    
    
# カレンダー文字列生成
def calendar_body(year, month, firstday=calendar.SUNDAY):
    """カレンダー配列 firstday変更可"""
    
    # calendar.setfirstweekday(firstday)
    # cal = calendar.monthcalendar(year, month)
    cal = calendar.Calendar(firstweekday=firstday)
    cal = cal.monthdayscalendar(year, month)
    cal = [[d or None for d in week] for week in cal]

    return cal

# 春分・秋分（祝日計算用近似式）
def shunbun(y):
    return int(20.8431 + 0.242194*(y-1980)) - (y-1980)//4

def shuubun(y):
    return int(23.2488 + 0.242194*(y-1980)) - (y-1980)//4

# 振替休日（既に祝日なら追加しない）
def furikae(date, holidays):
    if date.weekday() != 6:  # Sunday
        return
    next_day = date + datetime.timedelta(days=1)

    # 連続して祝日ならさらに翌日へ
    while next_day in holidays:
        next_day += datetime.timedelta(days=1)

    holidays.append(next_day)

# 国民の休日（祝日に挟まれた平日）
def kokumin_no_kyujitsu(holidays):
    extra = []
    hs = set(holidays)

    for h in holidays:
        next_day = h + datetime.timedelta(days=1)
        # 祝日 → 平日 → 祝日 の平日を追加
        if (next_day.weekday() < 5) and (next_day not in hs):
            if (h in hs) and ((next_day + datetime.timedelta(days=1)) in hs):
                extra.append(next_day)

    return extra

# 祝日リスト holiday_map(year)[month-1][] でその月の祝日リスト(振替込み)を取得
def holiday_map(year):
    holidays = []

    # 固定祝日
    for sp in SP_HOLIDAY:
        holidays.append(datetime.date(year, *sp))

    # 春分・秋分
    holidays.append(datetime.date(year, 3, shunbun(year)))
    holidays.append(datetime.date(year, 9, shuubun(year)))

    # ハッピーマンデー制度
    def nth_monday(month, n):
        d = datetime.date(year, month, 1)
        while d.weekday() != 0:  # Monday
            d += datetime.timedelta(days=1)
        return d + datetime.timedelta(days=7*(n-1))

    for hm in HM_HOLIDAY:
        holidays.append(nth_monday(*hm))


    # 国民の休日
    holidays += kokumin_no_kyujitsu(holidays)

    # 振替休日
    base = holidays.copy()
    for h in base:
        furikae(h, holidays)

    # 重複除去
    holidays = sorted(set(holidays))

    # 月毎の配列に変換
    holiday_map = [[] for _ in range(12)]
    for d in holidays:
        holiday_map[d.month - 1].append(d.day)

    return holiday_map


# ----------
# Text
def text_mask():
    text_info = TextP(impose_preserv)
    line1 = text_info.msg1
    line2 = text_info.msg2
    lines = [line1, line2]

    # font param
    fonts = FontsetP(impose_preserv['fontset'])
    fkey = fonts.key
    fdic = fonts.font_dic
    source = fdic[fkey][3]
    index = fdic[fkey][4]

    fontex = FontexP(impose_preserv['fontex'])
    common = CommonP(impose_preserv['common'])
    fsize = fontex.size
    lspc = common.lspc
    llspc = int(fsize * lspc)
    grad = fontex.grad
    mid = fontex.mid
    pos = common.pos
    h_align = pos % 3  # 0:left 1:center 2:right

    limgs = []
    lhtotal = 0
    spcmax = 0
    maxw = 1
    for ltxt in lines:
        if ltxt == '' or ltxt is None:
            if limgs == []:
                ltxt = ' '
            else:
                continue
        # print(f'{ltxt},{ord(ltxt[0])}')
        limg = text_image(ltxt, source, index=index,
                          size=fsize, color=WDAY_INT)
        dimg = limg.crop(limg.getbbox())
        w1,h1 = limg.size
        if w1 == 0:
            dimg = Image.new('L',(10,fsize//4),0)
            
        if grad == 1:  # gradation linear
            maskpat = linear_line_mask(w1, h1, mid)
        elif grad == 2:  # gradation stripe line
            maskpat = stripe_line_mask(w1, h1, mid)
        else:
            maskpat = Image.new('L', (w1, h1), 255)

        img = Image.new('L', (w1, h1), 0)
        img.paste(maskpat, (0,0), dimg)

        limgs.append(img)
        lhtotal += max(h1+1, llspc)
        spcmax = max(1, llspc-h1)
        #lhlist.append(h1)
        maxw = max(maxw, w1)

    #totalh = sum(lhlist)+(len(limgs)-1)*spc
    #img = Image.new('L', (maxw, totalh), 0)

    img = Image.new('L', (maxw, lhtotal), 0)
    y = 0
    for l in limgs:
        lw, lh = l.size
        if h_align == 2:
            x = maxw - lw
        elif h_align == 1:
            x = int((maxw - lw)/2)
        else:
            x = 0
        img.paste(l, (x,y))
        y = y+max(lh+1,llspc)

    img = img.crop(img.getbbox())
    effect = text_info.effect
    if effect == 1:
        stack = text_info.stack
        img = layered_np(img, stack, thickness=11)
        img = img.crop(img.getbbox())
        storehist('stack', 'text', stack)
    if effect == 2:
        lower = text_info.stack
        upper = text_info.upper
        img, img2 = stacker(img, upper, lower, spcmax)
        return img, img2
    
    return img, None  # mask(shadow enable), mask2(non shadow)


# layered outline typography
def layered_np(img, step, thickness=8):
    """layeredのNumPy高速版"""
    iw, ih = img.size

    # layered() で最初に作られる thick() の幅
    max_width = (step + 1) * thickness
    if max_width % 2 == 0:
        max_width += 1

    # 最外周のthick()と同じサイズのキャンバスを作る
    bw = iw + max_width * 2
    bh = ih + max_width * 2

    src = np.asarray(img, dtype=np.uint8)

    # 元画像を最大キャンバスの中央へ配置
    base = np.zeros((bh, bw), dtype=np.uint8)
    base[
        max_width:max_width + ih,
        max_width:max_width + iw
    ] = src

    # FIND_EDGES は一度だけ実行
    edge_img = Image.fromarray(base, mode='L').filter(ImageFilter.FIND_EDGES)
    edge = np.asarray(edge_img, dtype=np.uint8)

    result = np.zeros((bh, bw), dtype=np.uint8)
    for i in range(step):
        width = (step - i) * thickness

        if width % 2 == 0:
            width += 1

        lw = iw + width * 2 # thick(img, width)サイズ
        lh = ih + width * 2
        ix = (bw - lw) // 2
        iy = (bh - lh) // 2

        # FIND_EDGES済み画像から対応部分取得
        e = edge[iy:iy + lh, ix:ix + lw]

        contour = _maxfilter_np(e, width)
        layer = np.maximum(
            base[iy:iy + lh, ix:ix + lw],
            contour
        )
        result[iy:iy + lh, ix:ix + lw] ^= layer  # XOR

    ix = (bw - iw) // 2
    iy = (bh - ih) // 2
    result[iy:iy + ih, ix:ix + iw] ^= src  # 元画像XOR

    return Image.fromarray(result, mode='L')
        

# 水平方向maxfilter
def _maxfilter_1d_horizontal(a, size):
    if size <= 1:
        return a

    r = size // 2
    p = np.pad(a, ((0, 0), (r, r)), mode='constant')
    h, w = p.shape
    nb = (w + size - 1) // size
    ww = nb * size

    if ww != w:
        p = np.pad(p, ((0, 0), (0, ww - w)), mode='constant')

    q = p.reshape(h, nb, size)

    left = np.maximum.accumulate(q, axis=2)
    right = np.maximum.accumulate(q[..., ::-1],axis=2)[..., ::-1]

    left = left.reshape(h, ww)
    right = right.reshape(h, ww)

    need = size - 1 + a.shape[1]
    if left.shape[1] < need:
        left = np.pad(left, ((0, 0), (0, need - left.shape[1])), mode='edge')

    r = right[:, :a.shape[1]]
    l = left[:, size - 1:size - 1 + a.shape[1]]

    return np.maximum(r, l)


# 垂直方向maxfilter
def _maxfilter_1d_vertical(a, size):
    if size <= 1:
        return a

    r = size // 2
    p = np.pad(a, ((r, r), (0, 0)), mode='constant')
    h, w = p.shape
    nb = (h + size - 1) // size
    hh = nb * size

    if hh != h:
        p = np.pad(p, ((0, hh - h), (0, 0)), mode='constant')

    q = p.reshape(nb, size, w)

    left = np.maximum.accumulate(q, axis=1)
    right = np.maximum.accumulate(q[:, ::-1, :], axis=1)[:, ::-1, :]

    left = left.reshape(hh, w)
    right = right.reshape(hh, w)

    try:
        return np.maximum(right[:a.shape[0], :],
                          left[size:size+a.shape[0], :])
    except ValueError:
        return a

# MaxFilterをnumpyで代替、高速化
def _maxfilter_np(img, size):
    """PIL MaxFilter相当の高速NumPy版。"""
    if size <= 1:
        return img
    if size % 2 == 0:
        size += 1
    tmp = _maxfilter_1d_horizontal(img, size)

    return _maxfilter_1d_vertical(tmp, size)


# stacked typography
def stacker(img, upper, lower, gap=2):
    holimg = hollow(img, 3)
    hw, hh = holimg.size
    solimg = thick(img, 3)
    sw, sh = solimg.size
    fh = (hh+gap)*(upper+lower)+sh+gap
    fw = max(hw, sw)

    hol_np = np.array(holimg)
    sep = np.zeros((gap,hw),dtype=np.uint8)
    hol2 = np.vstack([hol_np, sep])

    uppart = np.tile(hol2, (upper, 1))
    lopart = np.tile(hol2, (lower, 1))
    sol_np = np.array(solimg)
    
    back = np.zeros((fh, fw), dtype=np.uint8)
    back[0:(hh+gap)*upper] = uppart
    back[(hh+gap)*upper+sh+gap:fh] = lopart
    back = Image.fromarray(back).convert('L')

    out = np.zeros((fh, fw), dtype=np.uint8)
    out[(hh+gap)*upper:(hh+gap)*upper+sh] = sol_np
    out = Image.fromarray(out).convert('L')
    
    return out, back    
    

# ----------
# Lorem Ipsum
def lorem_mask():
    lorem_info = LoremP(impose_preserv)
    if lorem_info.fname != '':
        buf = read_force_jap(lorem_info.fname)
        lines = []
        for eachln in buf:
            wrapped = textwrap.wrap(eachln, lorem_info.width)
            for wrapln in wrapped:
                lines.append(wrapln)
        
        if len(lines) == 0:
            lines = textwrap.wrap(LOREM, lorem_info.width)
    else:
        lines = textwrap.wrap(LOREM, lorem_info.width)
    maxlines = lorem_info.lmax
    ptr = np.random.randint(len(lines)-maxlines) if len(lines)>maxlines else 0
    lines = lines[ptr:ptr+maxlines]
    ensp = (lorem_info.ensp == 1)
    
    # font param
    fonts = FontsetP(impose_preserv['fontset'])
    fkey = fonts.key
    fdic = fonts.font_dic
    source = fdic[fkey][3]
    index = fdic[fkey][4]

    fontex = FontexP(impose_preserv['fontex'])
    size = fontex.size
    grad = fontex.grad
    mid = fontex.mid

    common = CommonP(impose_preserv['common'])
    lspc = common.lspc
    pos = common.pos
    h_align = pos % 3  # 0:left 1:center 2:right

    limgs = []
    maxw = 0
    maxh = 0
    for l in lines:
        ltmp = text_image(l, source, index=index, size=size,
                          color=WDAY_INT, enable_space=ensp)
        lw, lh = ltmp.size
        if grad == 1:  # gradation linear
            maskpat = linear_line_mask(lw, lh, mid)
        elif grad == 2:  # gradation stripe line
            maskpat = stripe_line_mask(lw, lh, mid)
        else:
            maskpat = Image.new('L', (lw, lh), 255)
        limg = Image.new('L', (lw, lh), 0)
        limg.paste(maskpat, (0,0), ltmp)
        if not ensp:
            limg = limg.crop(limg.getbbox())
        lw, lh = limg.size
        maxw = max(maxw, lw)
        maxh += lh
        limgs.append(limg)
    maxh = int(maxh*lspc - (lspc-1)*lh)
    
    img = Image.new('L', (maxw, maxh), 0)
    y = 0
    for lim in limgs:
        lw, lh = lim.size
        if h_align == 2:
            x = maxw - lw
        elif h_align == 1:
            x = int((maxw - lw)/2)
        else:
            x = 0
        if ensp:
            x = 0
            
        img.paste(lim, (x,y), lim)
        y = y+int(lh*lspc)

    if not ensp:
        img = img.crop(img.getbbox()) 
    return img


# エンコーディングを判定してテキスト読込
def read_force_jap(path):
    try:  # まずUTF-8を試す
        with open(path, 'r', encoding='utf-8') as f:
            return [line.expandtabs(4) for line in f.read().splitlines()]
    except UnicodeDecodeError:
        pass

    try:  # UTF-8がダメなら SJIS(cp932)
        with open(path, 'r', encoding='cp932') as f:
            return f.read().splitlines()
    except UnicodeDecodeError:  # SJISでもない
        pass

    with open(path, 'rb') as f:
        buf = f.read(8192)  # なんちゃって表示なので頭8kしか読み込まない
    return hexdump(buf)


# バイナリデータをhexdumpテキストに変換
def hexdump(raw: bytes):
    lines = []
    length = len(raw)

    for offset in range(0, length, 16):
        chunk = raw[offset:offset+16]

        # --- 16進部分（4バイト区切り） ---
        hex_groups = []
        for i in range(0, 16, 4):
            part = chunk[i:i+4]
            hex_part = ' '.join(f'{b:02X}' for b in part)
            if len(part) < 4:
                hex_part += ' ' * (3 * (4 - len(part)))
            hex_groups.append(hex_part)

        hex_str = '-'.join(hex_groups)

        # 文字表示欄はASCII以外を'.'に
        ascii_part = ''.join(
            chr(b) if 32 <= b <= 126 else '.'
            for b in chunk
        )

        # --- 行を構築 ---
        line = f'{offset:08X}  {hex_str}  |{ascii_part}|'
        lines.append(line)

    return lines


# --------------------
# 行装飾
# --------------------
# 濃淡グラデーション
def linear_line_mask(width, height, pos=33):
    """リニアグラデーション(固定区間あり)"""
    h1 = int(height * pos / 100)
    h2 = height - h1
    start = 255
    stop = 128
    
    top = np.full((h1, width), start, dtype=np.uint8)
    bottom = np.linspace(start, stop, h2, dtype=np.uint8).reshape(h2, 1)
    bottom = np.repeat(bottom, width, axis=1)
    hm = np.concatenate([top, bottom], axis=0)
    
    return Image.fromarray(hm, mode='L')


# 線幅グラデーション
def stripe_line_mask(width, height, fade=30, pitch=10):
    """フェードストライプ pitch=分割数"""
    bandw = height // pitch  # 白黒セット幅
    fade_r = (100 - fade) / 100 #if fade < 60 else 0.4
    img = np.zeros((height, width), dtype=np.uint8)

    # 各セットの開始位置
    y = 0

    for i in range(pitch):
        # 線形補間で白黒幅を決定
        t = i / (pitch - 1)
        w_white = int(bandw * (1 - fade_r*t))
        w_black = bandw - w_white

        # 白黒ストライプを縦方向に描画
        # 白ストライプ
        img[y:y+w_white, :] = 255
        # 黒ストライプ
        img[y+w_white:y+bandw, :] = 0

        y += bandw

    return Image.fromarray(img, mode='L')


# thick
def thick(img, width=3):  # img.mode == 'L'
    if width % 2 == 0:
        width += 1
    iw,ih = img.size
    newimg = Image.new('L', (iw+width*2, ih+width*2), 0)
    newimg.paste(img, (width, width))
    base_np = np.array(newimg)
    
    contour = newimg.filter(ImageFilter.FIND_EDGES)
    if width > 1:
        contour = contour.filter(ImageFilter.MaxFilter(width))
    contour_np = np.array(contour)

    or_img = np.maximum(base_np, contour_np) 
    
    return Image.fromarray(or_img, mode="L")

# Hollow
def hollow(img, width=3):  # img.mode == 'L'
    if width % 2 == 0:
        width += 1
    iw,ih = img.size
    newimg = Image.new('L', (iw+width*2, ih+width*2), 0)
    newimg.paste(img, (width, width))
    contour = newimg.filter(ImageFilter.FIND_EDGES)
    if width > 1:
        contour = contour.filter(ImageFilter.MaxFilter(width))

    return contour


# ------------------------------------
# スーパーインポーズ本体
# ------------------------------------
def impose_mask(fgimg, mask_name, bgimg, W=None, H=None):
    """bgimg上にfgimgをmaskで切り出してスーパーを入れる"""
    # shift = 8   影のシフト量(pixel)
    # alpha = 40  影の透過度(0-255)
    # blur = 10   影のぼかし半径(pixel)
    shade = ShadeP(impose_preserv['shade'])
    scolor = tuple((shade.color[:3]+(0, 0, 0))[:3]+(shade.alpha,))

    if W is None or H is None:
        W, H = fgimg.size

    mask2 = None
    if mask_name == 'cal':
        mask = calendar_mask()
    elif mask_name == 'txt':
        mask, mask2 = text_mask()
    elif mask_name == 'lor':
        mask = lorem_mask()
    else:
        mask = Image.new('L', (1, 1), 0)

    mask = allocate_img(W, H, mask)

    # 影
    dx = shade.shift
    dy = shade.shift

    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    mask_np = np.array(mask)
    mask_np = (mask_np > 0).astype(np.uint8) *255
    shadow.paste(scolor, mask=Image.fromarray(mask_np))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shade.blur))

    # 影シフト
    shifted = Image.new('RGBA', (W, H))
    shifted.paste(shadow, (dx, dy))
    shadow = shifted

    # マスクで切り抜き
    if shade.enbri != 0.0:
        fgimg = adjust_brightness(fgimg, shade.enbri)

    result = bgimg.convert('RGBA')
    if mask2 is not None:
        mask2 = allocate_img(W, H, mask2)
        overlay = Image.new('RGBA', (W,H), scolor)
        overlay.putalpha(mask2)
        result = Image.alpha_composite(result, overlay)
    result = Image.alpha_composite(result, shadow)
        
    bg_np = np.array(result, dtype=np.float32)
    fg_np = np.array(fgimg.convert('RGBA'), dtype=np.float32)
    mask_np = np.array(mask, dtype=np.float32) / 255.0  # 0〜1

    # mask をアルファとして使う
    a = mask_np[..., None]  # (H,W,1)

    # アルファブレンド
    out = bg_np * (1 - a) + fg_np * a
    out = np.clip(out, 0, 255).astype(np.uint8)

    result = Image.fromarray(out, mode='RGBA')
    return result


# マスクの配置
def allocate_img(W,H, img):
    baseimg = Image.new('L', (W,H), 0)
    if img.mode != 'L':
        img = img.convert('L')

    iw, ih = img.size
    common = CommonP(impose_preserv['common'])
    xpad = common.xpad
    ypad = common.ypad
    imgpos = common.pos

    if (imgpos // 3) == 2:  # south
        iy = H - ih - ypad
    elif (imgpos // 3) == 1:  # center
        iy = (H - ih)//2
    else:  # north
        iy = ypad
    
    if (imgpos % 3) == 2:  # east
        ix = W - iw - xpad
    elif (imgpos % 3) == 1:  # center
        ix = (W - iw)//2
    else:  # west
        ix = xpad

    baseimg.paste(img, (ix, iy), img)
    # print(f'{imgpos} -> {ix},{iy}')

    return baseimg


# 文字テクスチャ
def plain_image(W, H, base=(207,207,207), baseadd=(48,48,48), swirl=None):
    c = []
    for i in range(3):
        c.append(clip8(base[i]))
        if c[i] < 255 and baseadd[i] > 0:
            c[i] = clip8(np.random.randint(c[i], base[i]+baseadd[i]))
    img = Image.new('RGBA', (W, H), color=tuple(c))

    if swirl is None:
        return img

    fg = np.array(img, dtype=np.float32)
    factor = swirl_marble(W,H, swirl=swirl)
    res = (fg * factor[..., None]).astype(np.uint8)
        
    return Image.fromarray(res, mode='RGBA')

# うずまき
def swirl_marble(W, H, freq=10, swirl=13, wobble=3.3, contrast=0.04):
    xs = np.linspace(-1, 1, W, endpoint=False)
    ys = np.linspace(-1, 1, H, endpoint=False)
    X, Y = np.meshgrid(xs, ys)

    # アスペクト比補正
    aspect = W / H
    if aspect > 1:
        Y = Y * aspect
    else:
        X = X / aspect

    rad = np.sqrt(X * X + Y * Y)
    phi = np.arctan2(Y, X)

    flow = (
        rad * freq
        + phi * swirl
        + wobble * np.sin(phi * 5 + rad * 8)
    )

    base = (1.0 + contrast * np.sin(flow)).astype(np.float32)
    return np.clip(base, 0, 1)


# 明度変更補助
def srgb_to_linear(x, gamma):
    """numpy配列: sRGB(ガンマあり) → リニア変換"""
    x = x / 255.0
    base = np.maximum(x + 0.055, 0.0) / 1.055
    return np.where(x <= 0.04045, x / 12.92, base ** gamma)

def linear_to_srgb(x, gamma):
    """numpy配列: リニア → sRGB(ガンマあり)変換"""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x < 0.0031308, x * 12.92,
                    1.055 * (x ** (1/gamma)) - 0.055) * 255.0

# --- 明度加算（ガンマ込み） ---
def adjust_brightness(img, delta: float, gamma: float = 2.2):
    """PILイメージの明度をdelta(-255.0..255.0)加算
    (gamma=2.2(sRGB), 1.8(Mac68k), )"""
    
    arr = np.asarray(img).astype(np.float32)

    # RGB / RGBA 判定
    has_alpha = (arr.shape[-1] == 4)
    rgb = arr[..., :3]
    alpha = arr[..., 3] if has_alpha else None

    # 明度加算（linear 空間で行う）
    rgb_lin = srgb_to_linear(rgb, gamma)
    delta_lin = srgb_to_linear(np.array([abs(delta)], dtype=np.float32),
                               gamma)[0] * (delta/abs(delta))
    rgb_lin = rgb_lin + delta_lin

    # 再構成
    rgb_srgb = linear_to_srgb(rgb_lin, gamma)
    if has_alpha:
        out = np.dstack([rgb_srgb, alpha])
    else:
        out = rgb_srgb

    return Image.fromarray(out.astype(np.uint8))


# --------------------
# main
# --------------------
# GUIからパラメータを取得(バルク)
def scan_va(va, mask_name):
    pre = f'-{mask_name}'
    for paramname in va.keys():
        if paramname.startswith(pre):
            param = paramname[len(pre):-1]
            val = va[paramname]
            if param.endswith('$'):  # 文字列
                pass
            elif isinstance(val, bool):  # 論理値
                val = 1 if val else 0
            else:  # 数値
                val = stoi(val)
            # print(param, '=', val)
            storehist(param, Mask_Code[mask_name], val)
    return

# GUIからパラメータを取得(単発)
def getval(elemval, name, cat, default=None, lo=None, hi=None):
    """elementの値(文字列)を数値化して保存"""
    v = stoi(elemval, default, lo, hi)
    if v is not None:
        storehist(name, cat, v)
    return v


# ファイル名表示文字列長を調節
def strict_fname_len(fname, l):
    if l < 6:
        l = 6
    if len(fname) > l:
        right = min(len(basenm(fname)) + 1, l-4)
        left = l - right - 2
        retv = fname[:left]+'..'+fname[-right:]
    else:
        retv = fname
    return retv


# FGをファイルから取得
def read_file_image(wn, fgsel):
    src_path = fdi.get_openfile('', filetypes=Image_Files)
    if pa.exists(src_path):
        fgsel.path = src_path
        fname = pa.basename(src_path)
        wn['-fn1-'].update(fname)
        wn['-fgsel-'].update(FgMenu[2])  # 'File'
        # bgmode = None
    
        file_image = Image.open(src_path).convert('RGBA')
    else:
        file_image = None
    fdi.flush_ev(wn)

    return file_image



# FontDir探索スレッド完了処理
def retrieve_fontdir(done_flag, fpath):
    fkeys, fdic = make_font_dic(fpath)

    done_flag['fkeys'] = fkeys
    done_flag['fdic'] = fdic
    done_flag['done'] = True

# 非同期処理中に不活性化させるwidget
Dis_List = ['-fdsl-', '-fdfl-','-cgrad-', '-cpos-', '-flst-',   
            '-shpcal-', '-shptxt-', '-shplor-',
            '-bgsel-', '-swap-', '-bgc-', '-file1-',
            '-test-','-ok-','-can-']

# メインエントリ
def efx(image, p: Param):
    global impose_preserv, Font_Dic
    dcpy = copy.deepcopy(impose_preserv)
    preview_size = Preview_Size
    
    W, H = p.width, p.height
    init_fgimg = image if image is not None else plain_image(W,H, swirl=6)    
    try:
        if init_fgimg.size != (W,H):
            init_fgimg = init_fgimg.resize((W,H), resample=Image.LANCZOS)
    except AttributeError:
        pass
    file_image = None

    # default Bacic Params
    shade = ShadeP(impose_preserv['shade'])
    sfgc, sbgc = bg_and_font(shade.color)

    fgsel = FgselP(impose_preserv['fgsel'])
    fgc, bgc = bg_and_font(fgsel.color)
    init_pimg = plain_image(W,H, base=fgsel.color,
                            baseadd=tuple(fgsel.jit for _ in range(3)))

    init_bgimg = p.bg(W,H)
    bgimg = init_pimg
    bgfile = FgInd[3]
    bgmode = FgMenu[3]

    
    fonts = FontsetP(impose_preserv['fontset'])
    fdic = fonts.font_dic
    fkeys = list(fdic.keys())
    # fdic["jp_family|face"] = [jp_family, face, family, source, idx]

    fontex = FontexP(impose_preserv['fontex'])
    common = CommonP(impose_preserv['common'])

    calendar_info = CalendarP(impose_preserv)
    t = datetime.date.today()
    calendar_info.year = t.year
    calendar_info.month = t.month

    text_info = TextP(impose_preserv)
    txteffect = text_info.effect

    lorem_info = LoremP(impose_preserv)
    
    # UI panel
    flheight = FontList_Size - (3 if Cramped else 0) 
    fontset = [[sg.Text(f'Fonts ({strict_fname_len(fonts.font_dir,18)})',
                        key='-fdir-'),
                sg.Button(' ... ', key='-fdsl-', background_color='#ddddff'),
                sg.Button('Sys', key='-fdfl-'),],
               [sg.Listbox(fkeys, key='-flst-', size=(35, flheight),
                           enable_events=True),],
               [],
               [sg.Text(fonts.key, key='-falt-', text_color='black'),],
               ]
    
    fontexblock = fontex.sub_layout()
    shadeset = shade.sub_layout()
    bgset = fgsel.sub_layout()
    commonset = common.sub_layout()
    
    calparam = calendar_info.sub_layout(activate=True)
    txtparam = text_info.sub_layout()
    lorparam = lorem_info.sub_layout()

    if Cramped:
        cal_lo = [[sg.Column(layout=fontset),
                   sg.Column(layout=[calparam,
                                     txtparam,
                                     fontexblock,])
                   ]]
    else:
        cal_lo = [[sg.Column(layout=fontset),
                   sg.Column(layout=[calparam,
                                     txtparam,
                                     lorparam,[],
                                     fontexblock,])
                   ]]

    buttonblock = [
        sg.Text(' ', expand_x=True, expand_y=True),
        sg.Button('Test', key='-test-'),
        sg.Button('Ok', key='-ok-', background_color='#ddffdd'),
        sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
        ]

    lo = [[sg.Frame(title='Superimpose', layout=cal_lo, relief='ridge',
                    expand_x=True)],
          [sg.Frame('Foreground', layout=bgset, relief='ridge',
                    expand_x=True)],
          [sg.Image(size=preview_size, key='-timg-'),
           sg.Column(layout=[[sg.Frame('Shading', layout=shadeset,
                                       relief='ridge', expand_x=True),],
                             [sg.Frame('Align Text', layout=commonset,
                                       relief='ridge', expand_x=True),],
                             buttonblock,], expand_x=True, expand_y=True ),
           ],
          ]
           
    src_path = None
    mask_name = 'cal'
    sample = impose_mask(bgimg, mask_name, init_fgimg, W, H)
   
    wn = sg.Window('Superimpose Texts', layout=lo)
    busy = False
    
    def blink_text(flag):
        if flag['done']:
            fdi.flush_ev(wn)
            wn.dispatch_event('-thread-done-')
            return

        current = wn['-falt-'].get()
        wn['-falt-'].update('' if current else 'Processing...')
        wn['-falt-'].update(text_color=Alert_Color)
        wn.refresh()

        wn['-falt-'].widget.after(300, blink_text, flag)
        # register and return

    def set_gui_disabled(disable=True, list=Dis_List):
        for key in list:
            try:
                wn[key].set_disabled(disable)
            except:
                pass
    
    while True:
        wn['-timg-'].update(data=sample)
        
        ev, va = wn.read()
        # print(ev, va)

        if busy and ev != '-thread-done-':
            print('.', end='')
            continue

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            sample = image
            impose_preserv = dcpy
            break
        elif ev == '-ok-':
            break
        elif  ev == '-fgsel-' and va['-fgsel-'] == FgMenu[2]:
            if file_image is None:
                image = read_file_image(wn, fgsel)
                if image is not None:
                    file_image = image
        elif ev == '-file1-':
            image = read_file_image(wn, fgsel)
            if image is not None:
                file_image = image
        elif ev == '-bgc-':
            base = to_rgb(sg.popup_color('Select Base Color',
                                         default_color=fgsel.color))
            if base is not None:
                fgsel.color = base
                fgc, bgc = bg_and_font(base)
                wn['-bgc-'].update(background_color=bgc, text_color=fgc)
                wn['-fgsel-'].update('Plain')
                bgmode = None
            fdi.flush_ev(wn)
        elif ev == '-scolor-':
            scolor = to_rgb(sg.popup_color('Select Shade Color',
                                       default_color=shade.color))
            if scolor is not None:
                sfgc, sbgc = bg_and_font(scolor)
                wn['-scolor-'].update(background_color=sbgc, text_color=sfgc)
                shade.color = scolor
            fdi.flush_ev(wn)
        elif ev == '-test-':
            bgmode = None
        elif ev == '-flst-':
            v = wn['-flst-'].get()
            if len(v) != 1:  # Listboxの値はlistで返る
                continue
            if v[0] in fonts.font_dic:
                fonts.key = v[0]
                wn['-falt-'].update(fonts.key)
        elif ev == '-fdsl-' or ev == '-fdfl-':
            if ev == '-fdfl-':
                fpath = SysFont_Dir
            else:
                fpath = fdi.get_folder(init_dir=fonts.font_dir)
            if pa.exists(fpath):
                busy = True
                set_gui_disabled(True)
                flag = {'done': False}
                threading.Thread(target=retrieve_fontdir, args=(flag, fpath),
                                 daemon=True).start()
                blink_text(flag)
            continue
        elif ev == '-thread-done-':
            busy = False
            wn['-falt-'].update('', text_color='black')
            
            nfkeys = flag['fkeys']
            nfdic = flag['fdic']
            if len(nfkeys) > 0:
                fkeys = nfkeys
                fonts.font_dic = nfdic
                fonts.font_dir = fpath
                fonts.key = fkeys[0]
                set_gui_disabled(False, ['-fdir-','-flst-'])
                wn['-fdir-'].update(
                    f'Fonts ({strict_fname_len(fpath,18)})')
                wn['-flst-'].update(values=fkeys)
                wn['-falt-'].update(fonts.key)
            wn.refresh()
            fdi.flush_ev(wn)
            set_gui_disabled(False)
            flag['done'] = True
        elif ev.startswith('-shp'):
            mask_name = ev[4:-1]
        elif ev == '-lfopen-':
            src_path = fdi.get_openfile(lorem_info.fname,
                                        filetypes=[('Any','*.*'),])
            if pa.exists(src_path):
                if pa.getsize(src_path) > 0:
                    lorem_info.fname = src_path
                    wn['-lfpath-'].update(pa.basename(src_path))
            fdi.flush_ev(wn)
            wn['-lfflg-'].update(True)
        elif ev == '-lfflg-':
            if va['-lfflg-'] == True:
                if va['-lfpath-'] == '':
                    wn['-lfflg-'].update(False)
            else:
                wn['-lfpath-'].update('')
                lorem_info.fname = ''

        impose_preserv['fontset'] = fonts.to_dict()
        fontex.scan(wn)
        impose_preserv['fontex'] = fontex.to_dict()
        shade.scan(wn)
        impose_preserv['shade'] = shade.to_dict()
        common.scan(wn)
        impose_preserv['common'] = common.to_dict()

        scan_va(va, mask_name)

        storehist('path', 'lorem', lorem_info.fname)            
        v = va['-t_efx-']
        if v is not None:
            storehist('effect', 'text', T_FX.index(v))

        bgimg = fgsel.scan(wn, init_bgimg)
        impose_preserv['fgsel'] = fgsel.to_dict()
        
        if isinstance(bgimg, int):
            if bgimg == 0:
                bgimg = init_fgimg
            elif bgimg == 1:
                bgimg = init_bgimg
            elif bgimg == 2:
                if file_image is None:  # fallback, will not touched
                    print('NO FILE IMAGE')
                    bgimg = init_fgimg
                bgimg = file_image
            else:
                bgimg = plain_image(W, H, base=fgsel.color,
                                    baseadd=tuple(fgsel.jit for _ in range(3)))
              
        if fgsel.swap:
              fg = init_fgimg
              bg = bgimg
        else:
              bg = init_fgimg
              fg = bgimg

        sample = impose_mask(fg, mask_name, bg, W, H)
        wn['-timg-'].update(sample)

        wn.refresh()

    wn.close()

    return sample


if __name__ == "__main__":
    p = Param()
    p.width, p.height = (1920,1080)
    
    img = efx(None, p)
    if img is not None:
        img.show()

    fk,fd = make_font_dic(Font_Dir)
    storehist('key', 'fontset', fk[0])
    storehist('font_dir', 'fontset', Font_Dir)
    #storehist('fontdic', 'font', fd)
    Font_Dic = fd
    storehist('msg1$', 'text','TestTest Test')
