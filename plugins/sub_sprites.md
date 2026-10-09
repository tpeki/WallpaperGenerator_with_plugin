## 1. `SpriteSet` クラス

`SpriteSet` は、複数のスプライトデータ（パターン定義、色情報、画像サイズなど）を管理・操作するための中心的なデータ構造クラスです。   

### 主な属性（メンバ変数）

- **`self.name`**: スプライトセットの名前。   
- **`self.desc`**: セットの説明文。   
- **`self.sprites`**: 辞書形式 `{スプライト名: スプライトデータリスト}` で定義を保持。   
- **`self.enabled`**: 有効化されているスプライト名のリスト。   
- **`self.internal_set` / `self.internal_name`**: モジュール内蔵（デフォルト）のスプライトデータ（`INT_SPRITES`）およびそのセット名。   

### 主なメソッド

- **`set_internal(name, sprite_set)`**: 内蔵スプライトセットを登録・再設定します。   
- **`load_internal()`**: 内蔵スプライトセットを自身のスプライトデータとして読み込みます。   
- **`set_pattern(set_name, patterndic, desc)`**: 外部から渡された辞書データをもとにスプライトセットを構築します。   
- **`list()` / `get(label)` / `size(label)`**: 登録されているスプライト名のリスト取得、データ取得、およびサイズ `(w, h)` の取得を行います。   
- **`trim(label, size)`**: スプライトを指定サイズに切り抜き/余白追加してサイズを変更します。   
- **`image(label)`**: 指定したスプライトラベルから PIL の Image オブジェクトを生成して返します。   
- **`merge_pdic(appendix)`**: 既存のスプライトセットに別のスプライト辞書をマージします（重複キーは保持）。   
- **`update_sprite(label, sprdat, add_only)`**: 指定したラベルのスプライトデータを更新（登録）します。   
- **`add_bytext(label, pattext)`**: テキスト形式のパターン行のリストからスプライトを追加します。   
- **`add_byimage(label, image, transparent)`**: PIL 画像オブジェクトからスプライトデータへ変換して追加します。   

## 2. モジュールの関数一覧

機能カテゴリごとに整理した関数一覧です。

### ① スプライトファイル操作（読込・保存）

- **`sprfile_list(directory, zfile)`**
  - 指定ディレクトリから `.spr` ファイル名のリストを取得します。   
- **`load_spr(file, directory, zfile)`**
  - テキスト形式の `.spr` ファイルを解析し、スプライト辞書データと説明文を返します。   
- **`save_spr(file, pdic)`**
  - スプライト辞書データを圧縮し、`.spr` ファイル（SJIS エンコーディング）へ保存します。   
- **`str_to_tuple(s)`**
  - テキストの 1 行（カンマ区切り文字列）を解析し、数値パターンや色コード、コマンドのタプルに変換します。   
- **`dtos(data)`**
  - 内部のデータ構造（数値やリスト）を SPR 形式の CSV 文字列に相互変換します。   
- **`compress(buf)`**
  - 動的計画法（DP）を用いて、繰り返しのパターン行を `,rep<n>` や `,turnover` などの圧縮マクロ行に短縮・最適化します。   

### ② 画像ファイル（ビットマップ）からの変換・インポート

- **`reduce_cpr(img, colors_per_row)`**
  - PIL 画像に対し、1行あたりの色数を減色（クオンタイズ）処理します。   
- **`conv_spr(img, transparent_color)`**
  - 画像ピクセルデータを走査し、SPR 形式のテキストデータ列に変換します。   
- **`read_and_conv(file, trans)`**
  - 画像ファイルを読み込み、リサイズ処理・透過色指定を行った上でスプライトデータタプル群に変換します。   
- **`dump_sprites(outdir, sprites)`**
  - `SpriteSet` 内のスプライトを全件 `.png` 画像として指定フォルダに一括出力（ダンプ）します。   

### ③ スプライトパターンのデータ整形・演算

- **`and_pat(orig, pat, n)`**
  - 多重パターンの重ね合わせ（ビットマスクの畳み込み）を行い、インデックス文字列を作成します。   
- **`sprite_pattern(name, sprites)`**
  - 圧縮マクロ（`,rep`, `,turnover`）を展開し、スプライトを「行ごとのピクセル色番号文字列と対応カラーリスト」に復元します。   
- **`format_line_for_dtos(line)`**
  - 内部の `[patterns, colors]` データを、`compress()` や `dtos()` で扱える正しい SPR 記法文字列へフォーマットします。   
- **`pattern_to_spr(pat_list, do_compress=True)`**
  - 展開されたスプライトパターンリストから、ビットマスクとカラー配列の内部データ構造を復元（必要に応じて圧縮）します。   
- **`get_sprite_by_name(name, sprites)`**
  - 指定した名前のスプライトを PIL 画像として取得します（未登録の場合は 8x8 の空画像を返します）。   

### ④ 描画およびパレット計算

- **`draw_oneline(dr, pat, colors, y)`**
  - PIL ImageDraw を使い、スプライトの 1 行分を画像へ描画します。   
- **`sprite_image(pat)`**
  - 展開後のパターンデータをもとに PIL RGBA 画像を生成します。   
- **`palette_extract(img, max_colors=16)`**
  - 画像内で使用頻度の高い色を上位 N 色（デフォルト16色）抽出します。   
- **`palette_draw(palette, trans=None)`**
  - パレットの色見本画像（UI表示用）を生成します。   
- **`palette_img(img, trans=None)`**
  - 画像からパレットを抽出し、そのパレット描画画像と抽出カラーリストをセットで返します。   

### ⑤ GUI画面（TkEasyGUI）連携関数

- **`xy_keep_aspect(img)`**
  - プレビュー領域のアスペクト比を維持したリサイズ後の幅と高さを計算します。   
- **`update_preview(wn, img, cpr, trans)`**
  - 減色適用後のプレビュー画像とパレットを GUI ウィンドウに反映します。   
- **`check_transparent(wn, palette, trans)`**
  - 指定された透過色が抽出パレットに含まれているかを判定・補正します。   
- **`create_spr(spriteset, directory)`**
  - 単一画像を読み込んで減色・透過指定・登録を行う GUI ダイアログを表示・処理します。   
- **`bulk_import(directory)`**
  - フォルダ内の画像群を一括読み込み・スプライトデータ化する GUI ダイアログを表示・処理します。   

### ⑥ 汎用ヘルパー関数

- **`safeint(s, default=0)`**
  - 文字列（10進数および `0x` から始まる16進数）を安全に整数へ変換します。   