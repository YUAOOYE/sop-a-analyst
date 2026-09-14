import os
import re
import time
import streamlit as st

# ==================== 1. 依赖库导入与安全保护 ====================
HAS_OPENAI = False
HAS_GEMINI = False
HAS_DDGS = False

try:
  from openai import OpenAI

  HAS_OPENAI = True
except ImportError:
  pass

try:
  from google import genai
  from google.genai import types

  HAS_GEMINI = True
except ImportError:
  pass

try:
  from duckduckgo_search import DDGS

  HAS_DDGS = True
except ImportError:
  pass

# ==================== 2. 全局页面配置 ====================
st.set_page_config(
    page_title="宁波威霖 · 北美暖通出风口(RGD)产品市场详细认知与对标系统",
    page_icon="🏭",
    layout="wide",
)

# 纯粹的产品与市场物理认知专属 System Prompt（剔除痛点分析，只做客观事实与技术认知）
SOP_A_SYSTEM_INSTRUCTION = """
You are a Senior US HVAC RGD (Registers, Grilles, Diffusers) Market Research Director & Chief Industrial Engineer at Ningbo Runner Industrial Corporation (宁波威霖住宅设施有限公司).
Your mission is to establish deep, objective, engineering-grade physical and market reality understanding of HVAC terminal products in North America.

Strict Operational Boundaries:
- DO NOT perform new product redesign, speculative invention, or customer negative review / pain point / RMA complaint analysis (the user already has a separate product R&D SOP).
- Focus strictly on:
  1. Detailed Physical Realities: Duct opening dimensions vs. actual drop-in box negative tolerances (-1/8" to -3/16") vs. visible faceplate overall size.
  2. Industrial Manufacturing: Die-casting (A380), sheet stamping (SPCC), aluminum extrusion (6063-T5), mold tooling cycles, dual electro+powder coating, and ASTM B117 salt spray specs.
  3. North American Standards: IBC concentrated floor load test (>=300 lbs), ADA heel-proof (<9.5mm / 0.375" gap), Free Area % / CFM airflow resistance curves.
  4. Commercial Logistics & Trade: HS Code classification (7616.99 / 7326.90 / 3926.90 / 7419.80), Section 301 tariffs, supply origins (Ningbo HQ vs. Runner Thailand), packaging engineering (Pro Bulk vs. Retail Shrink-wrap), and 40HQ container CBM load calculation.
  5. Technical RFQ Communication: Standard professional English vocabulary and technical parameter matrix for interacting with North American buyers.

Confidence Tagging:
Every factual claim must carry one tag:
【FACT】 / 【HIGH CONFIDENCE】 / 【INFERENCE】 / 【INDUSTRY STANDARD】 / 【UNVERIFIED】 / 【UNKNOWN】
Missing data tags: 【未找到】 / 【无法验证】 / 【行业推断】
"""

# 包含 3.8 / 3.7 / 3.6 等官方最新模型库
PROVIDER_CONFIG = {
    "Google Gemini": {
        "models": [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.1-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ],
        "default_url": "",
        "key_hint": "从 Google AI Studio 获取官方 API Key",
    },
    "WorkBuddy (聚合平台)": {
        "models": [
            "claude-3-7-sonnet",
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "claude-3-5-sonnet",
            "gpt-4o",
            "o3-mini",
            "deepseek-r1",
            "deepseek-v3",
        ],
        "default_url": "https://api.workbuddy.cn/v1",
        "key_hint": "WorkBuddy 聚合平台 API 密钥",
    },
    "OpenAI": {
        "models": [
            "gpt-4o",
            "o3",
            "o3-mini",
            "o1",
            "gpt-4.5-preview",
            "gpt-4o-mini",
        ],
        "default_url": "https://api.openai.com/v1",
        "key_hint": "OpenAI 官方或中转 API Key",
    },
    "DeepSeek (深度求索)": {
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_url": "https://api.deepseek.com/v1",
        "key_hint": "DeepSeek 开放平台 API Key",
    },
    "自定义 OpenAI 兼容接口": {
        "models": [
            "gemini-3.8-flash",
            "claude-3-7-sonnet",
            "gpt-4o",
            "deepseek-r1",
            "自定义输入",
        ],
        "default_url": "https://api.example.com/v1",
        "key_hint": "中转服务商提供的 API 密钥",
    },
}

# 北美暖通市场全品类与工业参数选项库
MARKET_SPECS = {
    "categories": [
        "地板出风口 (Floor Register / Floor Diffuser)",
        "侧墙/天花出风口 (Sidewall & Ceiling Register)",
        "回风过滤面罩 (Filter Return Air Grille)",
        "标准回风格栅 (Return Air Grille - 无滤网款)",
        "踢脚线风口 (Baseboard Register / Diffuser)",
        "商业线性条缝散流器 (Linear Slot Diffuser)",
        "T-Bar 吊顶跌落式散流器 (2x2 T-Bar Ceiling Diffuser)",
        "✍️ 自定义手动填写品类",
        "❓ 【我不知道/请AI根据市场推断】",
    ],
    "sizes": [
        "4x10 inches (北美最畅销标准地面开孔)",
        "4x12 inches",
        "2x10 inches",
        "2x12 inches",
        "2x14 inches",
        "6x10 inches",
        "6x12 inches",
        "6x6 inches (侧墙天花常用)",
        "8x8 inches",
        "10x6 inches",
        "12x6 inches",
        "14x20 inches (回风过滤常用)",
        "14x25 inches",
        "20x20 inches",
        "20x25 inches",
        "20x30 inches",
        "15 inches (踢脚线风口)",
        "18 inches",
        "24 inches",
        "48 inches (商业线性散流器)",
        "✍️ 自定义手动填写尺寸",
        "❓ 【我不知道/请AI根据市场推断】",
    ],
    "materials": [
        "A380 汽车级重型高压压铸铝 (Cast Aluminum)",
        "SPCC 冷轧钢板连续模冲压 (Stamped Cold-Rolled Steel)",
        "6063-T5 阳极氧化优质铝挤型材 (Extruded Aluminum)",
        "工程 ABS/PC 阻燃防结露注塑塑料 (Injection Molded ABS)",
        "实木材质 (Solid Red Oak / White Oak / Maple)",
        "纯黄铜/青铜重型铸造 (Solid Cast Brass / Bronze)",
        "钢木复合结构 (Steel Frame + Hardwood Insert)",
        "✍️ 自定义手动填写材质",
        "❓ 【我不知道/请AI根据市场推断】",
    ],
    "dampers": [
        "ABS 工程塑料耐磨滑块百叶阀 (Sliding Louver Damper - 耐高温无锈蚀)",
        "全钢连动多叶对开风门 (Opposed Blade Damper, OBD - 高风阻调节)",
        "全钢连动单向百叶阀 (Multi-Shutter Damper)",
        "重力平衡自垂翻板 (Gravity Flap Damper)",
        "内置可调气流导向柱 (Pattern Controllers - 线性散流器专配)",
        "纯面罩无风阀 (Grille Only - No Damper)",
        "✍️ 自定义手动填写调节阀",
        "❓ 【我不知道/请AI根据市场推断】",
    ],
    "finishes": [
        "威霖环保双涂层：电泳底漆 + 哑光黑静电粉末喷涂 (Powder Coated Matte Black)",
        "商超标准哑光白粉末喷涂 (Powder Coated White / Off-White)",
        "金属拉丝表面处理 (Brushed Nickel Finish)",
        "仿古油擦青铜色 (Oil Rubbed Bronze, ORB)",
        "清漆阳极氧化磨砂 (Clear Satin Anodized)",
        "电镀铬色 (Polished Chrome)",
        "未上漆实木原色 (Unfinished Raw Wood - 供现场刷漆)",
        "✍️ 自定义手动填写表面处理",
        "❓ 【我不知道/请AI根据市场推断】",
    ],
}


# ==================== 3. 稳健网络实时检索 ====================
def search_live_web(query, max_results=3):
  if not HAS_DDGS:
    return "（系统未安装 duckduckgo_search 模块，采用内置暖通知识库）"
  try:
    time.sleep(0.6)  # 避免高频请求 429
    ddgs = DDGS()
    results = []
    for r in ddgs.text(query, max_results=max_results):
      title = re.sub(r"[\r\n]+", " ", r.get("title", ""))
      body = re.sub(r"[\r\n]+", " ", r.get("body", ""))
      results.append(
          f"- 来源: {title}\n  链接: {r.get('href')}\n  市场摘要: {body}"
      )
    return "\n".join(results) if results else "（未检索到特定实时信息）"
  except Exception as e:
    return f"（网络检索临时受限: {e}，调用威霖工厂工程标准库）"


# ==================== 4. 统一流式调用引擎 ====================
def stream_llm_response(
    provider,
    model,
    key,
    url,
    system_instruction,
    prompt,
    render_targets,
    temperature=0.2,
):
  full_text = ""
  targets = (
      render_targets
      if isinstance(render_targets, (list, tuple))
      else [render_targets]
  )

  if provider == "Google Gemini":
    if not HAS_GEMINI:
      raise ImportError(
          "当前环境未安装 google-genai 库，请执行: pip install google-genai"
      )
    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction, temperature=temperature
    )
    response_stream = client.models.generate_content_stream(
        model=model, contents=prompt, config=config
    )
    for chunk in response_stream:
      if chunk.text:
        full_text += chunk.text
        for t in targets:
          if t:
            t.markdown(full_text + " ▌")
  else:
    if not HAS_OPENAI:
      raise ImportError(
          "当前环境未安装 openai 库，请执行: pip install openai"
      )
    client = OpenAI(api_key=key, base_url=url if url else None)
    is_reasoning = any(
        x in model.lower() for x in ["o1", "o3", "reasoner", "r1", "thinking"]
    )
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt},
    ]
    kwargs = {"model": model, "messages": messages, "stream": True}
    if not is_reasoning:
      kwargs["temperature"] = temperature
    response_stream = client.chat.completions.create(**kwargs)
    for chunk in response_stream:
      if (
          chunk.choices
          and chunk.choices[0].delta
          and chunk.choices[0].delta.content
      ):
        full_text += chunk.choices[0].delta.content
        for t in targets:
          if t:
            t.markdown(full_text + " ▌")

  for t in targets:
    if t:
      t.markdown(full_text)
  return full_text


# ==================== 5. 侧边栏配置 ====================
with st.sidebar:
  st.markdown("### 🏢 宁波威霖住宅设施有限公司")
  st.caption("Ningbo Runner · 北美暖通出风口外贸产品认知工作台")
  st.markdown("---")

  app_mode = st.radio(
      "🎯 选择业务模式",
      options=[
          "🔍 单品 4 阶段深度认知 SOP A",
          "⚖️ 多款竞品横向技术对标 (Benchmark)",
      ],
      index=0,
  )

  st.markdown("---")
  st.subheader("⚙️ 官方最新大模型服务")
  selected_provider = st.selectbox(
      "选择 AI 服务商", options=list(PROVIDER_CONFIG.keys()), index=0
  )
  cfg = PROVIDER_CONFIG[selected_provider]

  selected_model = st.selectbox(
      f"选择 {selected_provider} 最新模型", options=cfg["models"], index=0
  )
  actual_model = (
      st.text_input(
          "手动输入模型名称", placeholder="例如: gemini-3.8-flash / gpt-4o"
      )
      if selected_model == "自定义输入"
      else selected_model
  )

  api_key = st.text_input(
      f"{selected_provider} API Key*",
      type="password",
      placeholder="粘贴官方 API Key",
      help=cfg["key_hint"],
  ).strip()

  base_url = ""
  if selected_provider in [
      "OpenAI",
      "WorkBuddy (聚合平台)",
      "自定义 OpenAI 兼容接口",
      "DeepSeek (深度求索)",
  ]:
    base_url = st.text_input(
        "API Base URL (基地址)",
        value="" if selected_provider == "OpenAI" else cfg["default_url"],
        placeholder="官方接口留空；中转请填如 https://api.xxx.com/v1",
    ).strip()

  st.markdown("---")
  st.subheader("🚢 威霖外贸供应链与贸易参数")
  supply_origin = st.selectbox(
      "制造出货基地 (规避关税核心)",
      [
          "中国宁波象山总部工厂 (Ningbo Port - 承担美国301关税)",
          "建霖泰国海外制造基地 (Runner Thailand - 零301关税/原产地合规)",
      ],
      index=0,
  )
  trade_terms = st.selectbox(
      "贸易交货条款 (Incoterms)",
      [
          "FOB Ningbo / FOB Laem Chabang",
          "CIF US West Coast (长滩/洛杉矶)",
          "DDP 完税后交货到客户指定海外仓",
      ],
      index=0,
  )
  target_channel = st.selectbox(
      "目标采购买手渠道",
      [
          "北美建材商超 (Home Depot / Lowe's / Menards) - 零售挂卡彩盒",
          "暖通工程批发商 (Ferguson / Johnstone Supply) - 工业散装 (Bulk)",
          "跨境电商/D2C (Amazon FBA / Wayfair) - 零塑耐跌落独立盒",
      ],
      index=0,
  )

# ==================== 顶部标题与按需演示 Demo ====================
st.markdown(
    "## 🏭 宁波威霖北美暖通出风口（RGD）产品市场认知与对标系统"
)
st.caption(
    f"出货基地: **{supply_origin.split(' ')[0]}** | 贸易方式:"
    f" **{trade_terms.split(' ')[0]}** | 渠道: **{target_channel.split(' ')[0]}**"
)

if "demo_mode" not in st.session_state:
  st.session_state.demo_mode = False

col_top1, col_top2 = st.columns([3, 1])
with col_top2:
  if st.button("📥 一键填入威霖畅销款演示数据", use_container_width=True):
    st.session_state.demo_mode = True
    st.rerun()

# ==================== 辅助选项解析器 ====================
def parse_selection(choice, custom_val, field_name):
  if choice == "✍️ 自定义手动填写品类" or "自定义手动填写" in choice:
    return custom_val.strip() if custom_val.strip() else f"自定义{field_name}"
  elif "我不知道" in choice:
    return "【我不知道/待调研 - 请AI根据北美市场主流标配智能推断并给出推荐】"
  return choice


# ==================== 模式 A: 单品 4 阶段深度认知 SOP A ====================
if app_mode == "🔍 单品 4 阶段深度认知 SOP A":
  for k in ["s1", "s2", "s3", "s4", "live_data"]:
    if k not in st.session_state:
      st.session_state[k] = ""

  st.markdown("### 📋 单品详细物理与外贸工程输入单")

  c1, c2 = st.columns(2)
  with c1:
    sel_cat = st.selectbox("1. 产品标准品类*", MARKET_SPECS["categories"], index=0)
    custom_cat = ""
    if "自定义" in sel_cat:
      custom_cat = st.text_input(
          "填写自定义品类",
          placeholder="例如: 现代极简隐形出风口 (Frameless Register)",
      )
    final_cat = parse_selection(sel_cat, custom_cat, "品类")

  with c2:
    sel_size = st.selectbox(
        "2. 标称开孔尺寸 (Duct Opening)*", MARKET_SPECS["sizes"], index=0
    )
    custom_size = ""
    if "自定义" in sel_size:
      custom_size = st.text_input(
          "填写自定义开孔尺寸", placeholder="例如: 4x10 inches"
      )
    final_size = parse_selection(sel_size, custom_size, "尺寸")

  c3, c4 = st.columns(2)
  with c3:
    sel_mat = st.selectbox(
        "3. 面板材质与成型工艺*", MARKET_SPECS["materials"], index=0
    )
    custom_mat = ""
    if "自定义" in sel_mat:
      custom_mat = st.text_input(
          "填写自定义材质工艺", placeholder="例如: A380高压压铸铝合金"
      )
    final_mat = parse_selection(sel_mat, custom_mat, "材质")

  with c4:
    sel_damper = st.selectbox(
        "4. 风量调节机构/风门类型*", MARKET_SPECS["dampers"], index=0
    )
    custom_damper = ""
    if "自定义" in sel_damper:
      custom_damper = st.text_input(
          "填写自定义风门", placeholder="例如: ABS滑块式阻尼百叶阀"
      )
    final_damper = parse_selection(sel_damper, custom_damper, "风门")

  c5, c6 = st.columns(2)
  with c5:
    sel_finish = st.selectbox(
        "5. 表面处理与涂装工艺*", MARKET_SPECS["finishes"], index=0
    )
    custom_finish = ""
    if "自定义" in sel_finish:
      custom_finish = st.text_input(
          "填写自定义涂层", placeholder="例如: 哑光黑静电粉末喷涂"
      )
    final_finish = parse_selection(sel_finish, custom_finish, "涂层")

  with c6:
    ref_link = st.text_input(
        "6. 参考链接/竞品型号 (选填)",
        value=(
            "https://www.homedepot.com/p/Decor-Grates-4-in-x-10-in-Cast-Aluminum-Floor-Register-AJH410-ALU/202525184"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: Home Depot / Lowe's 在售对应链接 (可选)",
    )

  def ensure_single_live_data():
    if not st.session_state.live_data:
      with st.spinner("🌐 正在抓取北美暖通行业在售同类产品规格、海关关税与测试标准..."):
        q1 = f"{final_cat} {final_size} technical specifications Home Depot lowes"
        q2 = (
            f"{final_cat} ASTM B117 IBC 300 lbs load capacity airflow CFM"
            " standard"
        )
        st.session_state.live_data = (
            f"### 北美商超工程参数调研:\n{search_live_web(q1, 2)}\n\n###"
            f" 行业检测规范 (IBC/ASTM):\n{search_live_web(q2, 2)}"
        )

  def get_single_ctx():
    ensure_single_live_data()
    return f"""
【威霖外贸单品输入条件】
- 产品品类: {final_cat}
- 标称开孔尺寸: {final_size}
- 面板材质与工艺: {final_mat}
- 风量调节机构: {final_damper}
- 表面处理工艺: {final_finish}
- 供应链背景: 生产出运基地【{supply_origin}】 | 贸易条款【{trade_terms}】 | 渠道包装【{target_channel}】
- 竞品参考: {ref_link if ref_link else '无特定链接，基于北美全行业基准'}

<external_market_evidence>
{st.session_state.live_data}
</external_market_evidence>
"""

  st.markdown("---")
  st.markdown("#### 🎯 选择本次需要输出的阶段 (可自由勾选)")
  col_s1, col_s2, col_s3, col_s4 = st.columns(4)
  with col_s1:
    exec_s1 = st.checkbox(
        "Stage 1: 工艺规格与海关关税",
        value=True,
        help="涵盖尺寸解耦、压铸/冲压工艺、IBC承重标准、HS Code与关税",
    )
  with col_s2:
    exec_s2 = st.checkbox(
        "Stage 2: 地材环境与场景应用",
        value=True,
        help="涵盖实木/LVP/地毯适配、扫地机越障坡度、冷暖风温差工况",
    )
  with col_s3:
    exec_s3 = st.checkbox(
        "Stage 3: 市场在售形态与渠道包装",
        value=True,
        help="涵盖商超挂卡/双泡壳 vs 批发工模大箱包装、40HQ 装箱 CBM 核算",
    )
  with col_s4:
    exec_s4 = st.checkbox(
        "Stage 4: 行业技术语言与询盘参数库",
        value=True,
        help="涵盖买手技术沟通专业术语、技术指标解答库、样品签样标准",
    )

  col_btn1, col_btn2 = st.columns(2)
  with col_btn1:
    run_single = st.button(
        "🚀 运行选中的阶段 (流式输出)",
        type="primary",
        use_container_width=True,
    )
  with col_btn2:
    if st.button("🔄 清空当前报告与缓存", use_container_width=True):
      for k in ["s1", "s2", "s3", "s4", "live_data"]:
        st.session_state[k] = ""
      st.session_state.demo_mode = False
      st.rerun()

  global_stream_status = st.empty()
  global_stream_box = st.empty()

  t1, t2, t3, t4, t5, t_live = st.tabs([
      "📐 Stage 1: 工艺规格与海关关税",
      "🏡 Stage 2: 地材环境与场景应用",
      "📦 Stage 3: 市场在售形态与包装装运",
      "💬 Stage 4: 行业技术语言与询盘参数库",
      "📄 完整报告导出",
      "🌐 抓取的一手市场数据",
  ])

  with t1:
    c_sub1, _ = st.columns([1, 4])
    with c_sub1:
      btn_re_s1 = st.button("⚡ 单独生成 Stage 1", key="btn_single_s1")
    p_s1 = st.empty()
    if st.session_state.s1:
      p_s1.markdown(st.session_state.s1)
  with t2:
    c_sub2, _ = st.columns([1, 4])
    with c_sub2:
      btn_re_s2 = st.button("⚡ 单独生成 Stage 2", key="btn_single_s2")
    p_s2 = st.empty()
    if st.session_state.s2:
      p_s2.markdown(st.session_state.s2)
  with t3:
    c_sub3, _ = st.columns([1, 4])
    with c_sub3:
      btn_re_s3 = st.button("⚡ 单独生成 Stage 3", key="btn_single_s3")
    p_s3 = st.empty()
    if st.session_state.s3:
      p_s3.markdown(st.session_state.s3)
  with t4:
    c_sub4, _ = st.columns([1, 4])
    with c_sub4:
      btn_re_s4 = st.button("⚡ 单独生成 Stage 4", key="btn_single_s4")
    p_s4 = st.empty()
    if st.session_state.s4:
      p_s4.markdown(st.session_state.s4)
  with t5:
    if any([
        st.session_state.s1,
        st.session_state.s2,
        st.session_state.s3,
        st.session_state.s4,
    ]):
      full_rep = f"""# 宁波威霖住宅设施 · {final_cat} ({final_size}) 北美市场产品认知报告
生产基地: {supply_origin} | 贸易方式: {trade_terms} | 目标渠道: {target_channel}
分析引擎: {selected_provider} ({actual_model}) | 报告日期: {time.strftime('%Y-%m-%d')}

---
## Stage 1: 物理配合尺寸、制造工艺、工程标准与关税装柜
{st.session_state.s1}
---
## Stage 2: 地材环境适配、扫地机越障与冷暖温差工况全景
{st.session_state.s2}
---
## Stage 3: 北美在售产品形态解构、买手渠道包装与海运装柜标准
{st.session_state.s3}
---
## Stage 4: 行业技术语言、买手 RFQ 询盘技术参数应答库与签样规范
{st.session_state.s4}
"""
      st.download_button(
          "📥 一键下载完整 Markdown 认知报告",
          full_rep,
          f"Runner_HVAC_Product_Knowledge_{final_size.replace(' ', '_')}.md",
          "text/markdown",
          use_container_width=True,
      )
      st.markdown(full_rep)
    else:
      st.info("尚未生成任何阶段报告，请勾选上方阶段并点击运行。")
  with t_live:
    if st.session_state.live_data:
      st.markdown(st.session_state.live_data)

  SINGLE_PROMPTS = {
      "s1": """
请执行【Stage 1: 物理配合尺寸、制造工艺、工程标准与关税大表】：
1. 尺寸解耦与工程图公差：详细拆解标称 Duct Opening 开孔尺寸、落入风管的箱体 Drop-in Box 负公差配合尺寸（标准余量 -1/8" 至 -3/16" 确保徒手轻松装入）、外边框 Faceplate 外径与凸出地板高度；
2. 威霖工厂制造工艺图谱：高压压铸铝 A380 / SPCC 冷轧钢连续冲压 / 6063-T5 铝挤型材成型工法，模具结构与生产周期；双涂层电泳+环保静电粉末喷涂技术与 ASTM B117 盐雾测试标准；
3. 北美暖通硬性工程标准：IBC 集中点载荷承重标准 (>=300 lbs 踩踏测试)、ADA Heel-proof 防卡鞋跟尺寸门槛 (<9.5mm / 0.375" 网孔间距)、有效开孔率 Free Area % 与 CFM 风阻压降曲线；
4. 外贸关税与物流数据：该品类海关 HS Code 归类、美国 301 关税税率，从【宁波总部】与【建霖泰国海外工厂】出货的关税合规对比。
严格使用 7 级置信度标签。
""",
      "s2": """
请执行【Stage 2: 地材环境适配、扫地机越障与冷暖温差工况全景】：
1. 复杂地面地材物理适配：实木地板防刮花、LVP/SPC 超薄石塑锁扣地板防边缘压裂、厚绒地毯对风门调节开关的干涉、瓷砖基层的平整承托；
2. 智能扫地机器人交互：面罩外缘坡度倒角规范（必须 <3mm 缓坡斜边设计）、防止扫地机越障卡轮与碰撞误触损坏风门开关；
3. 暖通极端冷热温差循环实况：冬季 140°F 强暖风热膨胀与金属摩擦异响 (Squeaking) 控制、夏季 55°F 冷风冷凝水积聚防锈防霉表现；
4. 赤脚踩踏脚感与人体工学：网孔格栅平滑度、边缘倒角处理。
严格使用 7 级置信度标签。
""",
      "s3": """
请执行【Stage 3: 北美在售产品形态解构、买手渠道包装与海运装运标准】：
1. 北美在售同类竞品主流物理架构拆解：目前市场上主流品牌（如 Accord, TruAire, Decor Grates, Shoemaker）在该规格上的物理结构与配置分级；
2. 采购渠道包装形态标准：
   - Retail 商超零售渠道（Home Depot / Lowe's）：单件热缩膜包覆 + 条形码背卡 (Shrink Wrap with Barcode Backer) / 双泡壳 (Double Blister Pack)，ISTA-1A 包装跌落测试要求；
   - Pro 工程批发渠道（Ferguson 等）：10-20 件工业牛皮纸大箱散装 (Bulk Pack)，降低开箱包装废弃物；
   - E-Commerce 电商渠道：抗跌落小包裹轻量化保护设计；
3. 集装箱装运装载率（40HQ Container CBM）：预估单箱体积、整柜装箱数量及美标托盘（US Standard Pallet 48x40"）打托堆叠方案。
严格使用 7 级置信度标签。
""",
      "s4": """
请执行【Stage 4: 行业技术语言、买手 RFQ 询盘技术参数应答库与签样规范】：
1. 建立【北美暖通买手地道专业技术参数中英文对照库】：涵盖如 CFM, Free Area, Neck Size, Face Flange, Louver, Opposed Blade Damper, Drop-in Fit 等核心专业词汇及标准定义；
2. 【外贸新业务员 RFQ 询盘应答标准技术表】：当北美建材商超买手或批发商工程总监询问风阻压降、材质厚度、点承重检测、盐雾报告、开孔配合余量等关键参数时，业务员应提供的权威工程数据与技术回复范本；
3. 发送给北美买手的【出样签样工程确认清单 (Sample PSS Checklist)】：包括实测公差、涂层膜厚、包装唛头条码核验等交付前必检清单。
严格使用 7 级置信度标签。
""",
  }

  if run_single:
    if not api_key:
      st.error(f"请先在左侧输入 {selected_provider} 的 API Key！")
    elif not any([exec_s1, exec_s2, exec_s3, exec_s4]):
      st.warning("您未勾选任何阶段，请在上方勾选至少一个阶段后再启动！")
    else:
      try:
        ctx = get_single_ctx()
        stage_map = [
            (
                exec_s1,
                "s1",
                "Stage 1 (工艺规格与海关关税)",
                SINGLE_PROMPTS["s1"],
                p_s1,
            ),
            (
                exec_s2,
                "s2",
                "Stage 2 (地材环境与场景应用)",
                SINGLE_PROMPTS["s2"],
                p_s2,
            ),
            (
                exec_s3,
                "s3",
                "Stage 3 (市场在售形态与渠道包装)",
                SINGLE_PROMPTS["s3"],
                p_s3,
            ),
            (
                exec_s4,
                "s4",
                "Stage 4 (行业技术语言与询盘参数库)",
                SINGLE_PROMPTS["s4"],
                p_s4,
            ),
        ]

        active_tasks = [item for item in stage_map if item[0]]
        for idx, (_, key_name, label_name, prompt_content, p_holder) in (
            enumerate(active_tasks, 1)
        ):
          global_stream_status.info(
            f"⏳ [{idx}/{len(active_tasks)}] 正在流式输出：{label_name}..."
        )
          st.session_state[key_name] = stream_llm_response(
              selected_provider,
              actual_model,
              api_key,
              base_url,
              SOP_A_SYSTEM_INSTRUCTION,
              ctx + prompt_content,
              (global_stream_box, p_holder),
          )

        global_stream_status.success(
            "🎉 选中的阶段全部输出完成！请在对应 Tab 中查看与下载。"
        )
        global_stream_box.empty()
      except Exception as e:
        global_stream_status.error(f"❌ 运行发生异常: {e}")

  # 单独重新生成单个阶段
  for btn_item, key_str, p_target, prompt_text, lbl in [
      (btn_re_s1, "s1", p_s1, SINGLE_PROMPTS["s1"], "Stage 1"),
      (btn_re_s2, "s2", p_s2, SINGLE_PROMPTS["s2"], "Stage 2"),
      (btn_re_s3, "s3", p_s3, SINGLE_PROMPTS["s3"], "Stage 3"),
      (btn_re_s4, "s4", p_s4, SINGLE_PROMPTS["s4"], "Stage 4"),
  ]:
    if btn_item:
      if not api_key:
        st.error("请输入 API Key！")
      else:
        try:
          with st.spinner(f"正在单独流式生成 {lbl}..."):
            ctx = get_single_ctx()
            res = stream_llm_response(
                selected_provider,
                actual_model,
                api_key,
                base_url,
                SOP_A_SYSTEM_INSTRUCTION,
                ctx + prompt_text,
                p_target,
            )
            st.session_state[key_str] = res
          st.success(f"{lbl} 生成成功！")
        except Exception as e:
          st.error(f"{lbl} 生成失败: {e}")

# ==================== 模式 B: 竞品横向技术对标 (Benchmark) ====================
else:
  for k in ["cp1", "cp2", "cp3", "cp4", "comp_live_data"]:
    if k not in st.session_state:
      st.session_state[k] = ""

  st.markdown("### 📋 竞品横向技术与规格对标输入单")

  c_b_cat, c_b_size = st.columns(2)
  with c_b_cat:
    b_cat_choice = st.selectbox(
        "对标品类*", MARKET_SPECS["categories"], index=0
    )
    b_cat_cust = ""
    if "自定义" in b_cat_choice:
      b_cat_cust = st.text_input(
          "输入自定义品类", placeholder="例如: 极简地板出风口"
      )
    final_b_cat = parse_selection(b_cat_choice, b_cat_cust, "品类")

  with c_b_size:
    b_size_choice = st.selectbox(
        "标称开孔尺寸*", MARKET_SPECS["sizes"], index=0
    )
    b_size_cust = ""
    if "自定义" in b_size_choice:
      b_size_cust = st.text_input(
          "输入自定义尺寸", placeholder="例如: 4x10 inches"
      )
    final_b_size = parse_selection(b_size_choice, b_size_cust, "尺寸")

  st.markdown("---")
  st.markdown("**1. 威霖目标款 / 推荐款 (Wellmien Target Offering)**")
  cb1, cb2 = st.columns(2)
  with cb1:
    b_name = st.text_input(
        "威霖款标称名称*",
        value=(
            "威霖重型铸铝装饰风口 (Wellmien Cast Aluminum)"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: 威霖重型铸铝装饰风口",
    )
  with cb2:
    b_spec = st.text_input(
        "材质工艺与建议零售价*",
        value=(
            "A380压铸铝+ABS阻尼风门, 哑光黑粉末喷涂, MSRP $18-$25"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: A380高压压铸铝, 哑光黑静电喷涂, MSRP $18-$25",
    )

  st.markdown("**2. 对照竞品 A (主流商超低价冲压钢走量款)**")
  ca1, ca2 = st.columns(2)
  with ca1:
    a_name = st.text_input(
        "竞品 A 名称*",
        value=(
            "商超冷轧钢冲压条缝款 (Home Depot Stamped Steel)"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: Accord / TruAire 冲压冷轧钢款",
    )
  with ca2:
    a_spec = st.text_input(
        "材质工艺与零售价*",
        value=(
            "0.6mm薄冷轧板冲压, 简易烤漆, MSRP $6-$10"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: 0.6mm薄冷轧钢冲压, 简易白色烤漆, MSRP $6-$10",
    )

  st.markdown("**3. 对照竞品 B (高端现代极简隐形款)**")
  c_b1, c_b2 = st.columns(2)
  with c_b1:
    b2_name = st.text_input(
        "竞品 B 名称*",
        value=(
            "无框齐平隐形风口 (Aria Vent / Flush Mount)"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: Aria Vent / Fittes 现代极简隐形款",
    )
  with c_b2:
    b2_spec = st.text_input(
        "材质工艺与零售价*",
        value=(
            "6063铝挤型材/可内嵌地板, 阳极氧化, MSRP $35-$55"
            if st.session_state.demo_mode
            else ""
        ),
        placeholder="例如: 6063-T5铝挤型材+ABS底盘, MSRP $35-$55",
    )

  bench_focus = st.text_area(
      "重点横向对标方向",
      value=(
          "1. 承重踩踏耐用性 (IBC 300 lbs) 与材质抗腐蚀对比\n2."
          " 扫地机器人越障通过性与边缘坡度设计对比\n3. 渠道包装形态、40HQ"
          " 柜容与海关 HS Code 关税差异\n4. 徒手直接更换 (Drop-in) 与现场复杂切砖"
          " (Flush Mount) 的工时对比"
          if st.session_state.demo_mode
          else ""
      ),
      placeholder="例如: 关注承重强度、风量通风率 Free Area%、包装体积与运输成本对比",
  )

  def ensure_comp_live():
    if not st.session_state.comp_live_data:
      with st.spinner("🌐 正在全网检索对标竞品的官方规格表与行业数据..."):
        q1 = f"{final_b_cat} {final_b_size} cast aluminum stamped steel specifications"
        q2 = (
            f"{final_b_cat} flush mount floor register aria vent technical"
            " details"
        )
        st.session_state.comp_live_data = (
            f"### 传统铸铝与冲压钢款技术参数:\n{search_live_web(q1, 2)}\n\n###"
            f" 现代极简隐形款技术参数:\n{search_live_web(q2, 2)}"
        )

  def get_comp_ctx():
    ensure_comp_live()
    return f"""
【竞品横向技术对标条件】
- 对标品类: {final_b_cat} | 标称开孔尺寸: {final_b_size}
- 威霖基准款: {b_name} | 特性参数: {b_spec}
- 对照竞品 A: {a_name} | 特性参数: {a_spec}
- 对照竞品 B: {b2_name} | 特性参数: {b2_spec}
- 供应链背景: 出货基地【{supply_origin}】 | 贸易条款【{trade_terms}】 | 渠道包装【{target_channel}】
- 重点对标方向: {bench_focus}

<external_market_evidence>
{st.session_state.comp_live_data}
</external_market_evidence>
"""

  BENCHMARK_PROMPTS = {
      "cp1": """
请执行【竞品对标维度一：工程技术参数、制造工法与关税装柜横向大表】：
1. 输出标准 Markdown 横向对比矩阵大表，客观横向对比【威霖目标款】、【竞品 A 冲压薄铁款】、【竞品 B 极简隐形款】：
   - 材质与模具成型工法（压铸铸铝 A380 vs SPCC 冷轧级进冲压 vs 6063-T5 铝挤/CNC）；
   - 表面处理体系（双涂层静电粉末喷涂 vs 普通烤漆 vs 阳极氧化；ASTM B117 盐雾测试耐久度）；
   - 物理配合尺寸与公差（Duct Opening 开孔配合公差、Drop-in Box 负公差配合、面罩外框厚度）；
   - 通风流体与承重性能（Free Area % 有效开孔率、CFM 风阻压降、IBC 300 lbs 集中载荷抗下沉变形指标、Heel-Proof 防卡鞋跟）；
   - 外贸商业参数：建议零售价 MSRP、海关 HS Code 编码、美国 301 关税影响预估、40HQ 装箱容积 CBM。
严格使用 7 级置信度标签。
""",
      "cp2": """
请执行【竞品对标维度二：地材适配兼容、扫地机器人通过性与极端工况对比】：
1. 横向深度对比三款产品在建筑实际应用中的客观表现：
   - 复杂地材适配：实木地板、LVP/SPC 超薄石塑锁扣地板、瓷砖基层的平整支撑与受力分布；
   - 扫地机器人干涉雷达：外唇坡度倒角是否顺畅（是否 <3mm 缓坡斜边设计）、卡轮脱困表现、外露拨片碰撞耐受性；
   - 暖通冷热交替循环极限工况：冬季 140°F 强暖风（金属热膨胀形变与摩擦异响 Squeaking 控制、ABS 阀体耐温表现）与夏季冷凝水防锈表现；
   - 安装耗时与人工门槛：普通消费者徒手落入更换 (Drop-in) 耗时（约10秒） vs 隐形款现场精确切割地板砖瓦（约30-60分钟+专业师傅工费）。
严格使用 7 级置信度标签。
""",
      "cp3": """
请执行【竞品对标维度三：市场在售形态定位、包装工程与海运物流成本对比】：
1. 市场价格带与产品层级梯队定位全景（入门经济型 vs 经典装饰升级型 vs 高端建筑师指定型）；
2. 包装交付与物流防护对比：
   - 零售商超挂卡吸塑（Retail Blister） vs 工程大箱牛皮纸散装（Pro Bulk） vs 电商防摔盒的体积（CBM）与保护性能；
   - 预估单箱重量（Gross Weight）与运输堆叠稳定性；
3. 渠道流通便利性与综合物流综合成本对比。
严格使用 7 级置信度标签。
""",
      "cp4": """
请执行【竞品对标维度四：技术规格横向总结与外贸业务员专业参数交流库】：
1. 技术差异化总结大表：威霖款相比竞品 A 的核心工程升级指标、相比竞品 B 的便捷更换成本优势；
2. 【外贸新业务员技术型商务交流库】：
   - 当北美商超买手（Retail Buyer）或批发商采购主管拿竞品 A（低价冲压钢）与威霖铸铝款对比价格时，业务员如何从 IBC 300 磅点承重不变形、全铝永不生锈、静音 ABS 阻尼阀等技术参数进行专业参数抗辩？
   - 针对不同买手类型（商超 vs 工程批发）的出样检测报告清单（ASTM 盐雾报告、承重检测认证、配合公差图纸）。
严格使用 7 级置信度标签。
""",
  }

  st.markdown("---")
  st.markdown("#### 🎯 选择本次需要对标的维度 (可自由勾选)")
  col_cp1, col_cp2, col_cp3, col_cp4 = st.columns(4)
  with col_cp1:
    exec_cp1 = st.checkbox(
        "维度 1: 规格工艺与关税大表",
        value=True,
        help="对比材质、成型模具、尺寸公差、承重标准与 HS Code 关税",
    )
  with col_cp2:
    exec_cp2 = st.checkbox(
        "维度 2: 地材兼容与场景应用",
        value=True,
        help="对比实木/LVP适配、扫地机越障坡度、冷暖风循环异响",
    )
  with col_cp3:
    exec_cp3 = st.checkbox(
        "维度 3: 市场形态与包装物流",
        value=True,
        help="对比零售吸塑 vs 批发工模大箱包装、CBM 装箱率",
    )
  with col_cp4:
    exec_cp4 = st.checkbox(
        "维度 4: 技术总结与买手参数库",
        value=True,
        help="技术指标总结、买手技术参数抗辩与样品签样规范",
    )

  col_b_run1, col_b_run2 = st.columns(2)
  with col_b_run1:
    run_comp_all = st.button(
        "🚀 运行选中的对标维度 (流式输出)",
        type="primary",
        use_container_width=True,
    )
  with col_b_run2:
    if st.button("🔄 清空竞品对标缓存", use_container_width=True):
      for k in ["cp1", "cp2", "cp3", "cp4", "comp_live_data"]:
        st.session_state[k] = ""
      st.session_state.demo_mode = False
      st.rerun()

  global_comp_status = st.empty()
  global_comp_box = st.empty()

  ct1, ct2, ct3, ct4, ct5, ct_live = st.tabs([
      "📊 维度 1: 规格工艺与关税大表",
      "🏡 维度 2: 地材兼容与场景应用",
      "📦 维度 3: 市场形态与包装物流",
      "💬 维度 4: 技术总结与买手参数库",
      "📑 完整对标报告导出",
      "🌐 抓取的竞品全网数据",
  ])

  with ct1:
    c_btn_cp1, _ = st.columns([1, 4])
    with c_btn_cp1:
      re_cp1 = st.button("⚡ 单独生成维度 1", key="btn_c1")
    ph_cp1 = st.empty()
    if st.session_state.cp1:
      ph_cp1.markdown(st.session_state.cp1)
  with ct2:
    c_btn_cp2, _ = st.columns([1, 4])
    with c_btn_cp2:
      re_cp2 = st.button("⚡ 单独生成维度 2", key="btn_c2")
    ph_cp2 = st.empty()
    if st.session_state.cp2:
      ph_cp2.markdown(st.session_state.cp2)
  with ct3:
    c_btn_cp3, _ = st.columns([1, 4])
    with c_btn_cp3:
      re_cp3 = st.button("⚡ 单独生成维度 3", key="btn_c3")
    ph_cp3 = st.empty()
    if st.session_state.cp3:
      ph_cp3.markdown(st.session_state.cp3)
  with ct4:
    c_btn_cp4, _ = st.columns([1, 4])
    with c_btn_cp4:
      re_cp4 = st.button("⚡ 单独生成维度 4", key="btn_c4")
    ph_cp4 = st.empty()
    if st.session_state.cp4:
      ph_cp4.markdown(st.session_state.cp4)
  with ct5:
    if any([
        st.session_state.cp1,
        st.session_state.cp2,
        st.session_state.cp3,
        st.session_state.cp4,
    ]):
      full_comp_rep = f"""# 宁波威霖住宅设施 · {final_b_cat} ({final_b_size}) 竞品技术横向对标报告
生产基地: {supply_origin} | 贸易方式: {trade_terms} | 目标渠道: {target_channel}
对标引擎: {selected_provider} ({actual_model}) | 报告日期: {time.strftime('%Y-%m-%d')}

---
## 维度一：工程技术参数、制造工法与关税装柜横向大表
{st.session_state.cp1}
---
## 维度二：地材适配兼容、扫地机器人通过性与极端工况对比
{st.session_state.cp2}
---
## 维度三：市场在售形态定位、包装工程与海运物流成本对比
{st.session_state.cp3}
---
## 维度四：技术规格横向总结与外贸业务员专业参数交流库
{st.session_state.cp4}
"""
      st.download_button(
          "📥 一键下载完整 Markdown 对标报告",
          full_comp_rep,
          f"Runner_HVAC_Benchmark_{final_b_size.replace(' ', '_')}.md",
          "text/markdown",
          use_container_width=True,
      )
      st.markdown(full_comp_rep)
    else:
      st.info("尚未生成对标报告，请勾选维度并点击启动。")
  with ct_live:
    if st.session_state.comp_live_data:
      st.markdown(st.session_state.comp_live_data)

  if run_comp_all:
    if not api_key:
      st.error(f"请先在左侧输入 {selected_provider} 的 API Key！")
    elif not any([exec_cp1, exec_cp2, exec_cp3, exec_cp4]):
      st.warning("您未勾选任何对标维度，请勾选后重试！")
    else:
      try:
        ctx_c = get_comp_ctx()
        comp_tasks = [
            (
                exec_cp1,
                "cp1",
                "维度 1 (规格工艺与关税大表)",
                BENCHMARK_PROMPTS["cp1"],
                ph_cp1,
            ),
            (
                exec_cp2,
                "cp2",
                "维度 2 (地材兼容与场景应用)",
                BENCHMARK_PROMPTS["cp2"],
                ph_cp2,
            ),
            (
                exec_cp3,
                "cp3",
                "维度 3 (市场形态与包装物流)",
                BENCHMARK_PROMPTS["cp3"],
                ph_cp3,
            ),
            (
                exec_cp4,
                "cp4",
                "维度 4 (技术总结与买手参数库)",
                BENCHMARK_PROMPTS["cp4"],
                ph_cp4,
            ),
        ]
        active_comp_tasks = [item for item in comp_tasks if item[0]]

        for idx, (_, k_code, lbl_text, prompt_body, ph_box) in enumerate(
            active_comp_tasks, 1
        ):
          global_comp_status.info(
              f"⏳ [{idx}/{len(active_comp_tasks)}] 正在流式对比：{lbl_text}..."
          )
          st.session_state[k_code] = stream_llm_response(
              selected_provider,
              actual_model,
              api_key,
              base_url,
              SOP_A_SYSTEM_INSTRUCTION,
              ctx_c + prompt_body,
              (global_comp_box, ph_box),
          )

        global_comp_status.success(
            "🎉 选中的竞品对标维度全部完成！可在各 Tab 查看与下载。"
        )
        global_comp_box.empty()
      except Exception as e:
        global_comp_status.error(f"❌ 竞品对标运行异常: {e}")

  # 竞品各分维度单独生成
  for btn_item, key_str, p_target, prompt_text, lbl in [
      (re_cp1, "cp1", ph_cp1, BENCHMARK_PROMPTS["cp1"], "维度 1"),
      (re_cp2, "cp2", ph_cp2, BENCHMARK_PROMPTS["cp2"], "维度 2"),
      (re_cp3, "cp3", ph_cp3, BENCHMARK_PROMPTS["cp3"], "维度 3"),
      (re_cp4, "cp4", ph_cp4, BENCHMARK_PROMPTS["cp4"], "维度 4"),
  ]:
    if btn_item:
      if not api_key:
        st.error("请输入 API Key！")
      else:
        try:
          with st.spinner(f"正在单独流式生成 {lbl}..."):
            ctx_c = get_comp_ctx()
            res = stream_llm_response(
                selected_provider,
                actual_model,
                api_key,
                base_url,
                SOP_A_SYSTEM_INSTRUCTION,
                ctx_c + prompt_text,
                p_target,
            )
            st.session_state[key_str] = res
          st.success(f"{lbl} 生成成功！")
        except Exception as e:
          st.error(f"{lbl} 生成失败: {e}")
