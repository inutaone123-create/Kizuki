"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

"""Qiita記事投稿スクリプト.

使い方:
    python scripts/publish_qiita.py docs/qiita_draft_08_report_edit.md

フロントマターの `published: true` にすると公開、`false` で下書き保存。
記事URLが見つかった場合（コメント行 `<!-- 公開URL: ... -->`）は更新、なければ新規作成。
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error

def load_token() -> str:
    """QIITA_TOKEN を .env または環境変数から取得する."""
    token = os.environ.get("QIITA_TOKEN")
    if not token:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("QIITA_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break
    if not token:
        print("❌ QIITA_TOKEN が見つかりません。.env ファイルに設定してください。")
        sys.exit(1)
    return token


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML フロントマターを解析して (meta, body) を返す."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end + 4:].strip()

    meta = {}
    for line in yaml_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # インラインリスト
                items = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
                meta[key.strip()] = items
            elif val in ("true", "True"):
                meta[key.strip()] = True
            elif val in ("false", "False"):
                meta[key.strip()] = False
            else:
                meta[key.strip()] = val.strip("\"'")
        elif line.strip().startswith("- "):
            # リスト項目（直前のキーに追加）
            last_key = list(meta.keys())[-1] if meta else None
            if last_key and not isinstance(meta[last_key], list):
                meta[last_key] = []
            if last_key:
                meta[last_key].append(line.strip()[2:].strip().strip("\"'"))
    return meta, body


def extract_article_id(text: str) -> str | None:
    """先頭の `<!-- 公開URL: https://qiita.com/... -->` コメント行から記事IDを抽出する."""
    # 先頭数行のみ検索（本文中のリンクと誤認しないよう限定）
    first_lines = text.split("\n")[:3]
    for line in first_lines:
        m = re.search(r"<!--\s*公開URL:\s*https://qiita\.com/[^/]+/items/([a-f0-9]+)", line)
        if m:
            return m.group(1)
    return None


def build_tags(tags: list[str]) -> list[dict]:
    """Qiita API 用のタグ形式に変換する."""
    return [{"name": t, "versions": []} for t in tags]


def qiita_request(method: str, path: str, token: str, data: dict | None = None) -> dict:
    """Qiita API にリクエストを送る."""
    url = f"https://qiita.com/api/v2{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"❌ API エラー {e.code}: {msg}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/publish_qiita.py <ドラフトファイルパス>")
        sys.exit(1)

    draft_path = sys.argv[1]
    if not os.path.exists(draft_path):
        print(f"❌ ファイルが見つかりません: {draft_path}")
        sys.exit(1)

    token = load_token()
    text = open(draft_path, encoding="utf-8").read()
    article_id = extract_article_id(text)

    # コメント行を除いてフロントマター解析
    body_text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL).strip()
    meta, content = parse_frontmatter(body_text)

    title = meta.get("title", "無題")
    tags = build_tags(meta.get("tags", ["Python"]))
    published = meta.get("published", False)

    payload = {
        "title": title,
        "body": content,
        "tags": tags,
        "private": not published,
        "tweet": False,
    }

    if article_id:
        print(f"🔄 記事を更新中... (ID: {article_id})")
        result = qiita_request("PATCH", f"/items/{article_id}", token, payload)
        print(f"✅ 更新完了: {result['url']}")
    else:
        print("🆕 新規記事を作成中...")
        result = qiita_request("POST", "/items", token, payload)
        url = result["url"]
        print(f"✅ 作成完了: {url}")
        print()
        print(f"📝 ドラフトファイルの先頭に以下を追加してください：")
        print(f"<!-- 公開URL: {url} -->")


if __name__ == "__main__":
    main()
