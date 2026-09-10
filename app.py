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
    page_title="SOP A V1.2 - Product Understanding & Industrial Research Engine",
    page_icon="🔍",
    layout="wide",
)

SOP_A_SYSTEM_INSTRUCTION = """
You are a senior US Market Product Understanding & Industrial Research Analyst executing SOP A V1.2.
Your sole mission is to thoroughly understand physical products in the North American market, their manufacturing realities, and their application contexts.

Strict Boundaries:
- DO NOT perform product design, new SKU definition, structural redesign, cost analysis, or listing copywriting.
- Focus strictly on understanding the product as it exists in the market, including its manufacturing processes, materials, compliance standards, and failure modes.

Core Nineteen-Step Workflow (SOP A V1.2):
- A00: Project Input Gatekeeping
- A01: Product Identity
- A02: Product Taxonomy (Industry, Retail hierarchy, Consumer mental model)
- A03: Core Function
- A04: Working Principle (Fluid dynamics, structural load distribution)
- A05: Product Architecture (BOM breakdown, assembly joints)
- A05.1: Manufacturing & Material Landscape (Cast Aluminum vs Stamped Steel vs Brass vs ABS vs Wood; Die casting vs Stamping vs Extrusion; Powder coating, Electroplating, Chemical Patina)
- A06: Specification Decoupling (3-tier dimensions: Duct Opening vs Drop-in Box vs Faceplate Flange, Free Area %, Heel-proof <9.5mm, Load capacity, finishes)
- A06.1: Quality Standards & Compliance Gate (IBC/IRC >= 300 lbs point load, ASTM B117 salt spray 24h-48h, thermal stability at 140°F, ADA/IBC heel-proof safety)
- A06.2: Packaging & Hardware Delivery Anatomy (Shrink wrap vs clamshell vs corrugated box; scratch/drop protection; screws, debris trap mesh, EVA gaskets)
- A07: Installation & Substrate Compatibility (Hardwood, LVP/SPC, Tile, Carpet; Drop-in vs Flush-mount)
- A08: Operation (Foot tap, hand lever, friction detent feel)
- A09: Maintenance & Failure Modes (Rust, jam, cleaning, coating peel)
- A10: User Personas (Buyer, Installer, End-user)
- A11: Application Scenario Matrix (4D: Spatial Zones × Substrates × Physical Load × HVAC Cycles)
- A11.5: Emerging Scenarios Radar (Robot vacuum clearance <3mm bevel, ultra-thin SPC edge cracking, frameless flush registers, pet hair mesh filters)
- A12: Real-world Image Evidence Database (Evidence ID, Category, Clickable URL, Substrate Context, Observed Fact/Pain Point)
- A13: Market Language Database (Industry Terms, Retail Terms, Consumer Terms, High-converting Search Terms)
- A14: User Behavior & Lifecycle (Why buy, 4 replacement triggers, RMA return complaint root causes)
- A15: Product Understanding Summary & Enterprise Feasibility (Engineering redlines, tooling constraints, quality traps)

Evidence & Confidence Rules:
- Prioritize Tier 1 (Manufacturer cut sheets, ASHRAE, IBC/IRC), Tier 2 (Home Depot, Lowe's, Menards technical tables), and Tier 3 (Verified buyer reviews, contractor jobsite teardowns, Reddit r/HVAC, r/HomeImprovement, r/Flooring).
- Prohibited Sources: 3D CGI lifestyle renders and AI images must NEVER be used as physical real-world evidence.
- 7-Tier Tags: 【FACT】 / 【HIGH CONFIDENCE】 / 【INFERENCE】 / 【USER EXPERIENCE】 / 【INDUSTRY INFERENCE】 / 【UNVERIFIED】 / 【UNKNOWN】
- Missing Data Tags: 【未找到】 / 【无法验证】 / 【行业推断】
"""

st.markdown(
    "## 🔍 SOP A V1.2 工业级产品认知与实际应用场景分析系统"
)
st.caption(
    "全流程升级至 19 步标准工法 | 深度融合【制造工艺/材质图谱】、【合规检测门槛】、【零售包装交付】与【前沿场景雷达】"
)


def search_live_web(query, max_results=4):
  if not HAS_DDGS:
    return "（未检测到 duckduckgo-search 依赖，使用大模型内置专业知识库）"
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
          "1. 重点分析制造工艺（铸铝压铸 vs 冲压冷轧钢）、成本与缺陷形态\n2. 重点核验"
          " IBC 承重 (>=300 lbs)、ASTM B117 盐雾测试及防卡鞋跟 (<9.5mm)\n3."
          " 重点考察包装随附配件、扫地机器人避障及买家高频退货退款原因"
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

if st.button("🚀 启动 SOP A V1.2 全流程深度流水线", type="primary"):
  if not api_key:
    st.error("请先在左侧输入 Gemini API Key")
  else:
    try:
      client = genai.Client(api_key=api_key)

      with st.spinner(
          "🌐 正在实时检索北美主流商超规格、制造材质标准及真实买家评价..."
      ):
        q1 = (
            f"{product_name} {nominal_size} cast aluminum stamped steel Home"
            " Depot specifications"
        )
        q2 = (
            f"{product_name} floor register ASTM B117 load capacity ADA heel"
            " proof"
        )
        q3 = (
            f"{product_name} floor vent robot vacuum LVP scratch complaints"
            " Reddit"
        )

        live_web_1 = search_live_web(q1, max_results=3)
        live_web_2 = search_live_web(q2, max_results=3)
        live_web_3 = search_live_web(q3, max_results=3)
        st.session_state.live_data = (
            f"### 材质与规格一手数据\n{live_web_1}\n\n###"
            f" 合规与检测标准\n{live_web_2}\n\n###"
            f" 真实痛点与新兴场景\n{live_web_3}"
        )

      a00_ctx = f"""
【A00 项目输入参数】
- 产品名称: {product_name}
- 标称开孔尺寸: {nominal_size}
- 权威参考链接: {ref_links}
- 材质与表面限定: {material_spec}
- 重点关注方向: {focus_points}

【最新全网实时检索数据】
{st.session_state.live_data}
"""

      # Stage 1: 物理架构、制造工艺与合规规格 (A01 - A06.2)
      p1 = (
          a00_ctx
          + """
请执行 SOP A V1.2 的【第一阶段：物理架构、制造工艺与工程规格】：
1. A01 Product Identity & A02 Product Taxonomy: 明确产品身份与三层类目路径。
2. A03 Core Function & A04 Working Principle: 气流动力学、阻尼调节与承重受力传导。
3. A05 Product Architecture: 机械 BOM 零件拆解与装配方式。
4. ★ A05.1 Manufacturing & Material Landscape（市场制造工艺与材质图谱）：
   - 深入对比市场主流材质（铸铝、冲压冷轧钢、黄铜、ABS塑料、实木）的性能、档次分布与成本差异；
   - 成型工艺（压铸 vs 连续模冲压）固有缺陷形态分析（毛刺割手 vs 铸造尖角积粉）；
   - 表面处理（静电粉末喷涂 Matte Black、电镀拉丝镍、化学古铜）工艺与附着力要求。
5. A06 Specification Decoupling: 严格解耦三大尺寸（Duct Opening vs Drop-in Box vs Faceplate Flange）、Free Area %。
6. ★ A06.1 Quality Standards & Compliance Gate（质量检测与合规门槛）：
   - IBC/IRC 集中静载荷承重标准（>=300 lbs）；
   - ASTM B117 盐雾防腐测试（24h-48h）；
   - 120°F-140°F 强制暖风连续耐温热变形测试；
   - ADA / IBC Heel-proof 防卡鞋跟安全规范（<9.5mm）。
7. ★ A06.2 Packaging & Hardware Delivery Anatomy（包装形态与配件交付）：
   - 零售包装形态（吸塑泡壳、挂卡热缩膜、瓦楞盒）及抗摔防刮防护；
   - 随附配件清单（螺丝是否标配、防落物尼龙网兜、减震胶垫）。
8. 输出结构化【Product Specification Database（含工艺、公差与合规标准）】表格。
严格标注 7 级置信度标签。
"""
      )
      st.session_state.s1 = execute_stage(
          client, model_name, p1, "Stage 1 架构、制造工艺与规格库"
      )

      # Stage 2: 安装环境、运维与四维场景矩阵 (含新兴场景雷达) (A07 - A11.5)
      p2 = (
          a00_ctx
          + """
请执行 SOP A V1.2 的【第二阶段：环境适配与四维场景矩阵】：
1. A07 Installation: 标准安装步骤、Drop-in vs Flush-mount，对实木、LVP/SPC、瓷砖、地毯的物理干涉与热胀冷缩间隙。
2. A08 Operation: 足踩/手拨交互动作、风量微调手感与阻尼保持力。
3. A09 Maintenance & Failure Modes: 日常吸尘清理、水汽防锈、拨片卡死与百叶脱落失效模式。
4. A10 User Personas: 购买者 (Buyer)、安装者 (Installer)、使用者 (End-user) 角色诉求。
5. A11 & ★ A11.5 Application Scenario Matrix（四维场景矩阵 + 前沿场景雷达）：
   - 建立结构化矩阵：空间功能区 × 地材介质 × 踩踏负荷等级 × HVAC 冷暖工况；
   - 深度纳入新兴场景：扫地机器人越障（外框斜边倒角 <3mm、防撞坏拨片）、超薄 SPC 地板脆裂防护、极简齐平风口风潮、宠物毛发滤网。
输出结构化【Application Scenario Matrix】表格。严格标注置信度标签。
"""
      )
      st.session_state.s2 = execute_stage(
          client, model_name, p2, "Stage 2 场景矩阵与前沿场景雷达"
      )

      # Stage 3: 现场实拍证据、市场语言与用户行为 (A12 - A14)
      p3 = (
          a00_ctx
          + """
请执行 SOP A V1.2 的【第三阶段：真实证据、市场语言与用户行为】：
1. A12 Real-world Image Evidence Database: 
   - 建立结构化证据库，严格排除 3D 渲染图，整合公开可点击的买家秀/论坛讨论/工程实录；
   - 执行高频物理缺陷“双源交叉佐证法则”。
2. A13 Market Language: 建立四维【Market Language Database】映射表（Industry Term / Retail Term / Consumer Term / Search Terms）。
3. A14 User Behavior & Replacement Triggers: 
   - 购买动因与 4 大更换触发时机（地板重铺翻新、旧件生锈踏弯、安全防卡小物件、风阻噪音优化）；
   - 总结高频客诉退款（RMA）根源分析（买家开孔测量错误、边缘锋利、拨片松脱）。
"""
      )
      st.session_state.s3 = execute_stage(
          client, model_name, p3, "Stage 3 真实证据与市场语言库"
      )

      # Stage 4: 总结、企业制造落地自检与 22 核心问题闭环 (A15)
      p4 = (
          a00_ctx
          + """
请执行 SOP A V1.2 的【第四阶段：认知总装、企业落地自检与闭环验收】：
1. A15 Product Understanding Summary: 提炼产品物理本质、核心红线与不可妥协门槛。
2. ★ Enterprise Feasibility & Quality Checklist（新人制造与供应链避坑清单）：
   - 针对公司生产落地，梳理模具资产考量、良品率卡点、外箱落摔与装箱率、专利侵权排查重点。
3. 22 Core Questions Closed-Loop Checklist:
   - 逐一精确回答 22 个核心问题，形成完整闭环验证清单。
"""
      )
      st.session_state.s4 = execute_stage(
          client, model_name, p4, "Stage 4 认知总装与 22 核心问题闭环"
      )

      st.success("🎉 SOP A V1.2 工业级全流程调研圆满完成！")
    except Exception as e:
      st.error(f"调用发生错误: {e}")

if st.session_state.s1:
  t1, t2, t3, t4, t5, t_live = st.tabs([
      "📐 Stage 1: 工艺/合规/规格库",
      "🏡 Stage 2: 场景矩阵 (含新兴雷达)",
      "📸 Stage 3: 真实证据与语言库",
      "🎯 Stage 4: 闭环总结与避坑清单",
      "📄 完整报告总览与下载",
      "🌐 抓取的实时一手网页数据",
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
    full_text = (
        f"# {product_name} SOP A V1.2 工业级深度调研报告\n\n{st.session_state.s1}\n\n---\n\n{st.session_state.s2}\n\n---\n\n{st.session_state.s3}\n\n---\n\n{st.session_state.s4}"
    )
    st.download_button(
        "📥 一键下载完整 Markdown 报告",
        full_text,
        file_name=f"SOP_A_V1.2_Report_{nominal_size.replace(' ', '_')}.md",
        mime="text/markdown",
    )
  with t_live:
    st.markdown(st.session_state.live_data)
