# `Q: `

`https://github.com/tpeki/WallpaperGenerator_with_plugin`

 `にあるスクリプトをWindowsのexeファイルにしたい。`
 `pyinstallerなどでパッケージングする際の注意事項などを教えてほしい`

------

# A:

はい。リポジトリを実際に確認すると、**このプログラムは PyInstaller で exe 化できますが、普通の Python GUI アプリより少し注意点があります**。

特に重要なのは、

1. `mod_*.py` / `efx_*.py` を動的に読み込んでいる
2. `samples` を実行時に参照している
3. `fontTools` が Windows のフォントを直接調べる
4. `wallpaper.pyw` が GUI 用なのでコンソールを出したくない
5. 現在のプラグイン探索コードに、exe 化すると問題になりそうな箇所が1つある

という点です。

------

# 1. まず結論：最初は `--onedir` を推奨

PyInstaller には大きく

```text
--onedir
    WallpaperGenerator/
        wallpaper.exe
        *.dll
        *.pyd
        ...
```

と

```text
--onefile
    WallpaperGenerator.exe
```

があります。

このプロジェクトの場合、**最初は `--onedir` で作るのがかなりおすすめ**です。

PyInstaller のデフォルトも `onedir` です。`onefile` は内部的には起動時に一時ディレクトリへ展開してから実行します。([PyInstaller](https://pyinstaller.org/en/stable/man/pyinstaller.html?utm_source=chatgpt.com))

このプログラムは「プラグインをファイルとして探す」という設計になっているので、`onedir` のほうが設計との相性がいいです。

例えば、

```text
WallpaperGenerator/
    WallpaperGenerator.exe
    _internal/
    plugins/
        mod_stripe.py
        mod_tiles.py
        mod_tartan.py
        ...
    samples/
        ...
```

のようにできます。

------

# 2. 一番重要なのは「動的 import」

現在の `wallpaper.pyw` は普通の

```python
import mod_stripe
```

ではありません。

実際には、

```python
import importlib.util as impl
import glob
```

を使って、

```python
for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
    ...
    spec = impl.spec_from_file_location(modname, modf)
    module = impl.module_from_spec(spec)
    ...
    spec.loader.exec_module(module)
```

という仕組みで `mod_*.py` を探してロードしています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/wallpaper.pyw))

同じことを `efx_*.py` に対しても行っています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/wallpaper.pyw))

これは PyInstaller にとって重要です。

PyInstaller は通常、

```python
import mod_stripe
```

なら依存関係を解析できますが、

```python
importlib.util.spec_from_file_location(...)
```

のような動的ロードまでは通常の import 解析だけでは把握できません。

PyInstaller 公式にも、通常の解析から見えない import は `--hidden-import` 等で指定する必要があると説明されています。([GitHub](https://github.com/pyinstaller/pyinstaller/blob/develop/doc/spec-files.rst?utm_source=chatgpt.com))

ただし、今回の場合は**hidden-import だけで解決するより、現在のプラグイン方式をそのまま活かす方法のほうがよい**と思います。

------

# 3. そして、現在のコードには exe 化前に直したい箇所があります

ここです。

```python
if plugin_dir is None:
    plugin_dir = pa.dirname(__file__)

plugin_pat = 'mod_*.py'

for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
    ...
    spec = impl.spec_from_file_location(modname, modf)
```

`glob(..., root_dir=plugin_dir)` は**検索対象を `plugin_dir` にしますが、返すファイル名は基本的に相対名**です。

つまり、

```python
glob.glob('mod_*.py', root_dir='C:/xxx')
```

で、

```python
['mod_stripe.py', 'mod_tiles.py', ...]
```

が返ってきます。

その後、

```python
spec_from_file_location(modname, modf)
```

としているので、`mod_stripe.py` を **現在のカレントディレクトリから探す**ことになります。

Python スクリプトとして現在のディレクトリから起動しているときは問題が表面化しにくいですが、exe 化すると、

```text
exeをダブルクリック
↓
カレントディレクトリは必ずしもexeの場所ではない
```

という問題が出ます。

なので、ここは例えば、

```python
for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
    modpath = pa.join(plugin_dir, modf)

    modname = pa.splitext(modf)[0]

    if modname.startswith('mod_'):
        modname = modname[4:]

    spec = impl.spec_from_file_location(modname, modpath)
```

としておくのが安全です。

`efx` 側も同様です。

```python
for modf in glob.glob(plugin_pat, root_dir=plugin_dir):
    modpath = pa.join(plugin_dir, modf)

    ...
    spec = impl.spec_from_file_location(modname, modpath)
```

**これは PyInstaller 以前に、`--plugin_dir` の指定方法によっては普通の Python 実行でも起こり得る問題なので、修正しておく価値があります。**

------

# 4. `samples` は必ずデータとして同梱する

ここも重要です。

例えば `mod_tartan.py` では、

```python
DATA_DIR = 'samples'
ZIPFILE = 'tartan.zip'
```

としており、`samples` 以下の `.ttn` ファイルを検索しています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/mod_tartan.py))

`mod_sprites.py` も、

```python
DATA_DIR = 'samples'
ZIPFILE = 'sprites.zip'
```

を使用しています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/mod_sprites.py))

これらは `.py` ではないので、PyInstaller が自動的に全部入れてくれるとは考えないほうがいいです。

PyInstaller では `--add-data` または spec ファイルの `datas=` を使ってデータファイルを明示的に追加できます。([GitHub](https://github.com/pyinstaller/pyinstaller/blob/develop/doc/spec-files.rst?utm_source=chatgpt.com))

例えば Windows なら、

```bat
pyinstaller ^
    --onedir ^
    --windowed ^
    --name WallpaperGenerator ^
    --icon=wallpaper.ico ^
    --add-data "samples;samples" ^
    wallpaper.pyw
```

のような形です。

------

# 5. ただし、プラグインの `.py` も考える必要がある

現在の設計では、

```text
mod_*.py
efx_*.py
```

そのものを実行時に読み込んでいます。

したがって、exe の中にプラグインを入れるなら、例えば

```text
WallpaperGenerator/
    WallpaperGenerator.exe
    plugins/
        mod_argyle.py
        mod_bauhaus.py
        ...
        efx_impose.py
        efx_lines.py
        efx_shade.py
```

という構造にするのが扱いやすいです。

PyInstaller の `datas` は Python モジュールとして解析するためではなく、**実ファイルとして配置するため**に使えます。([PyInstaller](https://pyinstaller.org/en/stable/spec-files.html?utm_source=chatgpt.com))

例えば spec ファイルなら、

```python
datas = [
    ('mod_*.py', '.'),
    ('efx_*.py', '.'),
    ('samples', 'samples'),
]
```

のような方向性です。

ただし、実際には `datas` の指定方法をもう少し丁寧にしたほうがいいので、私は**このプロジェクト専用の `.spec` を作る方法を推奨します**。

------

# 6. `onefile` にする場合は少し事情が変わる

`--onefile` にすると、

```text
WallpaperGenerator.exe
```

だけにできます。

これは配布には非常に便利です。

ただし起動時に PyInstaller が内部ファイルを一時ディレクトリへ展開します。

公式ドキュメントでは、この一時ディレクトリは `_MEIxxxxxx` とされており、`sys._MEIPASS` からアクセスできます。さらに現在の PyInstaller では、`__file__` もバンドル内の正しいパスになるので、データファイルの参照には `__file__` を使う方法が推奨できます。([GitHub](https://github.com/pyinstaller/pyinstaller/blob/develop/doc/runtime-information.rst?utm_source=chatgpt.com))

つまり、

```python
pa.dirname(__file__)
```

を使っている現在の設計は、**PyInstallerとの相性は悪くありません**。

これはむしろ好都合です。

------

# 7. `fontTools` は特に問題なさそう

`efx_impose.py` では、

```python
from fontTools.ttLib import TTFont
```

を使っています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/efx_impose.py))

また、

```python
SysFont_Dir = r'c:\Windows\Fonts'
```

として、Windows のフォントディレクトリを直接列挙しています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/efx_impose.py))

つまり、

```text
exeにWindowsフォントを全部入れる
```

必要はありません。

これは実行先 Windows の

```text
C:\Windows\Fonts
```

をそのまま利用します。

むしろフォント関連では、

```python
from fontTools.ttLib import TTFont
```

が PyInstaller に正常に収集されているかを確認するほうが重要です。

------

# 8. Arial の扱いも少し注意

`batch_generate()` では、

```python
font = ImageFont.truetype('arial.ttf', 10)
```

となっています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/wallpaper.pyw))

これは PyInstaller に Arial を同梱する話ではありません。

Pillow が Windows のフォントを見つけられる環境なら基本的には問題ありません。

ただし exe 化後にここで

```text
cannot open resource
```

などが出る場合は、この部分を Windows のフォントパスから取得する方法に変更したほうが堅牢です。

GUI 通常使用では `batch_generate()` を使わないので、まずは後回しでいいと思います。

------

# 9. `wallpaper.ico` はそのまま exe アイコンに使える

リポジトリには、

```text
wallpaper.ico
```

があります。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin))

これは、

```bat
--icon=wallpaper.ico
```

でそのまま利用できます。

例えば、

```bat
pyinstaller ^
    --onedir ^
    --windowed ^
    --name WallpaperGenerator ^
    --icon=wallpaper.ico ^
    wallpaper.pyw
```

です。

------

# 10. `--windowed` を使う

元ファイルが `.pyw` なので、目的としては当然、

```text
コンソール窓を出さない
```

でしょう。

PyInstaller では

```bat
--windowed
```

または

```bat
--noconsole
```

を使います。

そのため、

```bat
pyinstaller --onedir --windowed ...
```

でよいです。

ただし**最初のデバッグ段階では `--windowed` を付けないことを強くおすすめします。**

例えば、

```bat
pyinstaller --onedir wallpaper.pyw
```

としておけば、

```text
WallpaperGenerator.exe
```

をコマンドプロンプトから起動して、

```text
Loaded 28 pattern modules.
Loaded 3 after-effect modules.
```

などのメッセージや、Python の traceback を確認できます。

動作確認が終わってから、

```bat
--windowed
```

にします。

------

# 11. さらに重要：`--plugin_dir` をどうするか

このプロジェクトの「プラグイン方式」は exe 化との相性を考えると、むしろ面白いところです。

現在、

```text
--plugin_dir dirname
```

が用意されています。README にもプラグイン読み込みディレクトリを指定でき、デフォルトは実行スクリプトのディレクトリと説明されています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin))

これを活かして、

```text
WallpaperGenerator/
    WallpaperGenerator.exe

    plugins/
        mod_stripe.py
        mod_tiles.py
        ...
```

として、

```text
WallpaperGenerator.exe --plugin_dir plugins
```

とする設計もできます。

さらに一歩進めるなら、

```text
WallpaperGenerator/
    WallpaperGenerator.exe
    plugins/
        ...
    samples/
        ...
```

という**完全なポータブルアプリ**にするのがかなり自然だと思います。

------

# 12. 私なら「exe本体」と「プラグイン」を分けます

このプロジェクトの場合、個人的には次の構成をおすすめします。

```text
WallpaperGenerator/
│
├─ WallpaperGenerator.exe
│
├─ plugins/
│   ├─ mod_argyle.py
│   ├─ mod_bauhaus.py
│   ├─ mod_bias.py
│   ├─ mod_chevron.py
│   ├─ ...
│   ├─ mod_tiles.py
│   ├─ mod_turtle.py
│   ├─ mod_waves.py
│   │
│   ├─ efx_impose.py
│   ├─ efx_lines.py
│   └─ efx_shade.py
│
└─ samples/
    ├─ sprites.zip
    ├─ tartan.zip
    ├─ ...
```

そして本体側は、

```python
PLUGIN_DIR = pa.join(pa.dirname(__file__), 'plugins')
```

として、

```python
search_modules(modlist, PLUGIN_DIR)
search_aftereffects(efxlist, PLUGIN_DIR)
```

とする。

こうすると、

**「PyInstallerで固めた本体」**

と

**「ユーザーが追加・変更できるプラグイン」**

が明確に分離できます。

これは現在の設計思想ともかなり合っています。

------

# 13. 逆に `--onefile` は「配布版」で考える

開発中は、

```text
onedir
```

で、

```text
WallpaperGenerator/
    WallpaperGenerator.exe
    _internal/
    plugins/
    samples/
```

として動作確認。

最終的に、

```text
WallpaperGenerator.exe
```

一個にしたいなら、

```text
onefile
```

を検討する。

という順序がいいです。

ただし、**外部プラグインを許可するなら onefile でも plugins フォルダは外に置く**ことになります。

例えば、

```text
WallpaperGenerator.exe
plugins/
    my_plugin.py
```

です。

------

# 14. このプロジェクトで最初に作るべき spec

私なら、まずこんな `WallpaperGenerator.spec` を作ります。

概念的には、

```python
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['wallpaper.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('samples', 'samples'),

        # 動的ロードするプラグイン
        ('mod_*.py', '.'),
        ('efx_*.py', '.'),
    ],
    hiddenimports=[],
    ...
)
```

という方向です。

ただし、ここは**実際のリポジトリの構造に合わせてもう少し正確に作ったほうがいい**です。

PyInstaller の spec ファイルは単なる設定ファイルではなく Python コードとして実行され、`Analysis` の `datas`、`binaries`、`hiddenimports` などを指定できます。([GitHub](https://github.com/pyinstaller/pyinstaller/blob/develop/doc/spec-files.rst?utm_source=chatgpt.com))

------

# 15. もう一つ、かなり大事なこと

現在のリポジトリは README に、

```text
pillow 12.0.0
TkEasyGUI 1.0.40
numpy 2.2.6
fonttools 4.63.0
```

を使用すると記載されています。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin))

なので、**普段使っているPython環境から直接 PyInstaller を実行するより、exe専用のvenvを作ったほうがいい**です。

例えば、

```bat
py -m venv buildenv
buildenv\Scripts\activate

python -m pip install --upgrade pip

pip install pillow==12.0.0
pip install TkEasyGUI==1.0.40
pip install numpy==2.2.6
pip install fonttools==4.63.0
pip install pyinstaller
```

として、

```bat
python -m PyInstaller ...
```

とする。

これなら、

```text
開発環境にたまたま入っていたライブラリ
```

が紛れ込むことを防げます。

------

# 16. 今回は「PyInstallerが難しい」のではなく「プラグイン構造」がポイント

整理すると、このプロジェクトの場合、

| 項目            | 注意度 | 対策                            |
| --------------- | ------ | ------------------------------- |
| NumPy           | ○      | 通常はPyInstallerで収集         |
| Pillow          | ○      | 通常はPyInstallerで収集         |
| TkEasyGUI       | ○      | 実機で確認                      |
| fontTools       | ○      | hidden import等を確認           |
| `mod_*.py`      | **◎**  | 動的ロードなので明示的に扱う    |
| `efx_*.py`      | **◎**  | 同上                            |
| `samples/`      | **◎**  | `--add-data` / spec             |
| Windows Fonts   | ○      | exeに同梱不要                   |
| `wallpaper.ico` | ○      | `--icon`                        |
| `winwall.py`    | ○      | Windows専用なのでそのままでよい |
| `.pyw` GUI      | ○      | `--windowed`                    |
| `--plugin_dir`  | **◎**  | exe化後の設計を決める           |
| `--onefile`     | △      | 最初は避ける                    |

という感じです。

------

## 私ならこう進めます

いきなり `onefile` にせず、

**第1段階**

```text
Python環境
 ↓
PyInstaller
 ↓
onedir
 ↓
全モジュール動作確認
```

↓

**第2段階**

```text
plugins/
samples/
を含めた配布用ディレクトリ構成を決定
```

↓

**第3段階**

```text
onefile化するか判断
```

とします。

特に今のコードでは、**`glob(..., root_dir=plugin_dir)` → `spec_from_file_location(..., modf)` の部分を先に直す**のがおすすめです。ここは exe 化でトラブルになりやすい箇所です。([GitHub](https://github.com/tpeki/WallpaperGenerator_with_plugin/blob/main/wallpaper.pyw))

もしよければ次に、**このGitHubの現在の構成を前提にして、そのまま `WallpaperGenerator.spec` と `build.bat` を作れる形まで具体化**できます。`onedir` 版→動作確認→`onefile` 版、という2段階の構成にするとかなり安全です。

(by ChatGPT)