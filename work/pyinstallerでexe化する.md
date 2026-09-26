## pyinstallerでコンパイル

- 不要なモジュールまで組み込むと手間なので、venvを設定する

  - ```
    % py -m venv .venv
    % .venv\Scripts\activate
    % python -m pip install --upgrade pip
    % pip install pillow numpy fonttools TkEasyGUI pyinstaller
    ```

- このディレクトリから build.bat と WallpaperGenerator.spec を wallpaper.pyw と同じディレクトリに配置

- build.bat を起動すると、dist の下にexeファイルとplugins, samples 一式を作成する

- `WallpaperGenerator.exe, plugins/*.*, samples/*.*` をまとめて配置してできあがり

- ```
  - dist/ 
  - └─ WallpaperGenerator.exe
  -    ├─ plugins/ 
  -    │   ├─ mod_sprites.py 
  -    │   └─ ...
  -    ├─ samples/
  -    │   └─ ...
  ```

  

## コンパイルで必要だった修正

- plugins,samplesはそのままコピーするので、dataに加えてCOLLECTしない

- TkEasyGUIを使ったスクリプトをpyinstallerでコンパイルした際、Buttonがデフォルトでuse_ttk_buttons=True になってしまう。(インタプリタだとtkButtonを使うのでBGカラーの指定ができる)

  - →  以下のコードをWallpaper.pywの先頭に入れて、Buttonのデフォルトパラメータとしてuse_ttk_buttons=Falseが設定されるように定義の上書きを行う

  - ```
    _Button = sg.Button
    sg.Button = lambda text, **k: _Button(
          text, **{**{'use_ttk_buttons': False}, **k}
      )
    
    ```

- exe化すると実行環境とファイルの置き場所が違うことが一般的なので、moduleをサーチする場所を実行ファイルの場所を基準に考える

  - ```
    # pyinstallerで固めても大丈夫なbasedir設定
    
      def get_basedir():
          if getattr(sys, 'frozen', False):
              base_dir = pa.dirname(pa.abspath(sys.executable))
              if base_dir not in sys.path:
                  sys.path.insert(0, base_dir)
          else:
              base_dir = pa.dirname(pa.abspath(__file__))
    
          return base_dir
    ```

- sub_sprites.py のように将来の共通化のために切り出したファイルも、モジュール由来のものならpluginsに置きたい

  - pluginsをモジュールとして扱うため、`plugins/__init__.py` を置く。

- モジュールの開発時はモジュール単体を実行して `__name__ == '__main__'` のifブロックを使って動作チェックをすることが多い。しかし、pluginsに配置してしまうと、wall_common.pyやfiledialog.pyをimportできない。このため、 _4debug.py というデバッグ用モジュールを用意して、sys.pathに親ディレクトリを追加する。

- build.batの中でplugins、samplesをdistにコピーする

  - robocopyでディレクトリ丸ごとコピー (windowsなので cp -r は無かった)

