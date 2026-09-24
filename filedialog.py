import os.path as pa
import tkinter as tk
from tkinter import filedialog
import glob
import zipfile
# import posixpath
import re
import fnmatch
import TkEasyGUI as sg
from wall_common import to_rgb, clip8

def get_openfile(fname, filetypes='', init_dir='.'):
    """開く既存ファイル名を取得 filetypes省略時は[("PNG files", "*.png"),]"""
    root = tk.Tk()
    root.withdraw()

    if filetypes == '':
        filetypes = [('PNG files', '*.png'),]
        
    filename = filedialog.askopenfilename(
        title='Open File',
        initialdir=init_dir,
        initialfile=fname,
        filetypes=filetypes
    )
    
    root.destroy()

    if not pa.exists(filename):
        return ''
    else:
        return filename


def get_savefile(fname, filetypes='', init_dir='.'):
    """保存ファイル名を取得 filetypes省略時は[("PNG files", "*.png"),]"""
    root = tk.Tk()
    root.withdraw()

    if filetypes == '':
        filetypes = [('PNG files', '*.png'),]
        
    filename = filedialog.asksaveasfilename(
        title='Save File',
        initialdir=init_dir,
        initialfile=fname,
        filetypes=filetypes
    )
    root.destroy()
    return filename


def get_folder(init_dir='.'):
    """フォルダ名を取得 Tkだとファイルは表示されない"""
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title='Select Folder',
        initialdir=init_dir,
        mustexist=True,
        )

    root.destroy()
    return folder


def flush_ev(window):
    """イベント空読み(filedialog読出後に安全のため利用)"""
    while True:
        e, v = window.read(timeout=0)
        if e == sg.TIMEOUT_KEY:
            break
    return


# ファイル名サニタイズ
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

def sanitize_filename(name, ext=None, force_ext=None):
    """ファイル名に利用できない文字、デバイス名を除外する
    拡張子-> ext:無ければ付ける force_ext:強制的に付加"""
    name = name.strip()
    path, basename = pa.split(name)
    base, suffix = pa.splitext(basename)

    if path != '':
        path = sanitize_dirname(path)+pa.sep

    base = re.sub(r'[\\:*?"<>|]', '', base.replace('/','\\'))
    if base.upper() in RESERVED_NAMES:
        base = f"{base}_"

    if force_ext is not None:
        suffix = force_ext
    elif suffix == '' and ext is not None:
        suffix = ext

    return path+base+suffix


def sanitize_dirname(name):
    """ディレクトリ名に利用できない文字、デバイス名を除外する"""
    drv, path = pa.splitdrive(name)
    path = re.sub(r'[:*?"<>|]', '', path.replace('/','\\'))
    p = path.split('\\')
    path = '\\'.join([x+'_' if x.upper() in RESERVED_NAMES else x for x in p])

    return drv+path


def basename_wo_ext(fname):
    return pa.splitext(pa.basename(fname))[0]


def yn_dialog(title: str, message: str, buttontext: str = 'Ok'):
    """Cancel/Anyダイアログ
        デフォルトボタン表示テキスト = OK"""
    with sg.Window(title,
               layout=[[sg.Text(message)],
                       [sg.Button('Cancel', key='-dcan-'),
                        sg.Button(buttontext, key='-dok-',
                                  background_color='#ddffdd')]],
               modal=True) as dialog:
        for ev,va in dialog.event_iter():
            if ev == '-dok-':
                ans = True
                break
            elif ev == sg.WINDOW_CLOSED or ev == '-dcan-':
                ans = False
                break
    return ans


def glob_filelistz(fpattern: str, add_zip=None):
    """find filelist + zipped filelist
        fpattern = filename pattern (with default_directory)
        add_zip = zipfile in current dir
        return= [filelist], [zippedfilelist]"""
    
    # 生ファイル検索
    directory, pattern = pa.split(fpattern)
    if directory == '':
        directory = '.'
    
    nfiles = glob.glob(fpattern)
    if len(nfiles) == 0:
        nfiles = []
    else:
        nfiles = [pa.basename(x) for x in nfiles]
    
    zfiles = []
    if add_zip is not None:
        for f in (directory+pa.sep+add_zip, add_zip):
            if pa.exists(f):
                with zipfile.ZipFile(f) as z:
                    zfiles = [name for name in z.namelist()
                              if fnmatch.fnmatch(name, pattern)]
                    break

    return sorted(dict.fromkeys(nfiles + zfiles))


def read_filez(filepath: str, add_zip=None):
    """ファイル読み込み add_zipが指定された場合zip内のファイルも検索
        filepath -> dir, name とした場合、以下の順で存在したファイルを読込
            filepath, dir+add_zip/name, add_zip/name
        return [str...]  (SJIS)
    """
    def zipread(zip, name):
        with zip.open(name, mode='r') as zf:
            lines = zf.read().splitlines()
        lines = [x.decode('SJIS') for x in lines]
        return lines

    lines = []
    found = False
    filepath = sanitize_filename(filepath)
    directory, name = pa.split(filepath)
    if directory == '':
        directory = '.'
    
    if pa.exists(filepath):
        found = True
        # print(f'normal {name}')
        with open(filepath, mode='r', encoding='SJIS') as f:
            lines = f.read().splitlines()
        
            
    elif add_zip is not None:
        for f in (directory+pa.sep+add_zip, add_zip):
            if pa.exists(f):
                with zipfile.ZipFile(f) as z:
                    if name in z.namelist():
                        found = True
                        # print(f'zip {name}')
                        lines = zipread(z, name)
                        break

    return lines if found else None


# パレット保存/読出
def save_palette(colors, init_dir='samples', encoding='sjis', mode='w'):
    """colors [Color1, Color2,...], Color = (r,g,b) or '#rrggbb'
       mode='w'rite or 'o'verwrite"""
    fname = get_savefile('default.pal', filetypes=[('palette', '*.pal')],
                             init_dir=init_dir)
    if fname is None:
        return None
    return store_palette(fname, colors, init_dir, encoding, mode)

# 強制save
def store_palette(fname, colors, init_dir='samples', encoding='sjis',
                  mode='w'):
    if pa.exists(fname) and mode=='o':  # overwrite mode
        old_colors = retrieve_palette(fname, 10, encoding)
        if isinstance(old_colors, list):
           old_colors = [x for x in old_colors if x is not None]
           lc = len(colors)
           lo = len(old_colors)
           if lc < lo:
               for n in range(lo-lc):
                   colors.append(old_colors[n+lc])
    try:
        with open(fname, mode='w', encoding=encoding) as f:
            f.write('[Colors]\n')
            for i, c in enumerate(colors):
                if c is not None:
                    r,g,b = to_rgb(c)[:3]
                    f.write(f'Color{i}=({r},{g},{b})\n')
        return fname
    except Exception as e:
        print('Error:', e)
        print(colors, i, c)
        return None


def load_palette(fname='default.pal', max_num=10,
                 init_dir='samples', encoding='sjis'):
    """max_num <= 10, accept .pal/.ttn"""
    filetypes = [('palette', '*.pal'),
                 ('tartan set', '*.ttn')]
    fname = get_openfile(fname, filetypes=filetypes,
                             init_dir=init_dir)
    if fname is None or fname == '':
        return None
    colors = retrieve_palette(fname, max_num, encoding)
    if colors is None:
        return None

    # 欠損をグレーで補完
    k = 255 //  max_num
    for i in range(max_num):
        if not isinstance(colors[i], tuple):
            colors[i] = tuple((clip8(i*k),) * 3)

    return colors

# 強制load (補完なし)
def retrieve_palette(fname, max_num, encoding):
    try:
        with open(fname, mode='r', encoding=encoding) as f:
            buf = f.read().splitlines()
    except Exception as e:
        print('Error:', e)
        return None

    return decode_palette(buf, max_num)

def decode_palette(buf, max_num):
    """パレットテキストの読み込み -> (r,g,b) × max_num個のlist of tuple"""
    p = 0
    while True:
        if buf[p].startswith('[Colors]'):
            break
        p += 1
        if p == len(buf):
            return None
    p += 1
    colors = ([None]* max_num)
    c = 0
    while True:
        m = re.match(r'Color(\d+)=\(\s*(\d+),\s*(\d+),\s*(\d+).*\)', buf[p])
        if m:
            cno = int(m.group(1))
            r = int(m.group(2))
            g = int(m.group(3))
            b = int(m.group(4))
            if 0<= cno <  max_num:
                colors[cno] = (r,g,b)
                c += 1
                if c ==  max_num:
                    break
            else:
                print(f'no match: {p[buf]}')
                
        p += 1
        if p == len(buf):
            break

    return colors
