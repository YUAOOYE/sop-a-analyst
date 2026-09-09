import os
import time
from google import genai
from google.genai import types
import streamlit as st

try:
  from duckduckgo_search import DDGS

  HAS_DDGS = True
except ImportError:
  HAS_DDGS = False

st.set_page_config(
    page_title="SOP A V1.1 - Product Understanding & Dynamic Market Engine",
    page_icon="🔍",
    layout="wide",
)

SOP_A_SYSTEM_INSTRUCTION = """
You are a senior US Market Product Understanding & Application Research Analyst executing SOP A V1.1.
Your sole mission is to thoroughly understand physical products in the North American market.

Strict Boundaries:
- DO NOT perform product design, new SKU definition, structural redesign, cost analysis, or listing copywriting.
- Focus strictly on understanding the product as it exists in the market.

Dynamic Scenarios Radar (A11.5 - Must Address Emerging Trends):
- Robot Vacuum Interference: Floor clearance, beveled edge height (<3mm) to prevent wheel hang-up, protection of damper levers from collisions.
- Modern Thin Flooring: Ultra-thin SPC/LVP brittle edge cracking under point loads, expansion clearances.
- Architectural Flush Aesthetics: Frameless flush-mount registers (e.g. Aria Vent style), magnetic quick-release grilles.
- Pet & Micro-environment Pain Points: Drop-in mesh vent screens for pet hair, noise prevention (squeaking).

Evidence & Sourcing Protocol:
- Prioritize Tier 1 (Manufacturer cut sheets, ASHRAE Standard 70, IBC/IRC building codes), Tier 2 (Home Depot, Lowe's, Menards technical tables), and Tier 3 (Verified buyer reviews, contractor jobsite teardown videos, Reddit r/HVAC, r/HomeImprovement, r/Flooring).
- Prohibited Sources: 3D CGI lifestyle renders and AI-generated images must NEVER be used as physical real-world evidence.
- 2-Source Corroboration: High-frequency defects or non-standard specs require at least two independent corroborating sources.

7-Tier Confidence Tagging:
Every factual claim must carry one tag:
【FACT】 / 【HIGH CONFIDENCE】 / 【INFERENCE】 / 【USER EXPERIENCE】 / 【INDUSTRY INFERENCE】 / 【UNVERIFIED】 / 【UNKNOWN】
Missing data tags: 【未找到】 / 【无法验证】 / 【行业推断】

Deliverables Schema:
1. Product Understanding Report (Addressing all 22 Core Questions)
2. Product Specification Database (3-tier dimensions: Duct Opening vs Drop-in Box vs Faceplate Flange, Free Area %, Heel-proof limit, Load capacity, finishes)
3. Application Scenario Matrix (4D: Spatial Zones × Substrates [Hardwood/LVP/Tile/Carpet] × Physical Load × HVAC Cycles + Emerging Trends)
4. Real-world Image Evidence Database (Evidence ID, Category, Clickable Source URL, Substrate/Space Context, Observed Physical Fact/Pain Point)
5. Market Language Database (Industry Terms, Retail Terms, Consumer Terms, High-converting Search Terms)
"""

st.markdown("## 🔍 SOP A V1.1 动态产品认知与应用场景分析系统")
st.caption(
    "集成开源实时全网检索（DuckDuckGo Live RAG）| 零 429 配额限制 |"
    " 实时捕捉北美市场最新应用场景"
)


def search_live_web(query, max_results=4):
  if not HAS_DDGS:
    return "（未检测到 duckduckgo-search 库，使用内置行业数据库）"
  try:
    ddgs = DDGS()
    results = []
    for r in ddgs.text(query, max_results=max_results):
      results.append(
          f"- 来源标题: {r.get('title')}\n  链接: {r.get('href')}\n  实时摘要:"
          f" {r.get('body')}"
      )
    return "\n\n".join(results) if results else "（无相关实时返回）"
  except Exception as e:
    return f"（实时检索网络波动: {e}）"


with st.sidebar:
  st.header("⚙️ 引擎配置")

  default_key = ""
  if "GEMINI_API_KEY" in st.secrets:
    default_key = st.secrets["GEMINI_API_KEY"]
  elif os.environ.get("GEMINI_API_KEY"):
    default_key = os.environ.get("GEMINI_API_KEY")

  api_key_input = st.text_input(
      "Gemini API Key",
      value=default_key,
      type="password",
      help="从 Google AI Studio 获取的免费 API Key",
  )
  api_key = api_key_input.strip()

  model_name = st.selectbox(
      "选择模型",
      options=[
          "gemini-3.6-flash",
          "gemini-1.5-flash",
          "gemini-3.8-flash",
          "gemini-1.5-pro",
      ],
      index=0,
  )

  st.markdown("---")
  st.header("📋 A00 项目启动单")
  product_name = st.text_input(
      "产品标称名称*", value="Decorative Floor Register (美标装饰性地板出风口)"
  )
  nominal_size = st.text_input("标称开孔尺寸*", value="4x10 inches")
  ref_links = st.text_area(
      "参考链接*",
      value=(
          "https://www.homedepot.com/b/Heating-Venting-Cooling-HVAC-Supprives-Registers-Grilles/Floor-Register/N-5yc1vZc4ncZ1z0vj6i"
      ),
  )
  material_spec = st.text_input(
      "材质与工艺限定 (可选)",
      value="Heavy-duty Cast Aluminum, Matte Black powder coat",
  )
  focus_points = st.text_area(
      "核心约束 (可选)",
      value=(
          "1. 重点考察防卡鞋跟标准 (Heel-proof < 9.5mm)\n2."
          " 重点考察实木/LVP/瓷砖地面的安装干涉与扫地机器人避障\n3."
          " 重点核查真实买家对风门拨片损坏与生锈的抱怨"
      ),
  )


def execute_stage(client, model, stage_prompt, stage_name):
  config = types.GenerateContentConfig(
      system_instruction=SOP_A_SYSTEM_INSTRUCTION, temperature=0.2
  )
  with st.spinner(f"正在深度分析并构建: {stage_name}..."):
    response = client.models.generate_content(
        model=model, contents=stage_prompt, config=config
    )
    return response.text


for k in ["s1", "s2", "s3", "s4", "live_data"]:
  if k not in st.session_state:
    st.session_state[k] = ""

if st.button("🚀 启动 SOP A 实时深度流水线", type="primary"):
  if not api_key:
    st.error("请先在左侧输入 Gemini API Key")
  else:
    try:
      client = genai.Client(api_key=api_key)

      # --- 步骤 0: 实时全网检索（无需 Google API 配额，直接开源抓取） ---
      with st.spinner(
          "🌐 正在全网实时抓取 Home Depot、Lowe's 及 Reddit"
          " 社区最新讨论与前沿场景..."
      ):
        q1 = (
            f"{product_name} {nominal_size} specifications Home Depot Lowe's"
        )
        q2 = (
            f"{product_name} floor register robot vacuum LVP tile issues"
            " Reddit"
        )
        q3 = f"{product_name} floor vent customer complaints broken rusted"

        live_web_1 = search_live_web(q1, max_results=3)
        live_web_2 = search_live_web(q2, max_results=3)
        live_web_3 = search_live_web(q3, max_results=3)
        st.session_state.live_data = (
            f"### 规格检索\n{live_web_1}\n\n### 场景与干涉检索\n{live_web_2}\n\n###"
            f" 买家缺陷讨论\n{live_web_3}"
        )

      a00_ctx = f"""
【A00 项目输入参数】
- 产品名称: {product_name}
- 标称开孔尺寸: {nominal_size}
- 权威参考链接: {ref_links}
- 材质与表面: {material_spec}
- 核心约束: {focus_points}

【最新全网实时检索一手数据（含公开参考链接）】
{st.session_state.live_data}
"""

      # Stage 1: 物理架构与规格库
      p1 = (
          a00_ctx
          + "\n请结合实时检索数据，执行 SOP A V1.1 的【第一阶段：物理架构与工程规格】(A01-A06)，解耦三大尺寸基准，建立【Product"
          " Specification Database】表格。"
      )
      st.session_state.s1 = execute_stage(
          client, model_name, p1, "Stage 1 物理规格库"
      )

      # Stage 2: 场景矩阵与新兴场景雷达
      p2 = (
          a00_ctx
          + "\n基于前期结论与实时检索，请执行 SOP A V1.1"
          " 的【第二阶段：环境适配与四维场景矩阵】(A07-A11)，务必纳入 A11.5"
          " 扫地机器人避障、超薄SPC脆裂、齐平隐形风口等新兴场景，建立【Application"
          " Scenario Matrix】表格。"
      )
      st.session_state.s2 = execute_stage(
          client, model_name, p2, "Stage 2 场景矩阵与前沿场景"
      )

      # Stage 3: 真实证据与语言库
      p3 = (
          a00_ctx
          + "\n基于前期结论与实时检索，请执行 SOP A V1.1"
          " 的【第三阶段：真实证据与市场语言库】(A12-A14)，建立【Real-world Image Evidence"
          " Database】（利用实时检索中获取的真实买家/评测链接）与【Market Language"
          " Database】。严格排除 3D CGI 图。"
      )
      st.session_state.s3 = execute_stage(
          client, model_name, p3, "Stage 3 真实证据与语言库"
      )

      # Stage 4: 总结与闭环验收
      p4 = (
          a00_ctx
          + "\n基于前述成果，请执行 SOP A V1.1"
          " 的【第四阶段：认知总装与闭环验收】(A15)，并逐一回答 22 个核心问题清单。"
      )
      st.session_state.s4 = execute_stage(
          client, model_name, p4, "Stage 4 22核心问题闭环"
      )

      st.success("🎉 SOP A 实时全流程调研圆满完成！")
    except Exception as e:
      st.error(f"调用发生错误: {e}")

if st.session_state.s1:
  t1, t2, t3, t4, t5, t_live = st.tabs([
      "📐 物理规格库",
      "🏡 四维场景矩阵 (含新兴雷达)",
      "📸 真实证据与语言",
      "🎯 22问题闭环",
      "📄 完整报告下载",
      "🌐 抓取的实时网页数据",
  ])
  with t1:
    st.markdown(st.session_state.s1)
  with t2:
    st.markdown(st.session_state.s2)
  with t3:
    st.markdown(st.session_state.s3)
  with t4:
    st.markdown(st.session_state.s4)
  with t5:
    full_text = f"""# {product_name} 调研报告\n\n{st.session_state.s1}\n\n---\n\n{st.session_state.s2}\n\n---\n\n{st.session_state.s3}\n\n---\n\n{st.session_state.s4}"""
    st.download_button(
        "📥 一键下载完整 Markdown 报告",
        full_text,
        file_name="SOP_A_Report.md",
        mime="text/markdown",
    )
  with t_live:
    st.markdown(st.session_state.live_data)
