# 茨城版コロナ対策サイト スクレイピングプログラム

## 実行前に
 - Tesseract OCRをインストールしてください。
 - 以下のコードを毎回実行してください。<br>
  ```
  python -m pip install --upgrade pip
  pip install --upgrade -r requirements.txt
  pip freeze > requirements.lock
  ```

## 操作方法
https://docs.google.com/document/d/1T-RDNjKuoye6BJ33di50_brNFsLg7iL4SKlclJd9rVg

## ファイル一覧と対応するスプレッドシートのシート
 - patients .py - 陽性患者属性
 - summary .py - 陽性者の状況