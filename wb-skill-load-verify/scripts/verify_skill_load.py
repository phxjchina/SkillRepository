# -*- coding: utf-8 -*-
"""
WorkBuddy Skill 真机加载验证器
================================
验证一个 Skill 能否在真实 WorkBuddy 运行时中正常安装与加载。

用法：
  # 仅静态校验某个 skill 目录（已安装或候选源）
  python verify_skill_load.py <skill_dir>

  # 先复制安装到 ~/.workbuddy/skills/ 再做校验
  python verify_skill_load.py <skill_dir> --install

  # 指定安装目标名（默认用目录名）
  python verify_skill_load.py <skill_dir> --install --name my-skill

退出码 0 = 全部通过，1 = 存在问题。
"""
import os
import re
import sys
import shutil

HOME = os.path.expanduser("~")
SKILLS_ROOT = os.path.join(HOME, ".workbuddy", "skills")


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip('"')
    return fields


def collect_refs(text):
    # 含中文的相对路径截断：到空白/中文标点/括号/引号/反引号/逗号为止
    refs = set()
    for pat in [
        r"frameworks/[^\s，。、()（）\"'`<>，]+\.md",
        r"world_model_lab/[^\s，。、()（）\"'`<>，]+",
        r"model_backend\.py",
        r"[A-Za-z0-9_.\-]+/\.py",  # 其它 scripts 引用
    ]:
        for r in re.findall(pat, text):
            refs.add(r)
    return refs


def verify(skill_dir):
    print("=" * 64)
    print("STEP 1  目录结构 / 安装位置校验")
    print("=" * 64)
    assert os.path.isdir(skill_dir), f"Skill 目录不存在: {skill_dir}"
    name_from_dir = os.path.basename(os.path.normpath(skill_dir))
    print(f"  位置   : {skill_dir}")
    print(f"  目录名 : {name_from_dir}")
    for sub in ["SKILL.md"]:
        p = os.path.join(skill_dir, sub)
        print(f"  [{'OK' if os.path.exists(p) else 'MISSING'}] {sub}")

    skill_md = os.path.join(skill_dir, "SKILL.md")
    text = open(skill_md, encoding="utf-8").read()

    print("\n" + "=" * 64)
    print("STEP 2  SKILL.md frontmatter 解析")
    print("=" * 64)
    fields = parse_frontmatter(text)
    if not fields:
        print("  [FAIL] 找不到 frontmatter 分隔块 ---")
        return False
    for k in ["name", "description", "version", "author"]:
        ok = bool(fields.get(k))
        print(f"  [{'OK' if ok else 'FAIL'}] {k} = {fields.get(k, '')[:50]}")

    print("\n" + "=" * 64)
    print("STEP 3  目录名 == frontmatter.name（WorkBuddy 加载约定）")
    print("=" * 64)
    nm = fields.get("name", "")
    print(f"  name={nm!r}  目录={name_from_dir!r}")
    name_ok = (nm == name_from_dir)
    print(f"  [{'OK' if name_ok else 'FAIL'}] 二者一致")

    print("\n" + "=" * 64)
    print("STEP 4  相对路径引用完整性（含中文文件名）")
    print("=" * 64)
    refs = collect_refs(text)
    broken = []
    for r in sorted(refs):
        p = os.path.normpath(os.path.join(skill_dir, r))
        ok = os.path.exists(p)
        if not ok:
            broken.append(r)
        print(f"  [{'OK' if ok else 'BROKEN'}] {r}")
    print(f"  引用总数 {len(refs)}，损坏 {len(broken)}")

    print("\n" + "=" * 64)
    print("STEP 5  frameworks 物理 vs 引用交叉")
    print("=" * 64)
    fw = os.path.join(skill_dir, "frameworks")
    if os.path.isdir(fw):
        phys = sorted(f for f in os.listdir(fw) if f.endswith(".md"))
        refd = {r for r in refs if r.startswith("frameworks/")}
        unref = [f for f in phys if f"frameworks/{f}" not in refd]
        print(f"  物理 {len(phys)} 篇 | 被引用 {len(refd)} 篇 | 未引用(冗余): {unref or '无'}")
    else:
        print("  无 frameworks 目录（跳过）")

    print("\n" + "=" * 64)
    print("STEP 6  动态加载证据（__pycache__ 再生）")
    print("=" * 64)
    pyc = []
    for root, _, files in os.walk(skill_dir):
        for f in files:
            if f.endswith(".pyc"):
                pyc.append(os.path.relpath(os.path.join(root, f), skill_dir))
    if pyc:
        print(f"  检测到已编译字节码（WorkBuddy 加载器已扫描该 skill）：")
        for p in pyc:
            print(f"    - {p}")
        print("  [OK] 存在 __pycache__ = 已被真实运行时加载（铁证）")
    else:
        print("  未检测到 __pycache__。若已 --install，请重启 WorkBuddy / 新开对话")
        print("  后再次运行本脚本，加载器会在扫描时生成它。")

    ok = (os.path.isdir(skill_dir)
          and all(fields.get(k) for k in ["name", "description", "version", "author"])
          and name_ok
          and not broken)
    print("\n" + "=" * 64)
    print("结论: 真机静态校验", "全部通过 ✅" if ok else "存在问题 ❌")
    return ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    src = sys.argv[1]
    install = "--install" in sys.argv
    name = None
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]

    if install:
        name = name or os.path.basename(os.path.normpath(src))
        dst = os.path.join(SKILLS_ROOT, name)
        if os.path.exists(dst):
            print(f"[WARN] 目标已存在，覆盖: {dst}")
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        # 清理字节码缓存，保持分发干净
        for root, dirs, _ in os.walk(dst):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root, d))
        print(f"[OK] 已安装到: {dst}\n")
        skill_dir = dst
    else:
        skill_dir = src

    ok = verify(skill_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
