# class Tapes:

 ## [Attributes]
- patterns = {}
- name = ''
- desc = ''
- internal_set = copy.deepcopy(INT_PATTERNS)
- internal_name = INT_TAPESET

 ## [methods]
- set_internal (name=None, pattern_dic=None): 
    - load_internalで読み込むパターンセットの設定

- load_internal (): 
    - 内蔵パターンセットを読み込み

- list ():
    - パターンセットに登録されているパターン名のリスト

- get (label):
    - パターンの取得

- size (label):
    - パターンの基本構成サイズ

- image (label, length=None):
    - パターンで画像を生成

- set_patterns (set_name, pattern_dic)
    - パターンセットを設定:

- merge_patterns (appendic):
    - パターンセット(辞書)をマージ(既存は書き換えない)

- add_pattern (label, pattern)
    - パターンセットにパターンを追加:

- pat_to_text (label):
    - 1パターン分のテキスト

- patterns_to_text ():
    - パターンセットをセーブ用の文字列にする

- text_to_pat (buf):
    - [パターン名]行から続くパターンテキストを読み込んで辞書レコードに変換

- text_to_patterns (buf):
    - テキストからパターンを読み込んでテープセットに登録

- load_file (file_name, directory=None, add_zip=None):
    - パターンセットをファイルから読み込む
    - ZIPファイル対応
    - dir,zipがNoneならデフォルトディレクトリ、デフォルトアーカイブを探索

- save_file (file_name=None, directory=None):
    - パターンセットをファイルに書き出す(ZIP非対応)
    - return num of saved patterns


# class Tyrolean:

 ## [Attributes]
- pattern = copy.deepcopy(pattern)
- palette = copy.deepcopy(palette)
- sprites = []   # sprite名のリスト[(sls, spr), ... ]
- sprdic = {}  # spritesの登場スプライトパターン '{sls}&{spr}': [[sprtext]]
- imglist = []  # spriteイメージ(重複あり) renderで生成
- spr_h = 0
- height = 0
- outline = tyrolean_preserv\['basic']\['outline']
- margin = tyrolean_preserv\['basic']\['margin']
- spacing = tyrolean_preserv\['basic']\['spacing']
- flip = tyrolean_preserv\['basic']\['flip']
- twopt = tyrolean_preserv\['basic']\['twopt']
- texture = 1  # テクスチャ {0:なし(マスキングテープ) 1: 弱(通常)  2; 強(サテン調)}
- p_height = tw  # パターンの最大幅
- p_width = len(self.pattern)  # テープの最小繰り返し幅
- image = None  # image()で後から生成 -> いらないかも

 ## [Initialize]

- \__init__ (pattern, palette=None):
  - かならずパターンを指定する
  - パレットは指定されなければ基本パレットを利用


 ## [Methods]
- sprite_height (limit=0):
    - limit=0:最大sprite高 n:制限高
- pattern_size ():
    - 
- weave (length, height=None):
    - テープイメージを生成する。高さ指定が無ければ、self.heightの設定に従う
    - height=0:sprite_height based, n:limitted_height, None:default
- render_sprites(self)
    - 設定されているスプライトリストのスプライトを画像出力して、self.imglist[]に格納。これをパターン上に順次pasteすることでテープになる。
- merge_sprdic(self, setname, sdic):
    - 設定されているスプライト情報を上書き追加




## サポート関数

- safe_int(s)  # 文字列から整数へ変換
- ssname(s1,s2)  # s1&s2 を返す ただし、元文字列s1,s2中の'&'は'%26'に変換 (Tyrol内のスプライト辞書で使用)
- 

