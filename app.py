import os
import time
from google import genai
from google.genai import types
import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="SOP A V1.1 - Product Understanding Engine",
    page_icon="🔍",
    layout="wide",
)

SOP_A_SYSTEM_INSTRUCTION = """
You are a senior US Market Product Understanding & Application Research Analyst.
Your sole mission is to thoroughly understand physical products in the North American market by executing SOP A V1.1.

Strict Boundaries:
- DO NOT perform product design, new SKU definition, structural redesign, cost analysis, or listing copywriting.
- Focus strictly on understanding the product as it exists in the market.

Evidence & Sourcing Protocol:
- Prioritize Tier 1 (Manufacturer cut sheets, ASHRAE Standard 70, IBC/IRC building codes), Tier 2 (Home Depot, Lowe's, Menards, SupplyHouse technical tables), and Tier 3 (Verified buyer review photos, contractor jobsite teardown videos, Reddit r/HVAC, r/HomeImprovement, r/Flooring).
- Prohibited Sources: 3D CGI lifestyle renders and AI-generated images must NEVER be used as physical real-world evidence.
- 2-Source Corroboration: High-frequency defects or non-standard specs require at least two independent corroborating sources.

7-Tier Confidence Tagging:
Every factual claim must carry one tag:
【FACT】 / 【HIGH CONFIDENCE】 / 【INFERENCE】 / 【USER EXPERIENCE】 / 【INDUSTRY INFERENCE】 / 【UNVERIFIED】 / 【UNKNOWN】
Missing data tags: 【未找到】 / 【无法验证】 / 【行业推断】

Deliverables Schema:
1. Product Understanding Report (Addressing all 22 Core Questions)
2. Product Specification Database (3-tier dimensions: Duct Opening vs Drop-in Box vs Faceplate Flange, Free Area %, Heel-proof limit, Load capacity, finishes)
3. Application Scenario Matrix (4D: Spatial Zones × Substrates [Hardwood/LVP/Tile/Carpet] × Physical Load × HVAC Cycles)
4. Real-world Image Evidence Database (Evidence ID, Category, Clickable Source URL, Substrate/Space Context, Observed Physical Fact/Pain Point)
5. Market Language Database (Industry Terms, Retail Terms, Consumer Terms, High-converting Search Terms)
"""

st.markdown(
    "## 🔍 SOP A V1.1 产品认知与实际应用场景分析系统 (Cloud App)"
)
st.caption("美国市场深度调研引擎 | 严格遵循 7 级置信度标签与四维真实场景验证")

# --- Sidebar Configuration ---
with st.sidebar:
  st.header("⚙️ 引擎配置")

  # 优先从 Streamlit Secrets 自动读取，若无则从输入框读取
  default_key = ""
  if "GEMINI_API_KEY" in st.secrets:
    default_key = st.secrets["GEMINI_API_KEY"]
  elif os.environ.get("GEMINI_API_KEY"):
    default_key = os.environ.get("GEMINI_API_KEY")

  api_key_input = st.text_input(
      "Gemini API Key",
      value=default_key,
      type="password",
      help="从 Google AI Studio 获取",
  )
  api_key = api_key_input.strip()

  model_name = st.selectbox(
      "选择模型",
      options=[
          "gemini-2.5-flash",
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
          "https://www.homedepot.com/b/Heating-Venting-Cooling-HVAC-Supplies-Registers-Grilles/Floor-Register/N-5yc1vZc4ncZ1z0vj6i"
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
          " 重点考察实木/LVP/瓷砖地面的安装干涉\n3."
          " 重点核查真实买家对风门拨片踩踏损坏的抱怨"
      ),
  )


# --- Helper Function ---
def execute_stage(client, model, stage_prompt, stage_name):
  config = types.GenerateContentConfig(
      system_instruction=SOP_A_SYSTEM_INSTRUCTION,
      temperature=0.2,
      tools=[types.Tool(google_search=types.GoogleSearch())],
  )
  with st.spinner(f"正在深度分析与检索: {stage_name}..."):
    response = client.models.generate_content(
        model=model, contents=stage_prompt, config=config
    )
    return response.text


# --- State Initialization ---
for k in ["s1", "s2", "s3", "s4"]:
  if k not in st.session_state:
    st.session_state[k] = ""

if st.button("🚀 启动 SOP A 深度流水线", type="primary"):
  if not api_key:
    st.error("请先在左侧输入 Gemini API Key")
  else:
    try:
      client = genai.Client(api_key=api_key)
      a00_ctx = f"""
【A00 项目输入参数】
- 产品名称: {product_name}
- 标称开孔尺寸: {nominal_size}
- 权威参考链接: {ref_links}
- 材质与表面: {material_spec}
- 核心约束: {focus_points}
"""
      # Stage 1
      p1 = (
          f"{a00_ctx}\n请执行 SOP A V1.1 的【第一阶段：物理架构与工程规格】(A01-A06)，解耦三大尺寸基准，建立【Product"
          " Specification Database】表格。使用 Google Search 验证数据。"
      )
      st.session_state.s1 = execute_stage(
          client, model_name, p1, "Stage 1 物理规格库"
      )

      # Stage 2
      p2 = (
          f"{a00_ctx}\n基于前期结论，请执行 SOP A V1.1"
          " 的【第二阶段：环境适配与四维场景矩阵】(A07-A11)，建立【Application Scenario"
          " Matrix】表格。使用 Google Search 验证真实工况。"
      )
      st.session_state.s2 = execute_stage(
          client, model_name, p2, "Stage 2 场景矩阵"
      )

      # Stage 3
      p3 = (
          f"{a00_ctx}\n基于前期结论，请执行 SOP A V1.1"
          " 的【第三阶段：真实证据与市场语言库】(A12-A14)，建立【Real-world Image Evidence"
          " Database】与【Market Language Database】。严格排除 3D CGI 图。"
      )
      st.session_state.s3 = execute_stage(
          client, model_name, p3, "Stage 3 真实证据与语言库"
      )

      # Stage 4
      p4 = (
          f"{a00_ctx}\n基于前述成果，请执行 SOP A V1.1"
          " 的【第四阶段：认知总装与闭环验收】(A15)，并逐一回答 22 个核心问题清单。"
      )
      st.session_state.s4 = execute_stage(
          client, model_name, p4, "Stage 4 22核心问题闭环"
      )

      st.success("🎉 SOP A 调研流水线全部完成！")
    except Exception as e:
      st.error(f"调用发生错误: {e}")

# --- Output Display ---
if st.session_state.s1:
  t1, t2, t3, t4, t5 = st.tabs([
      "📐 物理规格库",
      "🏡 四维场景矩阵",
      "📸 真实证据与语言",
      "🎯 22问题闭环",
      "📄 完整报告下载",
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
