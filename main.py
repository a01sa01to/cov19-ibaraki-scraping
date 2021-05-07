# ----- IMPORT ----- #
import datetime
import os
import pathlib
import re
from urllib.parse import urljoin

import comtypes.client
import pandas as pd
import pdfplumber
import pyperclip
import requests
from bs4 import BeautifulSoup
from pdf2docx.main import parse

# ----- SETTINGS ----- #
HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
}
JST = datetime.timezone(datetime.timedelta(hours=+9))
NOW = datetime.datetime.now(JST).replace(tzinfo=None)
url = "https://www.pref.ibaraki.jp/1saigai/2019-ncov/index.html"

# ----- FUNCTIONS ----- #


def fetch_html(url, parser="html.parser"):
  req = requests.get(url=url, headers=HEADERS)
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


def pdf2data(pdfFile):
  with pdfplumber.open(pdfFile) as pdf:
    dataStr = []
    for page in pdf.pages[1:]:
      try:
        table = page.extract_table()
        _ = pd.DataFrame(table[1:], columns=table[0])
        if (_.columns[0] == "判明日") or (_.columns[1] == "判明日"):
          dataStr.append(_)
      except:
        continue
  data = pd.concat(dataStr)
  data.replace(["―", "－", ""], pd.NA, inplace=True)
  data.dropna(how="all", inplace=True)
  return data.reset_index(drop=True)


def str2date(st):
  data = (
      st.str.extract("(\\d{1,2})月(\\d{1,2})日")
      .rename(columns={0: "month", 1: "day"})
      .fillna(0)
      .astype(int)
  )
  data["year"] = NOW.year
  _ = pd.to_datetime(data, errors="coerce")
  data["year"] = data["year"].mask(_ > NOW, data["year"] - 1)
  return pd.to_datetime(data, errors="coerce")


def docx2pdf(docxPath, pdfPath):
  word = comtypes.client.CreateObject("Word.Application")
  doc = word.Documents.Open(str(docxPath))
  doc.SaveAs(str(pdfPath), FileFormat=17)
  doc.Close()
  word.Quit()


# ----- GET DATE ----- #
print("Getting date...")
soup = fetch_html(url)
publish_date = (
    soup.select_one("table tr td.bg_red h3").get_text(
        strip=True).replace("発表資料", "")
)
print("Using Data as of {}".format(publish_date))
# ----- GET PREF ----- #
print("\n\nFetching Pref PDF...")
tag_pref = soup.find(
    "a", class_="icon_pdf", text=re.compile("^新型コロナウイルス感染症患者の発生及び退院・退所等について")
)
link_pref = urljoin(url, tag_pref.get("href"))
path_pref = fetch_file(link_pref)
path_prefDocx = pathlib.Path(str(path_pref).replace(".pdf", ".docx")).resolve()
print("\nConverting to Docx...")
parse(path_pref, path_prefDocx)
print("\nReconverting to PDF...")
docx2pdf(path_prefDocx, path_pref)
print("\nAnalyzing Pref PDF...")
data_pref = pdf2data(path_pref)
data_pref["管轄ID"] = 0
data_pref["新規\n濃厚"] = data_pref["新規 \n濃厚"]
print("\nAll Done! Length: {}".format(len(data_pref)))

# ----- GET MITO ----- #
print("\n\nFetching Mito PDF...")
tag_mito = soup.find(
    "a", class_="icon_pdf", text=re.compile("^【水戸市発表】新型コロナウイルス感染症患者の発生について")
)
if tag_mito is not None:
  link_mito = urljoin(url, tag_mito.get("href"))
  path_mito = fetch_file(link_mito)
  print("\nAnalyzing Mito PDF...")
  data_mito = pdf2data(path_mito)
  data_mito["管轄ID"] = 1
  print("\nAll Done! Length: {}".format(len(data_mito)))
else:
  print("\nAll Done! Length: 0")


# ----- ANALYZE ----- #
print("\n\nGenerating Results...")
if tag_mito is not None:
  data_all = pd.concat([data_pref, data_mito])
else:
  data_all = pd.concat([data_pref])
data_all["状態"] = (
    data_all["発症日"].where(data_all["発症日"] == "症状なし").replace({"症状なし": "無症状"})
)
data_all["職業"] = data_all["職業"].replace(
    {"生徒": "学生", "児童": "学生", "非公表": "", "確認中": ""})
data_all["性別"] = data_all["性別"].replace({"男子": "男性", "女子": "女性"})
data_all["職業"] = data_all["職業"].mask(data_all["年代"] == "未就学児", "未就学児")
data_all["年代"] = (
    data_all["年代"]
    .replace({"未就学児": "10歳未満"})
    .str.replace("歳代", "代")
    .replace("100代", "100歳以上")
)
data_all["患者_濃厚接触者フラグ"] = data_all["新規\n濃厚"].replace({"新規": 0, "濃厚": 1})
data_all["発症日"] = str2date(data_all["発症日"])
data_all["発症日ISO"] = data_all["発症日"].apply(
    lambda d: pd.Timestamp(d, tz=None)
    .isoformat()
    .replace("NaT", "")
    .replace("T00:00:00", "")
)

data_all.rename(
    columns={
        "発症日ISO": "発症_年月日",
        "居住地": "患者_居住地",
        "年代": "患者_年代",
        "性別": "患者_性別",
        "職業": "患者_職業",
        "状態": "患者_状態",
        "備考（疑われる感染経路）": "備考",
    },
    inplace=True,
)
data_all["備考"] = data_all["備考"].str.replace("、", "感染;") + "感染"
data_all["備考"] = data_all["備考"].str.replace("他県感染", "県外の陽性者 接触")
data_all["備考"] = data_all["備考"].str.replace("県外感染", "県外の陽性者 接触")

data_all = (
    data_all.reset_index().sort_values(
        by=["管轄ID", "index"]).reset_index(drop=True)
)
data_all = data_all.reindex(
    [
        "発症_年月日",
        "患者_居住地",
        "患者_年代",
        "患者_性別",
        "患者_職業",
        "患者_状態",
        "患者_症状",
        "患者_渡航歴の有無フラグ",
        "患者_濃厚接触者フラグ",
        "検査方法",
        "備考",
    ],
    axis=1,
)

# ----- OUTPUT ----- #
data_all.to_csv("080004_ibaraki_covid19_patients.csv", encoding="utf_8_sig")
data_all.to_csv("080004_ibaraki_covid19_patients.tsv", sep="\t", encoding="utf_8_sig", index=False)

# ----- COPY TO CLIPBOARD ----- #
with open("080004_ibaraki_covid19_patients.tsv", "r", encoding="UTF-8") as f:
  file = f.readlines()

s = ""
for i in range(len(file)):
  if i == 0:
    continue
  s += file[i]
try:
  pyperclip.copy(s)
  print("\nCopied to Clipboard!")
except:
  print("\nFailed to copy")

# ----- REMOVE FILE ----- #
os.remove(path_pref)
os.remove(path_prefDocx)
if tag_mito is not None:
  os.remove(path_mito)
os.remove("080004_ibaraki_covid19_patients.csv")
os.remove("080004_ibaraki_covid19_patients.tsv")
