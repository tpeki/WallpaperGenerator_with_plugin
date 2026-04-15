'''wallpaper : 壁紙用シンプル画像生成
v1.0.0 2025/12/26 stagger-tiled-stripeのパターン生成スクリプト(単発)版
v2.0.0 2025/12/29 モジュール構成にして、複数のパターン作成に対応
v2.0.1 2026/01/01 コマンドラインオプションを追加 (.pywだとヘルプが出ない)
v2.0.2 2026/01/03 色選択部品の挙動を修正。ペンローズタイルモジュール追加
v2.0.3 2026/01/05 Save asダイアログを表示するようにした。
                  CLIの色指定修正(setattrではstrのまま設定してしまう)

協力：Google Gemini; モジュールのアルゴリズム作成支援(numpy使う手があったなんて)
謝辞：Kujira Handさん; TkEasyGUIがなければGUIアプリにしようと思いませんでした
      Microsoft: 鬱陶しいWindowsスポットライトが作成の原動力になりました
'''

import importlib.util as impl
from io import StringIO
import sys
import os.path as pa
import argparse
import glob
import random
from PIL import Image, ImageDraw, ImageFont
import TkEasyGUI as sg
import threading
import queue
from wall_common import *
from filedialog import *

DEFAULT_MODULE = 'stripe'
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
SAVE_NUM = 3
PREVIEW_SIZE = (640,360)

# ----
# プラグインモジュール検索
# ----
def search_modules(modlist: Modules, plugin_dir):
    modules = {}

    if plugin_dir is None:
        plugin_dir = pa.dirname(__file__)  # directory part
    plugin_pat = 'mod_*.py'  # filename pattern
    
    for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
        modname = pa.splitext(modf)[0]
        if modname.startswith('mod_'):
            modname = modname[4:]
        
        spec = impl.spec_from_file_location(modname, modf)
        module = impl.module_from_spec(spec)
        sys.modules[modname] = module
        spec.loader.exec_module(module)

        if hasattr(module, 'intro'):
            getattr(module, 'intro')(modlist, modname)
            modules[modname] = module

    print(f'Loaded {len(modules)} pattern modules.')
    return modules


def search_aftereffects(efxlist: EfxModules, plugin_dir):
    aftereffects = {}

    if plugin_dir is None:
        plugin_dir = pa.dirname(__file__)  # directory part
    plugin_pat = 'efx_*.py'  # filename pattern
    
    for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
        modname = pa.splitext(modf)[0]
        if modname.startswith('efx_'):
            modname = modname[4:]
        
        spec = impl.spec_from_file_location(modname, modf)
        module = impl.module_from_spec(spec)
        sys.modules[modname] = module
        spec.loader.exec_module(module)

        if hasattr(module, 'intro'):
            getattr(module, 'intro')(efxlist, modname)
            aftereffects[modname] = module

    print(f'Loaded {len(aftereffects)} after-effect modules.')
    return aftereffects


# モジュールファイルで作成必要なAPI関数
#
#    def intro(modlist: Modules, module_name):
#        modlist.add_module(module_name, 'ストライプ(タイル)',
#                           ['color1', 'color_jitter', 'pwidth', 'pheight',
#                            'sub_jitter'])
#        return module_name
#
#    def default_param(p: Param):  パラメータは例。
#        p.color1.itoc( BASE_R, BASE_G, BASE_B)
#        p.pwidth = STRIPE_WIDTH
#        p.pheight = TILE_HEIGHT
#        p.color_jitter = DIFF_STRIPE
#        p.sub_jitter = DIFF_TILE
#        return p
#
#    def generate(p: Param):  実際の画像描画
#        width = p.width
#        height = p.height
#        base_r, base_g, base_b = p.color1.ctoi()
#        image = Image.new("RGB", (width, height),
#                          color=(base_r, base_g, base_b))
#        return image
#
#    def desc(p: Param):
#       return image | None
#
#       descの実装はoptionalであり、無くてもよい。
#       サンプル画像をクリックした際に詳細情報/追加パラメータ設定
#       を提供することができる
#       設定変更の結果壁紙生成結果が変更される場合、imageを返すと
#       メイン画面のサンプル画像を更新する
#
# モジュールの呼び出し方
# (1) モジュールを検索登録する
# modlist = Modules()
# p = Param()
# m = search_modules(modlist, plugin_dir)
#
# (2) モジュールの関数を呼び出す
# modlist.modules == [module-name1, module-name2, ...] : 導入したモジュール名
# modlist.mod_gui[module-name] : モジュールで利用するGUI項目、入ってるものだけ表示
# mods[module-name].default_param(p) : おすすめ初期パラメータを設定
# image = mods[module-name].generate(p)  : 画像を生成


# ----
# メインGUI
# ----
def layout(modlist, efxlist):
    x = ['AE_'+item for item in efxlist.modules]
    menudef = [['File', ['Save', 'Exit']],
               ['Module', modlist.modules],
               ['Hold', ['Hold', 'Clear', 'Retrieve']],
               ['Effects', x],
               ]
    
    
    color_column_layout = [[sg.Text('Base Color:', key='-color1-0',
                                    size=(8,1)),
                            sg.Text('0,0,0', key='-color1-1',
                                    size=(9,1)),
                            sg.Button('...', key='-color1-2'),
                            sg.Button('?', key='-color1-3')
                            ],
                           [sg.Text('Second Color:', key='-color2-0',
                                    size=(8,1)),
                            sg.Text('0,0,0', key='-color2-1',
                                    size=(9,1)),
                            sg.Button('...', key='-color2-2'),
                            sg.Button('?', key='-color2-3')
                            ],
                           [sg.Text('Third Color:', key='-color3-0',
                                    size=(8,1)),
                            sg.Text('0,0,0', key='-color3-1',
                                    size=(9,1)),
                            sg.Button('...', key='-color3-2'),
                            sg.Button('?', key='-color3-3')
                            ]]
    jitter_column_layout = [[sg.Text('Color Mod1:', key='-color_jitter-0',
                                    size=(10,1)),
                             sg.Input('0', key='-color_jitter-1',
                                    enable_events=True, size=(3,1))],
                            [sg.Text('Color Mod2:', key='-sub_jitter-0',
                                    size=(10,1)),
                             sg.Input('0', key='-sub_jitter-1',
                                    enable_events=True, size=(3,1))],
                            [sg.Text('Color Mod3:', key='-sub_jitter2-0',
                                    size=(10,1)),
                             sg.Input('0', key='-sub_jitter2-1',
                                    enable_events=True, size=(3,1))],
                            ]
    pattern_column_layout = [[sg.Text('Pattern1:', key='-pwidth-0',
                                    size=(10,1)),
                             sg.Input('0', key='-pwidth-1',
                                    enable_events=True, size=(3,1))],
                            [sg.Text('Pattern2:', key='-pheight-0',
                                    size=(10,1)),
                             sg.Input('0', key='-pheight-1',
                                    enable_events=True, size=(3,1))],
                            [sg.Text('Pattern3:', key='-pdepth-0',
                                    size=(10,1)),
                             sg.Input('0', key='-pdepth-1',
                                    enable_events=True, size=(3,1))],
                            ]
    file_and_button_column = [[sg.Text('File Name:', text_color='#0022ff'),
                               sg.Text('', expand_x=True, key='-fname-')],
                              [sg.Text('')],
                              [sg.Text('', expand_x=True),
                               sg.Button('Redo', key='-redo-',
                                         background_color='#ffffdd'),
                               sg.Button('Save', key='-ok-',
                                         background_color='#ddffdd'),
                               sg.Text('　'),
                               sg.Button('Quit', key='-done-',
                                         background_color='#ffdddd'),
                               ]
                              ]
    layout = [[sg.Menu(menudef, key='-mnu-')],
              [sg.Text('', key='-modname-'), sg.Text(' '),
               sg.Text('', key='-moddesc-', expand_x=True),
               sg.Text('',expand_x=True), sg.Text('Size:'),
               sg.Input('width', key='-width-', size=(4,1)), sg.Text('x'),
               sg.Input('height', key='-height-', size=(4,1))],
              [sg.Text('',expand_x=True),
               sg.Image(key='-img-', background_color="#7f7f7f",
                        size=PREVIEW_SIZE, enable_events=True),
               sg.Text('',expand_x=True)],
              [sg.Column(layout=color_column_layout),
               sg.Column(layout=jitter_column_layout),
               sg.Column(layout=pattern_column_layout, expand_x=True),
               sg.Column(layout=file_and_button_column)]
              ]

    return layout


def hide_param(window, param):
    for x in range(3):
        k = f'-{param}-{x}'
        try:
            window[k].set_disabled(True)
            window[k].update('')
        except KeyError:
            pass
    if param in ('color1', 'color2', 'color3'):
        window[f'-{param}-1'].update(text_color='#000000', bg='#f0f0f0')
        window[f'-{param}-2'].update('  ')        
        window[f'-{param}-3'].update(' ')        


def show_param(window, param, desc):
    for x in range(3):
        try:
            window[f'-{param}-{x}'].set_disabled(False)
        except KeyError:
            pass
    window[f'-{param}-0'].update(desc)
    if param in ('color1', 'color2', 'color3'):
        window[f'-{param}-2'].update('...')        
        window[f'-{param}-3'].update('?')        


def set_module(window, modlist, module_name):
    if module_name not in modlist.modules:
        return False
    window['-modname-'].update(text=module_name)
    window['-moddesc-'].update(text=modlist.mod_desc[module_name])

    for el in PARAMVALS:
        hide_param(window, el)
    
    for el in modlist.mod_gui[module_name].keys():
        desc = modlist.mod_gui[module_name][el]
        # print(f'{module_name} enable; {el} -> {desc}') 
        show_param(window, el, desc)

    window['-fname-'].update(text=module_name)
    return True


def set_param(window, param, mod_gui):
    for elem in PARAMVALS:
        if elem in mod_gui:
            if elem in ('color1','color2','color3'):
                colr = getattr(param, elem)
                fg,bg = bg_and_font(colr)
                r,g,b = colr.ctoi()
                window[f'-{elem}-1'].update(f'{r},{g},{b}',
                                            text_color=fg, bg=bg)
            else:
                try:
                    window[f'-{elem}-1'].update(getattr(param,elem))
                except KeyError:
                    pass
        else:
            hide_param(window, elem)
    if param.savefile is None or param.savefile == '':
        param.file_name()
    window['-fname-'].update(pa.basename(param.savefile))
    window.refresh()


def set_window_geom(param:Param, window: sg.Window):
    param.wwidth, param.wheight = window.get_location()
    param.wposx, param.wposy = window.get_size()
    for c in range(3):
        s = window[f'-color{c+1}-1'].get()
        if s is not None:
            try:
                color = RGBColor(tuple(int(x) for x in s.split(',')))
                setattr(param, f'color{c+1}', color)
            except ValueError:
                pass
    for x in PARAMVALS[3:]:
        v = window[f'-{x}-1'].get()
        if v is not None:
            try:
                setattr(param, x, int(v, 10))
            except ValueError:
                pass
    return

def set_scale_init(width, height):
    pw, ph = PREVIEW_SIZE
    
    swidth = pw / width
    sheight = ph / height
    scale = min(swidth, sheight)

    # リサイズ後の表示左上位置
    rw, rh = int(width * scale), int(height * scale)
    left = (rw - pw) // 2 if rw >= pw else -(pw - rw) // 2
    top  = (rh - ph) // 2 if rh >= ph else -(ph - rh) // 2

    return scale, (left, top)

def gui_main(modlist: Modules, mods, param: Param,
             efxlist: EfxModules, exfs):
    '''gui_main(modlist:Modules, dict-module_funcs, p:Parameter)
        GUI動作メイン処理
    '''

    pick_color = {'pos':(0,0), 'c':None, 'e':None}
    
    lo = layout(modlist, efxlist)
    wn = sg.Window('Wallpaper Factory', layout=lo)
    set_window_geom(param, wn)

    if DEFAULT_MODULE in modlist.modules:
        modname = DEFAULT_MODULE
    elif modlist.modules != []:
        modname = modlist.modules[0]
    else:
        wn.close()
        return
        
    if set_module(wn, modlist, modname):
        mods[modname].default_param(param)
        param.pattern = modname
        set_param(wn, param, modlist.mod_gui[modname])

    image = mods[modname].generate(param)
    wn['-img-'].update(data=image)
    wn['-width-'].update(param.width)
    wn['-height-'].update(param.height)

    def on_click(event):
        # print('onclick')
        x,y = event.x, event.y
        if 0 <= x < image.width and 0 <= y < image.height:
            pick_color['pos'] = (x,y)
            pick_color['c'] = image.getpixel((x,y))
            wgt.unbind('<Button-1>')

    def loop():
        if pick_color['c'] is not None and pick_color['e'] is not None:
            # print('loop', pick_color['e'])
            if wn[pick_color['e']].get() == '?':
                x,y = pick_color['pos']
                dw,dh = wn['-img-'].size
                iw,ih = image.size
                new_color = image.getpixel((x/dw*iw,y/dh*ih))
                setattr(param, pick_color['e'][1:-2], RGBColor(new_color[0:3]))
                fg,bg = bg_and_font(new_color[0:3])
                r,g,b = to_rgb(bg)
                wn[pick_color['e'][:-1]+'1'].update(f'{r},{g},{b}',text_color=fg,
                                           background=bg)
            pick_color['c'] = None
            wgt = wn['-img-'].widget
            wgt.unbind('<Button-1>')
            wgt.configure(cursor='arrow')
        if wn.is_alive():
            wn.window.after(50,loop)

    def on_motion(event):
        nonlocal mouse_x, mouse_y
        mouse_x, mouse_y = event.x, event.y

    def on_wheel(event):
        nonlocal scale, mouse_x, mouse_y, cropos
        # assert image.size == (param.width, param.height)
        # print('Wheel:', scale, mouse_x, mouse_y, cropos)
        old_scale = scale
        scale *= 1.1 if event.delta > 0 else 0.9
        scale = min(max(scale, 0.1), 3.0)

        w,h = image.width, image.height
        pw,ph = PREVIEW_SIZE
        rw, rh = int(w*scale), int(h*scale)
        if rw < pw and rh < ph:
            scale, cropos = set_scale_init(image.width, image.height)
            if scale != old_scale:
                wn['-img-'].update(image)
            return

        rw0, rh0 = int(w*old_scale), int(h*old_scale)
        left0, top0 = cropos

        gx = (mouse_x + left0)/old_scale
        gy = (mouse_y + top0)/old_scale
        
        prvim = image.resize((rw,rh),resample=Image.LANCZOS)
        
        left, top = int(gx*scale-pw/2), int(gy*scale-ph/2)
        left = max(0, min(left, rw-pw)) if rw >= pw else -(pw - rw) // 2
        top = max(0, min(top, rh-ph)) if rh >= ph else -(ph - rh) // 2
        cropos = (left, top)

        if rw < pw or rh < ph:
            canvas = Image.new('RGB', PREVIEW_SIZE, '#7f7f7f')
            x, y = (pw-rw)//2, (ph-rh)//2 
            canvas.paste(prvim, (x,y))
            wn['-img-'].update(canvas)
        else:
            prvim = prvim.crop((left, top,left+pw,top+ph))
            wn['-img-'].update(prvim)

    scale, cropos = set_scale_init(IMAGE_WIDTH, IMAGE_HEIGHT)
    mouse_x, mouse_y = 0,0

    imw = wn['-img-'].widget
    imw.bind('<MouseWheel>', on_wheel)
    imw.bind('<Motion>', on_motion)

    wn.window.after(50,loop)

    print('-- main loop --')
    while True:
        ev, va = wn.read()
        # print(f'ev:{ev}, va:{va}')

        if ev == sg.WINDOW_CLOSED or ev == 'Exit' or ev == '-done-':
            break
        elif ev == 'Save' or ev == '-ok-':
            base=param.pattern
            fname = pa.basename(param.file_name())
            fname = get_savefile(fname)
            if fname == '':
                continue
            image.save(fname)
            param.savefile = pa.basename(fname)
            wn['-fname-'].update(param.savefile)
            continue
        elif ev == '-redo-':
            try:
                param.width = int(va['-width-'])
                param.height = int(va['-height-'])
            except ValueError:
                param.width, param.height = IMAGE_WIDTH, IMAGE_HEIGHT
            image = get_image_thread(wn, param, mods, modname)
            scale, cropos = set_scale_init(param.width, param.height)
            if image is not None:
                wn['-img-'].update(data=image)
            else:
                print("DON'T CLOSE DIALOGUE")
            continue
        elif ev in modlist.modules:
            modname = ev
            set_module(wn, modlist, modname)
            param.pattern = modname
            param.savefile = ''
            mods[ev].default_param(param)
            set_param(wn,param, modlist.mod_gui[modname])

            image = get_image_thread(wn, param, mods, modname)
            scale, cropos = set_scale_init(param.width, param.height)
            if image is not None:
                wn['-img-'].update(data=image)
            else:
                print("DON'T CLOSE DIALOGUE")
            continue
        elif ev == 'Hold':
            param.keep(modname, image)
            continue
        elif ev == 'Clear':
            param.unkeep()
            continue
        elif ev == 'Retrieve':
            t = param.retrieve()
            if t in modlist.modules:
                set_module(wn, modlist, t)
                param.pattern = t
                param.savefile = ''
                set_param(wn, param, modlist.mod_gui[t])
                modname = t
                image = param.bg()
                scale, cropos = set_scale_init(param.width, param.height)
                wn['-img-'].update(data=image)
            continue
        elif ev in ('-color1-3', '-color2-3', '-color3-3'):
            wgt = wn['-img-'].widget
            pick_color['e'] = ev
            wgt.bind('<Button-1>', on_click)
            wgt.configure(cursor='tcross')
            # loop wait
            continue
        elif ev in ('-color1-2', '-color2-2', '-color3-2'):
            s = getattr(param, ev[1:-2]).ctox().upper()
            new_color = sg.popup_color(default_color=s)
            if new_color.upper() != s:
                setattr(param, ev[1:-2], RGBColor(new_color))
                fg,bg = bg_and_font(new_color)
                r,g,b = to_rgb(bg)
                wn[ev[:-1]+'1'].update(f'{r},{g},{b}',text_color=fg,
                                       background=bg)
            continue            
        elif ev == '-img-' and va['event_type'] == 'mousedown':
            # print('-img-', ev, va)
            set_window_geom(param, wn)
            # print(param.wwidth, param.wheight, param.wposx, param.wposy)
            if hasattr(mods[modname], 'desc'):
                retv = mods[modname].desc(param)
                if isinstance(retv, Image.Image):
                    image = retv
                    scale, cropos = set_scale_init(param.width, param.height)
                    wn['-img-'].update(data=image)
                    set_param(wn, param, modlist.mod_gui[modname])
        elif isinstance(ev, str):
            widg = ev[1:-2]
            # print( widg )
            if not is_param(widg):
                continue
            try:
                s = int(wn[ev].get(),10)
            except ValueError:
                s = 0
            if hasattr(param, widg):
                t = int(getattr(param, widg))
                if s != t:
                    setattr(param, widg, s)
            else:
                print('has no attr', ev, 'as', widg)

    wn.close()
    return


# ----
# イメージ取得を別スレッドで実施する
# ----
result_q = queue.Queue()

def long_task(param, modules, modname):
    image = modules[modname].generate(param)
    result_q.put(image)


def get_image_thread(window, param, modules, modname):
    progress = sg.Window('', [[sg.Text('Wait...', text_align='center',
                                       size=(20,10), 
                                       background_color='#f0e070')]],
                         modal=True, no_titlebar=True, grab_anywhere=True,
                         padding_x=5, padding_y=10,
                         element_justification='c', finalize=True)
    threading.Thread(
        target=long_task,
        args=(param,modules,modname),
        daemon=True).start()
    while True:
        pev, pva = progress.read(timeout=50)
        if pev is None:
            image = None
            break
        elif  not result_q.empty():
            image = result_q.get()
            break
    progress.close()
    return image


# ----
# CLI(非インタラクティブ)動作メイン
# ----
def batch_generate(mods, pattern, args, param):
    mods[pattern].default_param(param)
    for name in ['jitter1', 'jitter2', 'jitter3',
                 'pwidth', 'pheight', 'pdepth']:
        v = getattr(args, name, None)
        if v is not None:
            setattr(param, name, v)
    for name in ['color1', 'color2', 'color3']:
        v = getattr(args, name, None)
        if v is not None:
            setattr(param, name, RGBColor(v))  # strのままじゃ駄目

    img = mods[pattern].generate(param)
    drw = ImageDraw.Draw(img)
    font = ImageFont.truetype('arial.ttf', 10)
    drw.text((param.width-len(pattern)*10,param.height-12),text=pattern,
             fill='#ffffff', font=font)
    return img


def args_set(parser):
    parser.add_argument('--plugin_dir', help='プラグインフォルダ')
    parser.add_argument('--list_modules',action='store_true',
                       help='モジュールリスト表示')
    parser.add_argument('--module', help='モジュールを起動 random可')
    parser.add_argument('--width', type=int, help='生成画像幅')
    parser.add_argument('--height', type=int, help='生成画像高')
    parser.add_argument('--color1', help='基本色指定')
    parser.add_argument('--color2', help='追加色指定2')
    parser.add_argument('--color3', help='追加色指定3')
    parser.add_argument('--jitter1', type=int, help='変動パラメータ1')
    parser.add_argument('--jitter2', type=int, help='変動パラメータ2')
    parser.add_argument('--jitter3', type=int, help='変動パラメータ3')
    parser.add_argument('--pheight', type=int, help='パターン設定1')
    parser.add_argument('--pwidth', type=int, help='パターン設定2')
    parser.add_argument('--pdepth', type=int, help='パターン設定3')
    parser.add_argument('files', nargs='*')
    
                   
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='壁紙ジェネレータ')
    args_set(parser)

    exe = pa.basename(sys.executable).lower()
    if ('--help' in sys.argv or '-h' in sys.argv) and exe == 'pythonw.exe':
        helptext = parser.format_help()
        sg.popup(helptext, title='WallPaper Generator')
        exit()
    args = parser.parse_args()    
    
    modlist = Modules()
    mods = search_modules(modlist, args.plugin_dir)
    efxlist = EfxModules()
    efxs = search_aftereffects(efxlist, args.plugin_dir)

    param = Param()
    
    param.width = IMAGE_WIDTH if args.width is None else args.width 
    param.height = IMAGE_HEIGHT if args.height is None else args.height

    if args.list_modules:
        buf = StringIO()
        print('Modules available:', file=buf)
        for x in modlist.modules:
            print(f'{x}: {modlist.mod_desc[x]}', file=buf)
        if  exe == 'pythonw.exe':
            sg.popup(message=buf.getvalue(), title='WallPaper Generator')
        else:
            print(buf.getvalue())
    elif args.module is None:
        gui_main(modlist, mods, param, efxlist, efxs)
    else:
        pattern = args.module
        if pattern.lower() == 'random':
            pattern = modlist.modules[random.randint(0,len(modlist.modules)-1)]
        
        img = batch_generate(mods, pattern, args, param)
        print(f'Generated {pattern}')
        if len(args.files) > 0:
            f = pa.splitext(args.files[0])[0]+'.png'
            img.save(f)
            print(f'Image saved in {f}')
        else:
            img.show()
