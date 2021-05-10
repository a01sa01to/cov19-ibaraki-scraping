# ----- IMPORT ----- #
import os
import pathlib
import re
from urllib.parse import urljoin

import cv2
import pyperclip
import pytesseract
import requests
from bs4 import BeautifulSoup

# ----- SETTINGS ----- #
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
}
url = "https://www.pref.ibaraki.jp/1saigai/2019-ncov/index.html"

# ----- FUNCTIONS ----- #


def fetch_html(url, parser="html.parser"):
  req = requests.get(url, headers=headers)
  req.raise_for_status()
  soup = BeautifulSoup(req.content, parser)
  return soup


def fetch_file(url, dir="."):
  path = pathlib.Path(dir, pathlib.PurePath(url).name)
  path.parent.mkdir(parents=True, exist_ok=True)
  req = requests.get(url)
  req.raise_for_status()
  with path.open(mode="wb") as fileWrite:
    fileWrite.write(req.content)
  return path.resolve()


# ----- GET DATE ----- #
print("Getting date...")
soup = fetch_html(url)
publish_date = (
    soup.select_one("table tr td.bg_red h3").get_text(
        strip=True).replace("発表資料", "")
)
print("Using Data as of {}".format(publish_date))

# ----- GET CUMULATIVE TOTAL ----- #
print("Getting Cumulative Total...")
data = [int(soup.select_one("strong > a").get_text(strip=True).rstrip("名").replace(",", ""))]


# ----- GET IMAGE ----- #
print("Fetching Image file...")
img_src = (
    soup.find("h2", text="茨城県内の新型コロナウイルス感染症の陽性者の状況")
    .find_next_sibling("p")
    .find("img", alt=re.compile("の陽性者の状況$"))
    .get("src")
)

link_img = urljoin(url, img_src)
path_img = fetch_file(link_img)

try:
  from PIL import Image
except ImportError:
  import Image

print("Reading Image...")
img = cv2.imread(str(path_img))

# ----- 黒文字抽出 ----- #
print("Extracting Gray text...")
bin_img = cv2.inRange(img, (0, 0, 0), (100, 200, 200))
# cv2.imwrite("summary_ocrBlack.png", bin_img)  # ファイル出力

# ----- 膨張 ----- #
print("Expanding the Text...")
kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
img = cv2.dilate(bin_img, kernel)
# cv2.imwrite("summary_ocrBlack_expand.png", img)  # ファイル出力

# ----- 反転 ----- #
print("Reversing Color...")
dst = cv2.bitwise_not(img)
# cv2.imwrite("summary_ocrRotate.png", dst)  # ファイル出力

# ----- テキスト抽出 ----- #
# ※日本語のテキストは抽出にずれがありますが、利用するのは数字のみなのでずれはなくなるかと...
print("Analyzing the Image...")
txt = (
    pytesseract.image_to_string(dst, lang="jpn", config="--psm 6")
    .strip()
    .replace(" ", "")
)
# print(txt)

# ----- データ配列に入れる ----- #
data.extend(list(map(int, re.findall("(\d+)人", txt))))

# data[0] : 陽性累計
# data[1] : 療養中
# data[2] : 入院中
# data[3] : 重症
# data[4] : 中等症
# data[5] : 軽症
# data[6] : 自宅療養
# data[7] : 宿泊施設療養
# data[8] : 回復
# data[9] : 死亡
# data[10] : その他


print(data)

# ----- COPY TO CLIPBOARD ----- #
s = ""
for i in range(len(data)):
  if i is not 2:
    s += str(data[i]) + "\n"

try:
  pyperclip.copy(s)
  print("\nCopied to Clipboard!")
except:
  print("\nFailed to copy")

if data[2] != data[3] + data[4] + data[5]:
  print("※入院中との合計があいません")
if data[1] != data[2] + data[6] + data[7]:
  print("※療養中との合計があいません")
if data[0] != data[1] + data[8] + data[9] + data[10]:
  print("※陽性者累計があいません")

# ----- REMOVE FILE ----- #
os.remove(path_img)
