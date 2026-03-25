import os.path as pa
import tkinter as tk
from tkinter import filedialog
import glob
import zipfile
# import posixpath
import re
import fnmatch
import TkEasyGUI as sg

def get_openfile(fname, filetypes='', init_dir='.'):
    '''開く既存ファイル名を取得 filetypes省略時は[("PNG files", "*.png"),]'''
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
    '''保存ファイル名を取得 filetypes省略時は[("PNG files", "*.png"),]'''
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


def frush_ev(window):
    '''イベント空読み(filedialog読出後に安全のため利用)'''
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
    drv, path = pa.splitdrive(name)
    path = path.replace('/','\\')
    p = path.split('\\')
    path = '\\'.join([x+'_' if x.upper() in RESERVED_NAMES else x for x in p])

    return drv+path


def yn_dialog(title: str, message: str, buttontext: str = 'Ok'):
    '''Cancel/Anyダイアログ
        デフォルトボタン表示テキスト = OK'''
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
    '''find filelist + zipped filelist
        fpattern = filename pattern (with default_directory)
        add_zip = zipfile in current dir
        return= [filelist], [zippedfilelist]'''
    
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
    '''ファイル読み込み add_zipが指定された場合zip内のファイルも検索
        filepath -> dir, name とした場合、以下の順で存在したファイルを読込
            filepath, dir+add_zip/name, add_zip/name
        return [str...]  (SJIS)
    '''
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
