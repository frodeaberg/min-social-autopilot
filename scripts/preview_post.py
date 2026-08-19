#!/usr/bin/env python3
"""One-off: create an UNPUBLISHED (admin-only draft) Facebook post from a
queue/stories post.json, without touching the queue or committing anything.

Used to preview a post in Meta Business Suite before the real publish run.

Required env vars:
    META_TOKEN, FB_PAGE_ID, PREVIEW_DIR (e.g. "queue/001-iso9001-kvalitet")
    GITHUB_REPOSITORY, GITHUB_SHA   (set automatically by Actions)
"""
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
GRAPH = "https://graph.facebook.com/v21.0"


def api(path: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=data)
    try:
        body = urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Graph API error on /{path}: {e.read().decode()[:800]}")
    return json.loads(body)


def main():
    post_dir = ROOT / os.environ["PREVIEW_DIR"]
    post = json.loads((post_dir / "post.json").read_text())
    caption = post["caption"].strip()
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]

    def raw_url(rel):
        return f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(rel)}"

    media_rels = post["images"]
    for rel in media_rels:
        if not (ROOT / rel).exists():
            sys.exit(f"Missing media file: {rel}")
    media_urls = [raw_url(rel) for rel in media_rels]

    token = os.environ["META_TOKEN"]
    page_id = os.environ["FB_PAGE_ID"]

    media = []
    for url in media_urls:
        photo = api(
            f"{page_id}/photos",
            {"url": url, "published": "false", "access_token": token},
        )["id"]
        media.append(photo)

    params = {"message": caption, "published": "false", "access_token": token}
    for i, photo_id in enumerate(media):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": photo_id})
    result = api(f"{page_id}/feed", params)
    post_id = result["id"]
    print(f"PREVIEW_POST_ID={post_id}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## Preview post created (unpublished draft)\n\n")
            f.write(f"- Post ID: `{post_id}`\n")
            f.write(f"- Source: `{os.environ['PREVIEW_DIR']}`\n")
            f.write("- Find it in Meta Business Suite -> Content -> Drafts, on the ProAdvice Page.\n")
            f.write("- Nothing was moved out of queue/ and no commit was made.\n")


if __name__ == "__main__":
    main()
