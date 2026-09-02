#!/usr/bin/env python3
"""Парсер сообщества ВКонтакте через VK API.

Складывает всё сырьё в <out>/raw.json и человекочитаемый конспект в <out>/summary.md.
Фото из альбомов сообщества скачивает в <out>/photos/<альбом>/ (фото со стены — только ссылки).

Использование:
    python3 scripts/vk_group_scrape.py \
        --group artnik_krasnodar \
        --token "<сервисный или пользовательский токен>" \
        --out sites/artnic/vk

Раздел «Товары/Услуги» (market.*) недоступен с сервисным токеном — нужен
пользовательский токен незаблокированного аккаунта, передаётся через --market-token.
Если он не задан или не сработал, конспект помечает раздел как недоступный.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.vk.com/method/"
API_VERSION = "5.199"

try:  # на маке системный Python часто без корневых сертификатов
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl._create_unverified_context()

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text, fallback="album"):
    text = (text or "").strip().lower()
    out = []
    for ch in text:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    return slug or fallback


def ts(unix):
    if not unix:
        return ""
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d")


class VK:
    def __init__(self, token):
        self.token = token
        self.last = 0.0

    def call(self, method, **params):
        params.setdefault("v", API_VERSION)
        params["access_token"] = self.token
        url = API + method + "?" + urllib.parse.urlencode(params)
        for attempt in range(5):
            gap = 0.35 - (time.time() - self.last)
            if gap > 0:
                time.sleep(gap)
            self.last = time.time()
            try:
                with urllib.request.urlopen(url, timeout=40, context=SSL_CTX) as resp:
                    data = json.load(resp)
            except Exception as exc:  # сеть/таймаут — повтор
                time.sleep(1.5)
                if attempt == 4:
                    return {"_error": {"error_msg": f"network: {exc}", "method": method}}
                continue
            if "error" in data:
                err = data["error"]
                if err.get("error_code") == 6:  # too many requests
                    time.sleep(1.0)
                    continue
                return {"_error": err}
            return data["response"]
        return {"_error": {"error_msg": "retry limit", "method": method}}


def paginate(vk, method, count=100, cap=100000, **params):
    """Собирает все items через offset."""
    items = []
    offset = 0
    while offset < cap:
        resp = vk.call(method, count=count, offset=offset, **params)
        if "_error" in resp:
            if offset == 0:
                return {"_error": resp["_error"]}
            break
        batch = resp.get("items", [])
        items.extend(batch)
        total = resp.get("count", len(items))
        offset += count
        if offset >= total or not batch:
            break
    return {"count": len(items), "items": items}


def best_photo_url(photo):
    sizes = photo.get("sizes") or []
    if not sizes:
        return photo.get("photo_1280") or photo.get("photo_807") or ""
    order = {"w": 9, "z": 8, "y": 7, "x": 6, "r": 5, "q": 4, "p": 3, "o": 2, "m": 1, "s": 0}
    best = max(sizes, key=lambda s: (s.get("width", 0) * s.get("height", 0), order.get(s.get("type"), 0)))
    return best.get("url", "")


def download(url, path):
    if os.path.exists(path):
        return "exists"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as resp:
            body = resp.read()
        with open(path, "wb") as fh:
            fh.write(body)
        return "ok"
    except Exception as exc:
        return f"fail: {exc}"


def collect(vk, market_vk, group):
    data = {"fetched_at": datetime.now(timezone.utc).isoformat(), "group_ref": group}

    resolved = vk.call("utils.resolveScreenName", screen_name=group)
    if "_error" in resolved or not resolved:
        sys.exit(f"Не удалось разрешить {group}: {resolved}")
    gid = resolved["object_id"]
    owner_id = -gid
    data["group_id"] = gid
    data["owner_id"] = owner_id

    fields = ("description,contacts,site,activity,status,addresses,links,counters,"
              "members_count,main_section,age_limits,public_date_label,phone,wiki_page")
    info = vk.call("groups.getById", group_id=gid, fields=fields)
    data["group"] = info

    data["wall"] = paginate(vk, "wall.get", owner_id=owner_id, count=100, filter="owner")

    albums = vk.call("photos.getAlbums", owner_id=owner_id, need_system=1)
    data["photo_albums"] = albums
    data["photos"] = {}
    if "_error" not in albums:
        for alb in albums.get("items", []):
            aid = alb["id"]
            data["photos"][str(aid)] = paginate(
                vk, "photos.get", owner_id=owner_id, album_id=aid, count=1000, rev=0
            )

    topics = vk.call("board.getTopics", group_id=gid, count=100, extended=1, order=1)
    data["board_topics"] = topics
    data["board_comments"] = {}
    if "_error" not in topics:
        for t in topics.get("items", []):
            if t.get("comments", 0):
                data["board_comments"][str(t["id"])] = paginate(
                    vk, "board.getComments", group_id=gid, topic_id=t["id"],
                    count=100, extended=1, need_likes=0,
                )

    mvk = market_vk or vk
    data["market_albums"] = mvk.call("market.getAlbums", owner_id=owner_id, count=100)
    data["market"] = paginate(mvk, "market.get", owner_id=owner_id, count=200, extended=1)

    return data


def write_summary(data, out_dir, photo_index):
    g = (data.get("group", {}).get("groups") or [{}])[0]
    lines = []
    A = lines.append

    A(f"# ВКонтакте — {g.get('name', data['group_ref'])}")
    A("")
    A(f"Источник: https://vk.ru/{g.get('screen_name', data['group_ref'])}  ")
    A(f"Собрано: {data['fetched_at'][:10]}  ")
    A(f"Сырьё: `raw.json` (id сообщества {data['group_id']})")
    A("")

    A("## Клиника")
    A("")
    if g.get("site"):
        A(f"- Сайт: {g['site']}")
    for c in g.get("contacts", []):
        if c.get("phone"):
            A(f"- Телефон: {c['phone']}")
        if c.get("email"):
            A(f"- E-mail: {c['email']}")
    addr = g.get("addresses", {}).get("main_address") if isinstance(g.get("addresses"), dict) else None
    if addr:
        A(f"- Адрес: {addr.get('address', '')}, {addr.get('city', {}).get('title', '')}")
    A("")
    if g.get("description"):
        A("### Описание сообщества")
        A("")
        for para in g["description"].split("\n"):
            A(para)
        A("")

    A("## Товары / Услуги (VK Market)")
    A("")
    market = data.get("market", {})
    if "_error" in market:
        err = market["_error"]
        A(f"> Недоступно: `{err.get('error_msg')}` (код {err.get('error_code')}).")
        A("> Нужен пользовательский токен незаблокированного аккаунта (--market-token).")
    elif not market.get("items"):
        A("> Раздел пуст.")
    else:
        albums = data.get("market_albums", {})
        if isinstance(albums, dict) and albums.get("items"):
            A("Подборки: " + ", ".join(f"{a['title']} ({a.get('count', 0)})" for a in albums["items"]))
            A("")
        for it in market["items"]:
            price = (it.get("price") or {}).get("text", "")
            A(f"### {it.get('title', '—')} — {price}".rstrip(" —"))
            if it.get("category", {}).get("name"):
                A(f"*Категория: {it['category']['name']}*")
            A("")
            if it.get("description"):
                A(it["description"])
                A("")
    A("")

    A("## Обсуждения")
    A("")
    topics = data.get("board_topics", {})
    if "_error" in topics:
        A(f"> Недоступно: `{topics['_error'].get('error_msg')}`.")
    elif not topics.get("items"):
        A("> Обсуждений нет.")
    else:
        for t in topics["items"]:
            A(f"- **{t.get('title')}** ({t.get('comments', 0)} комм.) — topic_id {t['id']}")
    A("")

    A("## Фотоальбомы")
    A("")
    albums = data.get("photo_albums", {})
    if "_error" not in albums:
        for alb in albums.get("items", []):
            aid = str(alb["id"])
            photos = data.get("photos", {}).get(aid, {})
            A(f"### {alb.get('title', aid)} ({photos.get('count', 0)} фото)")
            if alb.get("description"):
                A(f"*{alb['description']}*")
            folder = photo_index.get(aid)
            if folder:
                A(f"Скачано в `photos/{folder}/`")
            A("")
            for ph in photos.get("items", []):
                cap = (ph.get("text") or "").replace("\n", " ").strip()
                A(f"- {best_photo_url(ph)}" + (f" — {cap}" if cap else ""))
            A("")

    A("## Стена — все посты")
    A("")
    A("*Фото со стены не скачиваются, только ссылки.*")
    A("")
    wall = data.get("wall", {})
    for post in wall.get("items", []):
        A(f"### {ts(post.get('date'))} · пост {post.get('id')}")
        text = post.get("text", "").strip()
        if text:
            A(text)
        photos = [best_photo_url(a["photo"]) for a in post.get("attachments", []) if a.get("type") == "photo"]
        if photos:
            A("")
            A("Фото: " + " | ".join(photos))
        links = [a["link"]["url"] for a in post.get("attachments", []) if a.get("type") == "link"]
        if links:
            A("Ссылки: " + " | ".join(links))
        A("")

    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def download_album_photos(data, out_dir):
    """Качает фото из альбомов сообщества. Возвращает {album_id: имя_папки}."""
    index = {}
    albums = data.get("photo_albums", {})
    if "_error" in albums:
        return index
    used = set()
    for alb in albums.get("items", []):
        aid = str(alb["id"])
        photos = data.get("photos", {}).get(aid, {}).get("items", [])
        if not photos:
            continue
        base = slugify(alb.get("title"), f"album-{aid}")
        name = base
        n = 2
        while name in used:
            name = f"{base}-{n}"
            n += 1
        used.add(name)
        index[aid] = name
        folder = os.path.join(out_dir, "photos", name)
        os.makedirs(folder, exist_ok=True)
        for i, ph in enumerate(photos, 1):
            url = best_photo_url(ph)
            if not url:
                continue
            ext = ".jpg"
            dest = os.path.join(folder, f"{i:02d}{ext}")
            status = download(url, dest)
            print(f"  photos/{name}/{i:02d}{ext}: {status}")
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", required=True, help="короткое имя или id сообщества")
    ap.add_argument("--token", default=os.environ.get("VK_TOKEN"), help="токен VK API (или $VK_TOKEN)")
    ap.add_argument("--market-token", default=os.environ.get("VK_MARKET_TOKEN"),
                    help="пользовательский токен для market.* (или $VK_MARKET_TOKEN)")
    ap.add_argument("--out", required=True, help="каталог для raw.json / summary.md / photos/")
    ap.add_argument("--no-photos", action="store_true", help="не скачивать фото из альбомов")
    args = ap.parse_args()

    if not args.token:
        sys.exit("Нужен --token или переменная окружения VK_TOKEN")

    os.makedirs(args.out, exist_ok=True)
    vk = VK(args.token)
    market_vk = VK(args.market_token) if args.market_token else None

    print("Собираю данные из VK API…")
    data = collect(vk, market_vk, args.group)

    with open(os.path.join(args.out, "raw.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"raw.json — {os.path.getsize(os.path.join(args.out, 'raw.json'))} байт")

    photo_index = {}
    if not args.no_photos:
        print("Качаю фото из альбомов…")
        photo_index = download_album_photos(data, args.out)

    write_summary(data, args.out, photo_index)
    print(f"summary.md готов: {os.path.join(args.out, 'summary.md')}")


if __name__ == "__main__":
    main()
