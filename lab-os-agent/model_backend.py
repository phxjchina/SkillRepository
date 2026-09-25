"""
实验室 OS Agent —— 可插拔模型后端（通用版）
=========================================
本地 Ollama + Bonsai-27B（隐私/离线/免费基底）与云端大模型 API 一键切换。
所有厂商均兼容 OpenAI 协议，仅需改一个环境变量即可切换，业务代码零改动。

【快速上手 · 首次体验推荐云端 API】
本 Skill 默认后端为 local（本地 Ollama + Bonsai-27B，隐私不出本机）。
若您尚未部署本地模型，推荐先用云端 API 快速体验：
    export LAB_MODEL_BACKEND="deepseek"   # 国内直连、性价比高
    export DEEPSEEK_API_KEY="sk-xxx"      # 到 deepseek.com 免费申请
    python model_backend.py               # 自检
本地模型仍是隐私基底：学生情绪/档案等敏感链路请始终走 local。

依赖:
    pip install openai

配置（环境变量）:
    LAB_MODEL_BACKEND : local(默认) | deepseek | qwen | zhipu
    DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / ZHIPU_API_KEY : 对应厂商 Key

在 Agent 代码中:
    from model_backend import get_client
    client, model = get_client()
    resp = client.chat.completions.create(model=model, messages=[...])
"""

import os

# ── 后端注册表 ─────────────────────────────────────────────
# local   : 本地 Ollama + Bonsai-27B，离线免费，隐私不出本机（默认基底）
# deepseek: 深度求索，国内直连无需代理，性价比首选（首次体验推荐）
# qwen    : 阿里通义千问，长上下文（qwen-long 1M）适合多专家编排
# zhipu   : 智谱 GLM，轻量 Flash 版便宜，适合分类/摘要
BACKENDS = {
    "local": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",                 # Ollama 不校验 key
        "model": "bonsai-27b-q1_0",
        "note": "本地基底：隐私/离线/免费，适合学生敏感数据（默认）",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "note": "云端：国内直连，~2/8 元每百万 token，首次体验首选",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "model": "qwen-plus",               # 长上下文可换 qwen-long / qwen-max
        "note": "云端：阿里通义，长上下文适合多专家编排",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "api_key_env": "ZHIPU_API_KEY",
        "model": "glm-4-flash",             # 便宜轻量；要更强换 glm-4-plus
        "note": "云端：智谱 GLM，Flash 版便宜，适合脱敏分类/摘要",
    },
}

ACTIVE = os.environ.get("LAB_MODEL_BACKEND", "local").strip().lower()


def get_client():
    """返回 (OpenAI client, model_name)。切换后端只改环境变量 LAB_MODEL_BACKEND。"""
    from openai import OpenAI  # 延迟导入：未安装 openai 时也不阻断 Skill 加载
    if ACTIVE not in BACKENDS:
        raise ValueError(
            f"未知后端 '{ACTIVE}'，可选：{', '.join(BACKENDS)}"
        )
    cfg = BACKENDS[ACTIVE]
    api_key = cfg.get("api_key") or os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        raise RuntimeError(
            f"后端 '{ACTIVE}' 需要环境变量 {cfg['api_key_env']}，请先 export。"
            f"（首次体验建议：export LAB_MODEL_BACKEND=deepseek 并配置 DEEPSEEK_API_KEY）"
        )
    client = OpenAI(base_url=cfg["base_url"], api_key=api_key)
    return client, cfg["model"]


def current_backend():
    """当前后端信息，便于日志/审计。"""
    cfg = BACKENDS.get(ACTIVE, {})
    masked = "本地无 key" if "api_key" in cfg else f"env:{cfg.get('api_key_env')}"
    return {"name": ACTIVE, "model": cfg.get("model"), "auth": masked, "note": cfg.get("note")}


if __name__ == "__main__":
    info = current_backend()
    print(f"当前模型后端: {info['name']}")
    print(f"  模型       : {info['model']}")
    print(f"  鉴权       : {info['auth']}")
    print(f"  说明       : {info['note']}")
    if ACTIVE == "local":
        print("  💡 首次体验若无本地 Ollama，可改用云端：")
        print("     export LAB_MODEL_BACKEND=deepseek && export DEEPSEEK_API_KEY=sk-xxx")
    try:
        client, model = get_client()
        print(f"  ✅ 客户端构建成功，可调用 chat.completions.create(model='{model}')")
    except Exception as e:
        print(f"  ⚠️  客户端构建失败：{e}")
