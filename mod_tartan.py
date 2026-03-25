import re
import copy
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
import TkEasyGUI as sg
from wall_common import *
from filedialog import *
'''
タータンの繰り返しパターンの1単位はセットといい、
・2色以上の色糸が直角に交わる格子柄であること
・たて糸・よこ糸の色と数が同じパターンの繰り返しであること
というデザイン上の特徴がある。ひとつひとつの色にも意味があるらしい。

タータンには氏族や地域を表すものや、組織・王室・企業などの所属を示すもの
など様々なタータンがあるが、スコットランドの「タータン登記所」に登録
することで正式に「タータン」と認められる。
スコットランドの家紋のような位置づけなので、勝手にタータンと称しては
いけない。古くは、戦場で誰だか判らなくなった遺体の身元確認に使われていた
という説もある。

2026/02/01 エディタにRewrite(再整形), 2倍、1/2倍ボタンを追加
　セットパターンは行番号が実際には無視されるので、表示エリアの内容を
セットパターンテキストとして成形する Reform機能を追加
　パターン内の各色幅を2倍・1/2倍するボタンを追加
'''

# ----
# 定数
# ----
SPECIAL_COLOR1 = (0xf8, 0xf8, 0x44)  # 7 特色1 黄
SPECIAL_COLOR2 = (0xf8, 0x11, 0xf8)  # 8 特色2 桃
SPECIAL_COLOR3 = (0xfc, 0xe6, 0x8d)  # 9 特色3 卵
BRIGHTNESS = 100
SATURATION = 100
PERIOD = 6
DUTY = 50

# 内部定数
DATA_DIR = 'samples'
ZIPFILE = 'tartan.zip'
BASIC_COLOR = [(20, 60, 40),     # 0 緑
               (190, 20, 30),    # 1 赤
               (239, 227, 215),  # 2 オフホワイト
               (20, 10, 80),     # 3 紺 
               (5, 5, 5),        # 4 黒
               (197, 170, 145),  # 5 キャメル
               (130, 130, 130),  # 6 灰
               ]

tartan_preserv = {
    'pattern': [(0,200),(7,5),(0,200),(5,10),(0,20),
                (1,25),(0,10),(1,25),(0,20),(5,10)]  # 初期柄
}

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'タータンチェック風(＋セットエディタ)',
                       {'color1':'特色1', 'color2':'特色2', 'color3':'特色3',
                        'color_jitter':'明るさ(%)', 'sub_jitter':'彩度(%)',
                        'pwidth':'織目数', 'pheight':'DUTY比(%)'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*SPECIAL_COLOR1)
    p.color2.itoc(*SPECIAL_COLOR2)
    p.color3.itoc(*SPECIAL_COLOR3)
    p.color_jitter = BRIGHTNESS
    p.sub_jitter = SATURATION
    p.pwidth = PERIOD
    p.pheight = DUTY
    return p


# ----
# セットエディタ
# ----
def layout():
    left = sg.Image(key='-test-', size=(300,300))
    macros = [[sg.Button('Rewrite', key='-t_rwt-'),
               sg.Button('2X', key='-t_dbl-'),
               sg.Button('1/2', key='-t_hlf-'), ],
              [sg.Button('Flip&Paste', key='-t_flp-')],
              ]
    right = [[sg.Text('Pallet'),
              sg.Image(key='-pallet-', size=(136,56), enable_events=True),
              sg.Text('', expand_x=True),
              sg.Column(macros, expand_x=True),
              ],
             [sg.Multiline('', key='-t_pat-',size=(20,12),
                           background_color='#f0eea0',
                           text_align='left',
                           expand_x=True, expand_y=True)],
             [sg.Button('Delete', key='-t_del-'),
              sg.Text('C:',text_align='right', size=(4,1)),
              sg.Text('', key='-t_col-', size=(2,1)),
              sg.Text('', key='-t_ctp-', size=(10,1)),
              sg.Text(' W:'),
              sg.Input('', key='-t_wth-', size=(4,1),
                       background_color='#f0eea0'),
              sg.Button('Add', key='-t_add-'),]
             ]
    
    buttons = [sg.Text('File'),
               sg.Combo([], key='-t_file-',
                        readonly=True, expand_x=True),
               sg.Button('Load', key='-t_ld-'),
               sg.Button('Save', key='-t_sv-'),
               sg.Text('', size=(2,1)),
               sg.Button('Clear', key='-t_clr-', background_color='#ddddff'),
               sg.Text('', size=(2,1), expand_x=True),
               sg.Button('Cancel', key='-t_can-', background_color='#ffdddd'),
               sg.Button('Apply', key='-t_ok-', background_color='#ddffdd'),
               ]

    return [[left, sg.Column(layout=right, expand_x=True, expand_y=True)],
            buttons]


# ttnファイルリスト
def ttnfile_list(directory=DATA_DIR):
    patn = directory+pa.sep+'*.ttn'
    files = [fn.replace('.ttn','') \
             for fn in glob_filelistz(patn, add_zip=ZIPFILE)]
    return files


# パレット画像の生成
def palimg(cset):
    # print(cset)
    img = Image.new('RGB', (137,57), '#e0e0e0')
    drw = ImageDraw.Draw(img)
    for i in range(5):
        drw.rectangle((i*27+5,5,i*27+25, 25), fill=cset[i])
        drw.rectangle((i*27+4,3,i*27+27, 27), outline='#000000', width=2)
        drw.rectangle((i*27+5,32,i*27+25, 52),fill=cset[i+5])
        drw.rectangle((i*27+3,30,i*27+27, 54), outline='#000000', width=2)
    return img
    

# セットパターンのテキスト化
def pattxt(pattern):
    width = 0
    text = '[Pattern]\n'
    lno = 0
    for c,w in pattern:
        lno += 1
        line = f'{lno:02d}:Color{c} * {w}\n'
        text += line
        width += w

    if len(pattern) == 0:
        return text, 100
    return text, width


# ttnファイルの読み込み
def read_color_section(buf, lno):
    cset = [None]*10
    for l2 in range(lno,len(buf)):
        l = buf[l2].strip()
        if len(l) < 1:
            lno += 1
            continue
        if l[0] == '[':
            break
        cc = l.split('=')
        # print(cc)
        if len(cc) >= 2:
            try:
                cn = int(cc[0][-1:])
            except ValueError:
                continue
            rgb = to_rgb(strtotuple(cc[1]))
            cset[cn] = rgb
        lno += 1
        continue
    return cset, lno

    
def read_pattern_section(buf, lno):
    pat = []
    for l2 in range(lno,len(buf)):
        #print(l2,':', buf[l2])
        l = buf[l2].strip()
        if len(l) < 1:
            lno += 1
            continue
        if l[0] == '[':
            break

        cc = l.split(':')
        # print(cc)
        if len(cc) >= 2:
            # 行番号部分は読み捨て
            cc = cc[1].split('*')
            if len(cc) >= 2:
                r = re.search(r'\d+', cc[0])
                if r:
                    col = np.clip(int(r.group()),0,9)
                    r = re.search(r'\d+', cc[1])
                    if r:
                        w = min(max(1,int(r.group())),3840)
                        pat.append((col,w))
            #print(cc, pat[-1])
        lno += 1
        continue
    return pat, lno


def pattern_resize(pat, sc):
    for p in range(len(pat)):
        c,w = pat[p]
        pat[p] = (c, min(max(1,int(w*sc)),3840))
    return pat
        

def load_pattern(fname):
    '''fnameからセットパターン及び利用色情報を読み込み、text, csetを返す'''
    fname = DATA_DIR+pa.sep+fname
    # print(fname)
    buf = read_filez(fname, add_zip=ZIPFILE)
    if buf is None or buf == []:
        return [], 0

    cset = [None]*10
    pat = []
    section = None
    lno = 0
    for lno in range(len(buf)):
        l = buf[lno].strip()
        # print(f'{section}:', l)
        if '[Colors]' in l:
            section = 'c'
            lno += 1
            cset_r, lno = read_color_section(buf, lno)
            for no in range(10):
                cset[no] = cset_r[no] if cset_r[no] is not None else None
            continue
        elif '[Pattern]' in l:
            section = 'p'
            lno += 1
            pat, lno = read_pattern_section(buf, lno)
            continue
    for i in range(10):
        if cset[i] is None:
            cset[i] = (0,0,0)
    # print(cset)
    return pat, cset


# セットパターンをttnファイルへ保存
def save_pattern(fname, pat, cset):
    fname = sanitize_filename(fname, force_ext='.ttn')
    with open(fname, mode='w') as f:
        f.write('[Colors]\n')
        for i in range(10):
            t = to_rgb(cset[i])
            f.write(f'Color{i}={t}\n')

        txt,_ = pattxt(pat)
        f.write(txt)
    return


# "(r,g,b)" を (r,g,b) に変換
def strtotuple(s):
    if s[0] == '#':
        return to_rgb(s)
    elif s[0] == '(':
        return tuple(int(x) for x in s.strip('()').split(','))


def desc(p: Param):
    wn = sg.Window('Tartan-Set Editor', layout=layout(),
                   resizable=True)  # , modal=True)

    # 色セットの読み込み
    cset = copy.copy(BASIC_COLOR)
    cset.append(p.color1.ctoi())
    cset.append(p.color2.ctoi())
    cset.append(p.color3.ctoi())
    img = palimg(cset)
    wn['-pallet-'].update(data=img)

    # 仮セットパターンの読み込み
    pat = copy.copy(tartan_preserv['pattern'])
    text, patw = pattxt(pat)
    wn['-t_pat-'].update(text=text)

    # 本体用パラメータの保存(特色も)
    org_w, org_h = p.width, p.height
    org_color = []
    for i in range(3):
        org_color.append(getattr(p, f'color{i+1}'))
    p.width, p.height = patw, patw
    
    img = generate(p, pattern=pat)
    wn['-test-'].update(data=img)
    flist = ttnfile_list()
    wn['-t_file-'].update(values=flist)

    while True:
        ev, va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-t_can-':  # キャンセル
            break
        if ev == '-t_ok-':  # 反映して終了
            if len(pat) > 0:
                for i in range(3):
                    if cset[i+7] != getattr(p, f'color{i+1}'):
                        setattr(p, f'color{i+1}', RGBColor(cset[i+7]))
            break
        elif ev == '-pallet-' and va['event_type'] == 'mousedown':  # 色指定
            x, y = get_pos(str(va['event']))
            xx = (x-7) % 27
            if 0<= xx <= 20:
                x = (x-7) // 27 if (x-7) // 27 < 5 else 4
                yy = (y-5) % 27
                if 0<= yy <= 20:
                    y = 5 if y>31 else 0
                    c = y + x
                    # print(va['event'],x, y, c)
                    # 色名表示部分には背景色をつける
                    fg, bg = bg_and_font(cset[c])
                    wn['-t_col-'].update(str(c),
                                         text_color=fg, background_color=bg)
                    wn['-t_ctp-'].update(f'({cset[c][0]},{cset[c][1]},{cset[c][2]})')
            continue
        elif ev == '-t_add-':  # 色・幅をセットに追加
            if wn['-t_col-'].get() == '' or wn['-t_wth-'].get() == '':
                continue
            col = int(wn['-t_col-'].get())
            w = int(wn['-t_wth-'].get())
            pat.append((c,w))
        elif ev == '-t_del-':  # 最終行を削除
            pat.pop()
        elif ev == '-t_clr-':  # セットを初期化
            pat = []
        elif ev == '-t_ld-':  # 読み込み
            fname = wn['-t_file-'].get()
            if fname != '' and fname is not None:
                old_cset = copy.copy(cset)
                pat, cset = load_pattern(fname+'.ttn')
                # wn['-t_file-'].update(fname)
                if cset != old_cset:
                    pimg = palimg(cset)
                    wn['-pallet-'].update(data=pimg)
                    
                p.savefile = fname
        elif ev == '-t_sv-':  # 保存
            oldf = wn['-t_file-'].get()+'.ttn'
            fname = get_savefile(oldf, filetypes=[('Tartan set','*.ttn'),],
                                 init_dir=DATA_DIR)
            frush_ev(wn)
            if fname != '' and fname is not None:
                save_pattern(fname, pat, cset)
                wn['-t_file-'].update(fname)
                p.savefile = fname
            flist = ttnfile_list()
            wn['-t_file-'].update(values=flist)
            continue
        elif ev in ('-t_rwt-', '-t_dbl-', '-t_hlf-'):
            # リライト/倍幅化/半幅化
            opat = copy.copy(pat)
            ptext = (wn['-t_pat-'].get()+'\n').splitlines()
            # 編集されたパターン文字列をpatに読み込む
            pat,_ = read_pattern_section(ptext, 1)
            if len(pat) < 2:
                pat = copy.copy(opat)  # 空になってたら元に戻す
            elif ev == '-t_dbl-':
                pat = pattern_resize(pat, 2)  # 倍幅化
            elif  ev == '-t_hlf-':
                pat = pattern_resize(pat, 0.5)  # 半幅化
            # テキストにして表示領域を更新
            ptxt,_ = pattxt(pat)
            wn['-t_pat-'].update(ptxt)
            if pat == opat:
                continue
        elif ev == '-t_flp-':
            print(va)
            ml = wn['-t_pat-'].widget
            if ml.tag_ranges("sel"):
                # 選択範囲の先頭と最後を取得
                st = int(ml.index('sel.first').split('.')[0])-1
                ed = int(ml.index('sel.last').split('.')[0])-1
                # バッファ先頭が[Pattern]ならオフセットあり
                firstline = ml.get('1.0','2.0')
                offset = 1 if 'attern' in firstline else 0
                # 現パターン長までの間で、選択範囲のパターンを取得
                lm = len(pat)
                addpat = []
                for cptr in range(st-offset, ed-offset+1):
                    if cptr < lm:
                        addpat.append(pat[cptr])
                # 反転させて末尾にペースト
                for itm in reversed(addpat):
                    pat.append(itm)
                #print(f'range: {st},{ed}, line1={ml.get("1.0","2.0")}')
            else:
                #print('No Sel:',ml.tag_ranges("sel"))
                continue
        else:
            continue
        
        # 変更があった場合はサンプル画像を更新
        text, patw = pattxt(pat)
        wn['-t_pat-'].update(text=text)
        p.width, p.height = patw, patw
        for i in range(3):
            setattr(p, f'color{i+1}', RGBColor(cset[7+i]))
        img = generate(p, pattern=pat)
        wn['-test-'].update(data=img)

    wn.close()
    p.width, p.height = org_w, org_h
    # 一旦元のcolor1～3に書き戻し
    for i in range(3):
        setattr(p, f'color{i+1}', org_color[i])
    if len(pat) == 0 or pat == tartan_preserv['pattern']:
        # セットの変更なし or 仮セットが空(実質キャンセル)
        return
    else:
        # セットの変更があった場合
        # 変更された可能性があるのでcolor1～3を更新
        for i in range(3):
            setattr(p, f'color{i+1}', RGBColor(cset[7+i]))
        tartan_preserv['pattern'] = pat
        return generate(p)


# ----
# 生成
# ----
def generate(p: Param, pattern=None):
    width, height = p.width, p.height
    cset = copy.copy(BASIC_COLOR)
    cset.append(p.color1.ctoi())
    cset.append(p.color2.ctoi())
    cset.append(p.color3.ctoi())
    color=[]
    for i in range(10):
        color.append(np.array(list(cset[i])))

    brightness = max(0.0, p.color_jitter / 100.0)
    saturation = max(0.0, p.sub_jitter / 100.0)
    period = min(max(p.pwidth,1),40)
    duty = np.clip(p.pheight, 0, 100) / 100.0

    # パターンの定義
    base_pattern = []
    if pattern == None:
        pattern = tartan_preserv['pattern']
    elif len(pattern) == 0:
        return Image.new('RGB', (width, height), cset[0])
        
    for c, w in pattern:
        base_pattern.extend([color[c]] * w)
        # print(f'color{c} * width{w}')

    base_pattern = np.array(base_pattern, dtype=np.uint8)
    ps = len(base_pattern)
    delta = int(period * duty) if int(period*duty) > 0 else 1
    if period <= 2:
        period = 2
        delta = 1
    
    # 座標グリッドの作成
    y_idx = np.arange(height) % ps
    x_idx = np.arange(width) % ps
    
    # 縦糸と横糸のそれぞれの色を全ピクセル分用意
    horizontal_stripes = base_pattern[y_idx][:, np.newaxis, :] # (height, 1, 3)
    vertical_stripes = base_pattern[x_idx][np.newaxis, :, :]   # (1, width, 3)
    
    # 「綾織り」ロジックの適用
    # (x + y) % 4 のような計算で、斜めに縦糸・横糸を入れ替える
    # 2x2 や 4x4 の周期で切り替えると布らしくなります
    # weave_mask が True なら縦糸、False なら横糸を表示
    yy, xx = np.indices((height, width))
    weave_mask = ((xx + yy) % period < delta)
    weave_mask = weave_mask[:, :, np.newaxis] # ブロードキャスト用

    # マスクに基づいて色を選択
    tartan_data = np.where(weave_mask, vertical_stripes, horizontal_stripes).astype(np.uint8)

    # 糸の重なりを強調するためにわずかに明るさを変える
    shade = ((xx + yy) % 2 * 10).astype(np.int16)
    tartan_data = np.clip(tartan_data.astype(np.int16) - shade[:, :, np.newaxis], 0, 255).astype(np.uint8)

    image = Image.fromarray(tartan_data)

    image = ImageEnhance.Color(image).enhance(saturation)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    return image


# ----
# テスト
# ----
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080

    img = generate(p)
    img.show()
