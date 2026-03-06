#  Copyright (C) 2025-2026 m2k7m
#
#  The MIT License (MIT)
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import json
import os
import shutil
import sys
import time
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

if os.name == 'nt':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')

try:
    import i18n
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    if input("Missing libraries. Install them now? (y/n): ").strip().lower() == "y":
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-i18n", "arabic-reshaper", "python-bidi"])
        import i18n
        import arabic_reshaper
        from bidi.algorithm import get_display
    else:
        sys.exit("Libraries are required.")

CFG_FILE = Path("config.json")
LOCALES_DIR = Path("locales")
IMG_SIZES = [440, 260, 128, 64]

LOCALES_DIR.mkdir(exist_ok=True)

en_dict = {
    "prompt": "Press Space to continue or 'L' to change language: ",
    "choose": "Choose language (1: English, 2: Arabic): ",
    "wand_ask": "Wand library is missing. Install it now? (y/n): ",
    "wand_err": "Wand library is required.",
    "req_ask": "requests library is missing. Install it now? (y/n): ",
    "req_err": "requests library is required for URLs.",
    "fail_dl": "Download failed. Status: %{status}",
    "success": "Converted %{input} to %{output} successfully.",
    "timer": "Time taken: %{time} seconds",
    "enter_p": "Enter image path or URL: ",
    "no_in": "No input provided."
}

ar_dict = {
    "prompt": "اضغط مسطرة للاستمرار او مفتاح L لتغيير اللغة: ",
    "choose": "اختر اللغة (1 للانجليزية، 2 للعربية): ",
    "wand_ask": "مكتبة Wand غير موجودة. هل تريد تثبيتها؟ (y/n): ",
    "wand_err": "المكتبة مطلوبة لتشغيل الأداة.",
    "req_ask": "مكتبة requests غير موجودة. هل تريد تثبيتها؟ (y/n): ",
    "req_err": "المكتبة مطلوبة لمعالجة الروابط.",
    "fail_dl": "فشل تنزيل الصورة. كود الحالة: %{status}",
    "success": "تم تحويل %{input} إلى %{output} بنجاح.",
    "timer": "الوقت المستغرق: %{time} ثانية",
    "enter_p": "أدخل مسار الصورة أو الرابط: ",
    "no_in": "لم يتم إدخال شيء."
}

(LOCALES_DIR / "app.en.json").write_text(json.dumps({"en": en_dict}, ensure_ascii=False), encoding="utf-8")
(LOCALES_DIR / "app.ar.json").write_text(json.dumps({"ar": ar_dict}, ensure_ascii=False), encoding="utf-8")

i18n.load_path.append(str(LOCALES_DIR))
i18n.set('file_format', 'json')
i18n.set('filename_format', '{namespace}.{locale}.{format}')

def _(key, **kwargs):
    txt = i18n.t(f"app.{key}", **kwargs)
    if i18n.get('locale') == 'ar':
        return '\n'.join(get_display(arabic_reshaper.reshape(line)) for line in txt.split('\n'))
    return txt

lang = "ar"
if CFG_FILE.exists():
    with open(CFG_FILE, "r", encoding="utf-8") as f:
        lang = json.load(f).get("lang", "ar")

with open(CFG_FILE, "w", encoding="utf-8") as f:
    json.dump({"lang": lang}, f)

i18n.set('locale', lang)
i18n.set('fallback', 'en')

print(_('prompt'), end='', flush=True)

if os.name == 'nt':
    import msvcrt
    while True:
        k = msvcrt.getwch().lower()
        if k == ' ':
            print()
            break
        elif k == 'l':
            print()
            c = input(_('choose')).strip()
            lang = "en" if c == "1" else "ar"
            with open(CFG_FILE, "w", encoding="utf-8") as f:
                json.dump({"lang": lang}, f)
            i18n.set('locale', lang)
            break
else:
    ans = input()
    if ans.lower() == 'l':
        c = input(_('choose')).strip()
        lang = "en" if c == "1" else "ar"
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
        i18n.set('locale', lang)

try:
    from wand.image import Image as WandImage
except ImportError:
    if input(_('wand_ask')).strip().lower() == "y":
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Wand"])
        from wand.image import Image as WandImage
    else:
        sys.exit(_('wand_err'))

def make_zip(files: list[Path]) -> bytes:
    mem_zip = BytesIO()
    with ZipFile(mem_zip, "w", ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.name)
    mem_zip.seek(0)
    return mem_zip.read()

def fetch_image(url: str) -> bytes:
    try:
        import requests
    except ImportError:
        if input(_('req_ask')).strip().lower() == "y":
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            import requests
        else:
            sys.exit(_('req_err'))

    res = requests.get(url, stream=True)
    if res.status_code == 200:
        return res.content
    sys.exit(_('fail_dl', status=res.status_code))

def process_img(img, out_dir: Path):
    img.format = "png"
    img.resize(440, 440)
    img.save(filename=str(out_dir / "avatar.png"))
    img.compression = "dxt5"

    for s in IMG_SIZES:
        if img.width != s:
            img.resize(s, s)
        img.save(filename=str(out_dir / f"avatar{s}.dds"))

def build_avatar(target_in: str, target_out: Path):
    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        t_start = time.time()

        if target_in.startswith(("http://", "https://")):
            blob = fetch_image(target_in)
            with WandImage(blob=blob) as img:
                process_img(img, tmp_dir)
        else:
            with WandImage(filename=target_in) as img:
                process_img(img, tmp_dir)

        json_data = r"""{"avatarUrl":"http:\/\/static-resource.np.community.playstation.net\/avatar_xl\/WWS_E\/E0012_XL.png","firstName":"","lastName":"","pictureUrl":"https:\/\/image.api.np.km.playstation.net\/images\/?format=png&w=440&h=440&image=https%3A%2F%2Fkfscdn.api.np.km.playstation.net%2F00000000000008%2F000000000000003.png&sign=blablabla019501","trophySummary":"{\"level\":1,\"progress\":0,\"earnedTrophies\":{\"platinum\":0,\"gold\":0,\"silver\":0,\"bronze\":0}}","isOfficiallyVerified":"true"}"""
        (tmp_dir / "online.json").write_text(json_data, encoding="utf-8")
        shutil.copy(tmp_dir / "avatar.png", tmp_dir / "picture.png")
        
        for s in IMG_SIZES:
            shutil.copy(tmp_dir / f"avatar{s}.dds", tmp_dir / f"picture{s}.dds")

        final_bytes = make_zip(list(tmp_dir.iterdir()))

    target_out.write_bytes(final_bytes)
    t_end = time.time()

    print(_('success', input=target_in, output=target_out))
    print(_('timer', time=f"{t_end - t_start:.2f}"))

if __name__ == "__main__":
    args = sys.argv
    user_input = input(_('enter_p')).strip() if len(args) < 2 else args[1]

    if not user_input:
        sys.exit(_('no_in'))

    if len(args) != 3:
        if user_input.startswith(("http://", "https://")):
            safe_name = user_input.replace("://", "_").replace("/", "_")
            out_file = Path(safe_name).with_suffix(".xavatar")
        else:
            out_file = Path(user_input).with_suffix(".xavatar")
    else:
        out_file = Path(args[2])
        if out_file.suffix != ".xavatar":
            out_file = out_file.with_suffix(".xavatar")

    build_avatar(user_input, out_file)
