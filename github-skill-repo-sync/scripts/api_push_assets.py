# -*- coding: utf-8 -*-
"""GitHub Data API 增量推送（github.com 被墙、git push 超时时的兜底）。

经 api.github.com（实测常可达）完成 blob -> tree -> commit -> 更新 main。
**使用前改下面 4 个常量即可复用。**

实测：2026-09-25，github.com 直连 443 超时(21s)，api.github.com 直连 200/0.5s。
"""
import base64, json, os, subprocess, urllib.request

# ==== 按需修改 ====
REPO = "phxjchina/SkillRepository"                     # owner/repo
ROOT = r"C:/Users/Administrator/SkillRepository"       # 本地仓库工作副本根
NEW_DIRS = ["lab-os-agent", "wb-skill-load-verify", "wb-expert-package-build"]  # 本次新增/更新的目录
NEW_TOP = ["lab-os-architect.zip", "README.md"]        # 本次新增/更新的顶层文件
MSG = "feat(skills): 新增 ... \n\n(via GitHub Data API)"
# ==================


def collect():
    files = []
    for item in NEW_DIRS:
        base = os.path.join(ROOT, item)
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d != "__pycache__"]
            for fn in fns:
                if fn.endswith(".pyc"):
                    continue
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                files.append((rel, full))
    for f in NEW_TOP:
        files.append((f, os.path.join(ROOT, f)))
    return files


def token():
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("无 GCM token（检查 git config credential.helperselector.selected=manager）")


def api(method, path, tok, payload=None):
    url = "https://api.github.com%s" % path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "skill-sync")
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read().decode()
        return json.loads(body) if body.strip() else {}


def main():
    files = collect()
    print("待推送文件数:", len(files))
    tok = token()
    ref = api("GET", "/repos/%s/git/ref/heads/main" % REPO, tok)
    base_commit = ref["object"]["sha"]
    # 关键：取父提交的 tree 作为 base_tree，保证增量、不删既有文件
    base_tree_sha = api("GET", "/repos/%s/git/commits/%s" % (REPO, base_commit), tok)["tree"]["sha"]
    print("base commit:", base_commit, "| base tree:", base_tree_sha)

    entries = []
    for rel, full in files:
        with open(full, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        blob = api("POST", "/repos/%s/git/blobs" % REPO, tok,
                   {"content": b64, "encoding": "base64"})
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    print("blob 上传完成:", len(entries))

    tree = api("POST", "/repos/%s/git/trees" % REPO, tok,
               {"base_tree": base_tree_sha, "tree": entries})
    commit = api("POST", "/repos/%s/git/commits" % REPO, tok,
                 {"message": MSG, "tree": tree["sha"], "parents": [base_commit]})
    api("PATCH", "/repos/%s/git/refs/heads/main" % REPO, tok,
        {"sha": commit["sha"], "force": False})
    print("PUSHED:", commit["sha"])
    print("核实: curl -s -H \"Authorization: token <tok>\" "
          "https://api.github.com/repos/%s/contents/?ref=main" % REPO)


if __name__ == "__main__":
    main()
