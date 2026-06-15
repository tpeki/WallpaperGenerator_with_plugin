import ctypes
from ctypes import wintypes
import os
import sys
import tempfile
import glob
import winreg
from PIL import Image
import time

# Registry WallpaperStyle
OVERSCAN = 10  # アスペクト維持で拡大(余剰分カット)
MAXIMIZE = 6  # アスペクト維持で拡大(余白は背景色)
STRETCH = 2  # アスペクト無視で引き伸ばす
CENTER = 0  # 画面中央配置

DEBUG = False

def is_windows():
    """True if running under Windows"""
    return (sys.platform == 'win32')


def set_wallpaper(img, stretch, tiled=False, resize=None):
    """imgを壁紙に設定する: stretch=10で画面サイズに拡大、tile=Trueでタイル
    resize=タイルにする場合の画像サイズ"""

    monitors = get_screens()
    max_width = max(info["width"] for info in monitors)

    aspect = img.height/img.width
    if tiled:
        stretch = 0

    if stretch > 0:
        new_size = (max_width, int(max_width * aspect))
    elif isinstance(resize, tuple or list):
        new_size = resize
    else:
        new_size = img.size

    if img.size != new_size:
        img = img.resize(new_size, resample=Image.LANCZOS)
        if DEBUG:
            print(f'Resize image to {new_size}')
    else:
        if DEBUG:
            print(f'image size is same, {new_size}')

    t0 = dbg_time() if DEBUG else 0

    set_wpstyle_registry(stretch, tiled)

    t1 = dbg_time("registry", t0) if DEBUG else t0
    
    set_img_to_wp(img)

    t2 = dbg_time("SPI", t1) if DEBUG else t0
    if DEBUG:
        dbg_time("total", t0)
        
    return


def dbg_time(msg=None, base=None):
    t = time.perf_counter()
    if base is not None:
        print(msg if msg is not None else '', t - base)
    return t


def cache_cleanup():
    cache_dir = os.path.join(tempfile.gettempdir(),'wp_cache')
    for f in glob.glob(cache_dir+'\\*.*'):
        try:
            os.remove(f)
        except:
            pass
    return


# ! 注意 !
#  レジストリの変更は、次に SystemParametersInfoW が実行されたタイミングで
# Windows システムに反映される
#  そのため、必ず「レジストリ書き換え ➔ API呼び出し」の順で実行すること

def set_wpstyle_registry(stretch, tiled=False):
    """stretch={OVERSCAN(10)| MAXIMIZE(6)| STRETCH(2)| CENTER(0)}
        tiled = True | False, resize=(width,height) for tiles
    """
    if stretch not in (10,6,2,0):
        stretch = 6  # default="6": 画面サイズに合わせる

    # 配置スタイルを設定
    style_key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop",
        0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(style_key, "WallpaperStyle", 0, winreg.REG_SZ,
                      str(stretch))
    winreg.SetValueEx(style_key, "TileWallpaper", 0, winreg.REG_SZ,
                      "1" if tiled else "0")
    winreg.CloseKey(style_key)
    return


def set_img_to_wp(img, typ='.bmp'):
    t0 = dbg_time()

    cache_dir = os.path.join(tempfile.gettempdir(),"wp_cache")
    os.makedirs(cache_dir, exist_ok=True)
    for f in glob.glob(cache_dir+'\\*.*'):
        try:
            os.remove(f)
        except:
            pass

    fname = f'temp_wallpaper{time.time_ns()}'+typ

    try:
        image_path = os.path.abspath(os.path.join(cache_dir,fname))
        img.save(image_path)

        if DEBUG:
            dbg_time("save", t0)
    except:
        print('Temporaly save Error')
        return

    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE   = 0x01
    SPIF_SENDCHANGE      = 0x02
    
    flags = SPIF_UPDATEINIFILE  # | SPIF_SENDCHANGE

    ret = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, image_path, flags
    )

    if DEBUG:
        print('Set Wallpaper: Error=', ctypes.GetLastError())

    return


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def get_screens():
    # コールバック関数の型を定義
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )

    # ディスプレイ情報を格納するリスト
    monitors_info = []

    # コールバック関数の実装
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        # rect.left, rect.top は仮想画面上でのそのモニターの開始座標
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        monitors_info.append(
            {
                "handle": hMonitor,
                "width": width,
                "height": height,
                "rect": (rect.left, rect.top, rect.right, rect.bottom),
            }
        )
        return True  # Trueを返すと列挙を継続、Falseで中断

    # 高DPI環境で正しい物理ピクセル数を取得するための設定
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # 古いOSなどの対策

    # 列挙を実行
    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, MonitorEnumProc(callback), 0
    )

    """
    print(f"検出されたディスプレイ数: {len(monitors_info)}\n")
    for i, info in enumerate(monitors_info, 1):
        print(f"--- ディスプレイ {i} ---")
        print(f"  解像度: {info['width']} x {info['height']}")
        print(
            f"  位置座標 (左, 上, 右, 下): {info['rect']}"
        )  # メインモニターの左上が (0, 0)
    """

    return monitors_info

