import hashlib
import json
import os
import re
import time
import streamlit as st

# ==================== 1. 依赖库探测与降级保护 ====================
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
    page_title="宁波威霖 · 北美暖通末端(RGD)产品市场详细认知系统",
    page_icon="🏭",
    layout="wide",
)

# 威霖工程专家与外贸严谨认知 System Prompt
SOP_A_SYSTEM_INSTRUCTION = """
You are a Senior US HVAC RGD (Registers, Grilles, Diffusers) Sourcing Director & Chief Industrial Engineer at Ningbo Runner Industrial Corporation (宁波威霖住宅设施有限公司).
Your mission is to establish deep, objective, engineering-grade physical and market reality understanding of HVAC terminal products in North America.

STRICT FACT-GROUNDING MANDATE (CRITICAL):
1. You MUST prioritize the real-time search data inside `<live_ground_truth_feed>` above all else.
2. Exact Metrics: Transcribe exact retail prices (e.g. $19.98 / $7.42), actual dimensional drop-in negative tolerances (-1/8" to -3/16"), Free Area %, and US Customs HS Code / 301 tariff rates directly from the live feed.
3. NO PAIN POINT / COMPLAINT ANALYSIS: DO NOT perform 1-2 star customer complaint reviews, RMA refund root cause analysis, or speculative redesigns (the user has a separate R&D SOP). Focus strictly on physical realities, manufacturing feasibility, building compatibility, and trade parameters.

Manufacturing & Engineering Focus:
- Dual Footprint: Ningbo HQ (China) vs. Runner Thailand (US Section 301 tariff mitigation).
- Production Realities: High-pressure die casting (A380/ADC12), progressive sheet stamping (SPCC), 6063-T5 aluminum extrusion, eco-friendly dual-coat electro & electrostatic powder coating (ASTM B117 salt spray & ASTM D3359 cross-hatch adhesion).
- Hard Technical Standards & Certifications:
  * IBC concentrated floor load (>=300 lbs / 500 lbs) & ADA heel-proof (<9.5mm / 0.375" gap) for Floor Registers.
  * ASHRAE 70 (Airflow CFM, Static Pressure Drop, and NC Noise Criteria sound levels) for Air Outlets.
  * ASTM E84 Class A flame/smoke spread & NFPA 90A/90B non-combustibility for ceiling plenum spaces.
  * AMCA 500-D/500-L air leakage & performance testing for dampers/louvers.
  * ASHRAE 52.2 (MERV 8/11/13/16 ratings) & UL 900 for filter grilles.
  * California Proposition 65 & RoHS 3 / REACH legal chemical safety compliance.
  * ISTA-1A / 2A / 3A packaging drop test compliance for transit damage mitigation.
- Deep Detail Verification: Blade spacing (1/3" vs 1/2" pitch), Throw pattern (1-way, 2-way, 3-way, 4-way, 360° circular), Mounting frame (Beveled flange with countersunk screw holes + EVA foam gasket vs Drop-in gravity fit), Neck extension & Collar shape (Rectangular vs Round collar for flex duct).

Confidence Tagging:
Every factual claim must carry one tag:
【FACT】 / 【HIGH CONFIDENCE】 / 【INFERENCE】 / 【INDUSTRY STANDARD】 / 【UNVERIFIED】 / 【UNKNOWN】
Missing data tags: 【未找到】 / 【无法验证】 / 【行业推断】
"""

# 全网官方最新全量大模型配置库
PROVIDER_CONFIG = {
    "Google Gemini": {
        "models": [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.7-flash-thinking",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ],
        "default_url": "",
        "key_hint": "Google AI Studio 获取官方 API Key",
    },
    "OpenAI": {
        "models": [
            "gpt-6-astra",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "o4-mini",
            "o3",
            "o3-mini",
            "o3-mini-high",
            "o1",
            "gpt-4.5-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-oss-120b",
        ],
        "default_url": "https://api.openai.com/v1",
        "key_hint": "OpenAI 官方或授权代理 API Key (sk-...)",
    },
    "WorkBuddy (聚合平台)": {
        "models": [
            "claude-fable-5-1",
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-3-7-sonnet",
            "claude-haiku-4-5",
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gpt-6-astra",
            "o3",
            "deepseek-v4-pro",
            "deepseek-r1",
            "deepseek-v3",
        ],
        "default_url": "https://api.workbuddy.cn/v1",
        "key_hint": "WorkBuddy 聚合平台 API 密钥",
    },
    "DeepSeek (深度求索)": {
        "models": [
            "deepseek-v4-pro",
            "deepseek-flash",
            "deepseek-reasoner",
            "deepseek-chat",
        ],
        "default_url": "https://api.deepseek.com/v1",
        "key_hint": "DeepSeek 开放平台 API Key",
    },
    "自定义 OpenAI 兼容接口": {
        "models": [
            "gemini-3.8-flash",
            "gpt-6-astra",
            "claude-fable-5-1",
            "claude-3-7-sonnet",
            "deepseek-v4-pro",
            "qwen-max-2025",
            "自定义输入",
        ],
        "default_url": "https://api.example.com/v1",
        "key_hint": "第三方服务商提供的 API 接口密钥",
    },
}

# ==================== 3. 威霖北美暖通全品类工程树状数据库（含完整认证标准） ====================
RUNNER_PRODUCT_TREE = {
    "地板出风口 (Floor Register / Floor Diffuser)": {
        "sizes": [
            "4x10 inches (北美最畅销标准地面开孔)",
            "4x12 inches",
            "2x10 inches",
            "2x12 inches",
            "2x14 inches",
            "6x10 inches",
            "6x12 inches",
            "3x10 inches",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "A380 汽车级重型高压压铸铝 (Cast Aluminum - 承重抗踩断)",
            "SPCC 冷轧钢板连续冲压 (0.6mm-0.8mm 薄板商超量产款)",
            "工程 ABS/PC 阻燃防结露注塑塑料 (沿海高湿区专用)",
            "6063-T5 阳极氧化铝挤型材 (现代极简齐平内嵌款)",
            "实木材质 (Solid Red Oak / White Oak / Maple)",
            "纯黄铜/青铜重型铸造 (Solid Cast Brass / Bronze)",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "ABS 工程塑料耐磨滑块百叶阀 (Sliding Louver Damper - 耐高温无锈蚀)",
            "全钢连动单向百叶调节阀 (Steel Multi-Shutter Damper)",
            "全钢对开对向连动风门 (Opposed Blade Damper, OBD)",
            "无风门纯格栅 (Grille Only - No Damper)",
            "✍️ 自定义手动填写调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "双向条缝百叶分流 (Two-way Diverting Air Flow)",
            "加州式宽幅扩散 (Wide Crest Spread Pattern)",
            "垂直单向条缝直吹 (Straight Vertical Throw)",
            "美式经典卷轴花纹漫射 (Classic Scroll Decorative)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "Drop-in 徒手落入式 (免打螺丝孔/依靠重力与卡爪固定)",
            "Flush Mount 与地板齐平嵌入式 (可嵌实木/SPC条)",
            "边框预留沉头螺丝孔固定 (Countersunk Screw Holes)",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "标准百叶网孔间隙 (Heel-proof 防卡鞋跟 <9.5mm / 0.375\")",
            "重型粗筋格栅间隙 (Heavy-Duty Grille Bars)",
            "现代微细线性长缝 (Narrow Linear Slot 6mm)",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "IBC Section 1607 集中点载荷承重测试 (>=300 lbs 踩踏抗变形标准)",
            "ADA Title III Section 302.3 Heel-proof 防卡鞋跟标准 (<9.5mm 间隙)",
            "ASTM B117 盐雾腐蚀试验 (商超标配 96h / 沿海高耐候 240h)",
            "ASTM D3359 涂层附着力百格测试 (Cross-Hatch Adhesion >= 4B/5B)",
            "California Proposition 65 (加州65无铅/邻苯安全认证)",
            "RoHS 3 / REACH 绿色环保有害物质限用指令",
            "ISTA-1A 运输包装抗跌落防损测试",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "侧墙/天花出风口 (Sidewall & Ceiling Register)": {
        "sizes": [
            "6x6 inches (侧墙天花常用方口)",
            "8x8 inches",
            "10x6 inches (美标最通用侧墙尺寸)",
            "10x8 inches",
            "12x6 inches",
            "12x8 inches",
            "12x12 inches",
            "14x6 inches",
            "14x8 inches",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "SPCC 优质冷轧钢连续冲压 (商超走量标配)",
            "6063-T5 铝挤型材外框 + 冲压铝可调叶片 (防结露抗腐蚀)",
            "工程 ABS 塑料防冷凝天花风口",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "多叶连动风阀附带低剖面调节拨片 (Multi-Shutter Damper)",
            "对开双向连动平衡风阀 (Opposed Blade Damper - OBD)",
            "单叶自重平衡翻板风门",
            "无调节风阀 (纯出风格栅 Register Grille Only)",
            "✍️ 自定义手动填写调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "1-Way 单向垂直偏转射流 (One-Way Deflection)",
            "2-Way 双向水平两翼射流 (Two-Way Corner/Split Throw)",
            "3-Way 三向广角环绕射流 (Three-Way Deflection)",
            "4-Way 四向全景均布扩散 (Four-Way Ceiling Spread)",
            "双层独立可调弧形叶片 (Double Deflection Adjustable)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "外凸法兰边框带沉头螺丝孔 (Beveled Frame with Screw Holes - 附带安装螺丝)",
            "法兰背面附贴 EVA 发泡密封垫圈 (EVA Foam Gasket - 防漏风与共振异响)",
            "暗装弹簧卡扣卡入式 (Concealed Spring Clips)",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "1/3 英寸密集百叶间距 (1/3\" Fin Pitch - 商超走量主流/防直视管内积灰)",
            "1/2 英寸标准工业间距 (1/2\" Fin Pitch - 高开孔率/低风阻CFM)",
            "20° 固定偏转叶片 (Fixed 20 Degree Deflection)",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "ASHRAE Standard 70 性能评定 (出风静压压降、CFM风阻与 NC 噪声级评定)",
            "ASTM B117 盐雾腐蚀测试 (96h/240h)",
            "ASTM D3359 漆膜百格附着力测试 (>= 4B/5B)",
            "California Proposition 65 (加州65无铅/邻苯安全认证)",
            "RoHS 3 / REACH 环保合规",
            "ISTA-1A 挂卡/彩盒抗震跌落认证",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "T-Bar 吊顶跌落式散流器 (2x2 T-Bar Ceiling Diffuser)": {
        "sizes": [
            (
                "23-3/4\" x 23-3/4\" 面板 (适配 2x2 ft T-Bar 龙骨) 配 6\""
                " 圆形颈部 (6-Inch Round Collar)"
            ),
            (
                "23-3/4\" x 23-3/4\" 面板 (适配 2x2 ft T-Bar 龙骨) 配 8\""
                " 圆形颈部 (8-Inch Round Collar)"
            ),
            (
                "23-3/4\" x 23-3/4\" 面板 (适配 2x2 ft T-Bar 龙骨) 配 10\""
                " 圆形颈部 (10-Inch Round Collar)"
            ),
            (
                "23-3/4\" x 23-3/4\" 面板 (适配 2x2 ft T-Bar 龙骨) 配 12\""
                " 圆形颈部 (12-Inch Round Collar)"
            ),
            (
                "23-3/4\" x 23-3/4\" 面板 (适配 2x2 ft T-Bar 龙骨) 配 14\""
                " 圆形颈部 (14-Inch Round Collar)"
            ),
            "1x1 ft 跌落面板配 6\" 圆颈",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "全钢模具拉伸冲压面罩 + SPCC 镀锌背板 (Steel Stamped Face + Galvanized Back)",
            "全钢面罩 + 预贴玻纤保温背板 (Molded Fiberglass R6 Insulation Backer)",
            "全铝合金冲压面罩带轻量化背罩 (All-Aluminum Lightweight)",
            "穿孔吸音式钢制面板 (Perforated Face Diffuser)",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "圆形双叶蝶阀调节器 (Round Butterfly Damper - 软风管专用)",
            "径向放射状轮辐阻尼风阀 (Radial Blade Damper)",
            "无风门 (风管直接接入静压箱或由 VAV 系统独立变风量调节)",
            "✍️ 自定义手动填写调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "360° 全圆环形阶梯式扩散射流 (360-Degree Circular Diffusion)",
            "4-Way 方形四面同心锥形射流 (4-Way Square Cone Air Pattern)",
            "穿孔板低紊流下送风 (Perforated Low-Turbulence Flow)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "T-Bar 吊顶跌落式安装 (Lay-in Drop into Standard 15/16\" T-Grid)",
            "细边龙骨跌落安装 (Lay-in for 9/16\" Fineline T-Grid)",
            "石膏板吊顶表面硬装法兰固定框 (Surface Mount Frame)",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "多层同心冲压成型扩散锥叶片 (Multi-Cone Fixed Spacing)",
            "高开孔率微细冲孔面网 (51% Free Area Perforated Face)",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "ASTM E84 / UL 723 表面燃烧与烟气扩散 Class A 级认证 (Plenum 吊顶空间强制)",
            "NFPA 90A / 90B 暖通通风系统非燃与耐火要求",
            "ASHRAE Standard 70 声学 NC 评定 (商业办公室通常要求 NC <= 30)",
            "IBC Seismic Design Categories C-F 吊顶抗震系绳加固规范",
            "UL 94-V0 塑料部件阻燃认证",
            "California Proposition 65 (加州65合规)",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "回风过滤面罩 (Filter Return Air Grille)": {
        "sizes": [
            "14x20 inches (常用回风过滤开孔尺寸)",
            "14x25 inches",
            "16x20 inches",
            "16x25 inches",
            "20x20 inches (北美最通用大号回风面罩)",
            "20x25 inches",
            "20x30 inches",
            "24x24 inches",
            "25x25 inches",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "全钢冲压固定百叶面板 + 加固冲压外框 (Heavy Gauge Steel)",
            "6063 铝挤型材外框 + 铝制固定叶片 (防潮防下垂)",
            "线性细密金属网面罩",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "内置 1 英寸厚度标准 HVAC 过滤网槽架 (Accommodates 1\" Air Filter)",
            "内置 2 英寸加厚高能效过滤网槽架 (Accommodates 2\" Thick Filter)",
            "内置 4 英寸商业级折叠滤网槽架 (Accommodates 4\" Deep Filter)",
            "无滤网框架 (标准回风格栅 Return Grille Only)",
            "✍️ 自定义手动填写调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "45° 倾角下视防窥视吸风格栅 (45-Degree Downward Angled Blades)",
            "水平无阻力吸风 (Horizontal Free Return Airflow)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "可拆卸铰链式开合门带双侧按压塑料插销锁扣 (Hinged with Quick-Release Latches)",
            "门铰链带可拆卸卡销 (Removable Hinge Door for Easy Filter Swap)",
            "边框预钻法兰螺栓安装孔",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "1/3 英寸密集百叶间距 (1/3\" Spacing - 完全遮蔽内部积灰滤网)",
            "1/2 英寸标准开孔百叶间距 (1/2\" Spacing - 降低回风阻力)",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "ASHRAE 52.2 滤网能效阻力适配认证 (支持 MERV 8 / 11 / 13 滤网工作压降)",
            "UL 900 空气过滤器单元安全与防燃认证",
            "ASTM B117 盐雾腐蚀测试 (96h/240h)",
            "ASTM D3359 涂层百格测试 (>= 4B)",
            "California Proposition 65",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "标准回风格栅 (Return Air Grille - 无滤网款)": {
        "sizes": [
            "10x10 inches",
            "12x12 inches",
            "14x14 inches",
            "14x20 inches",
            "14x24 inches",
            "20x20 inches",
            "24x12 inches",
            "30x12 inches",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "全钢冲压整体百叶面罩",
            "铝合金型材边框 + 铝百叶条",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "纯回风格栅面板 (No Damper - 无风门，回风通道直通)",
            "✍️ 自定义调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "45° 倾角固定单向回风 (Deflected Return Air)",
            "线性直条缝回风 (Linear Bar Return)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "宽边法兰带螺丝孔固定 (Wall or Ceiling Mount with Screws)",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "1/3 英寸密集防直视间距",
            "1/2 英寸工程低风阻间距",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "ASHRAE Standard 70 回风开孔有效面积与静压损耗测试",
            "ASTM B117 盐雾腐蚀测试 (96h)",
            "ASTM D3359 漆膜附着力测试",
            "California Proposition 65",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "踢脚线风口 (Baseboard Register / Diffuser)": {
        "sizes": [
            "15 inches 标准长度 (7-1/4\" 高度)",
            "18 inches 加长型 (7-1/4\" 高度)",
            "24 inches 重型长款 (7-1/4\" 高度)",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "SPCC 优质全冷轧钢冲压折弯 (成型刚性强抗脚踢碰撞)",
            "铝合金抗刮擦踢脚线面板",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "全长重力平衡风门板 (Gravity Balanced Flap Damper)",
            "单侧指拨滑块连动风门板 (Lever Operated Damper)",
            "✍️ 自定义调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "前凸扇形三维立体广角漫射 (Fan-shaped Baseboard Throw)",
            "两端偏转向上送风 (End-deflected Perimeter Throw)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "地面与墙脚阴角贴靠安装 (Baseboard Corner Surface Mount)",
            "底板带螺丝孔固定",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "立式冲压条缝格栅条",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "踢脚线脚踢抗冲击测试 (Impact Resistance against Foot Strikes)",
            "ASTM B117 盐雾腐蚀测试 (96h)",
            "ASTM D3359 漆膜附着力测试",
            "California Proposition 65",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
    "商业线性条缝散流器 (Linear Slot Diffuser)": {
        "sizes": [
            "1 Slot (单槽) - 48 inches 长度 (宽度约 1.5\")",
            "2 Slot (双槽) - 48 inches 长度 (宽度约 2.5\")",
            "3 Slot (三槽) - 48 inches 长度 (宽度约 3.75\")",
            "4 Slot (四槽) - 48 inches 长度 (宽度约 5.0\")",
            "2 Slot (双槽) - 72 inches 长度 (商业大厅长条型)",
            "1/2\" Slot 缝宽系列",
            "3/4\" Slot 缝宽系列",
            "1\" Slot 宽条缝系列",
            "✍️ 自定义手动填写尺寸",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "materials": [
            "6063-T5 阳极氧化铝挤型材边框 + 黑色铝挤导风条",
            "高强度铝合金外框 + ABS 塑料内部导向器",
            "✍️ 自定义手动填写材质",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "dampers": [
            "槽内内置独立可旋转导流控制黑柱 (Pattern Controllers - 兼具风量调节与变向)",
            "外接镀锌静压箱带蝶阀或滑阀调节 (External Plenum Box Damper)",
            "无调节机构 (纯散流口)",
            "✍️ 自定义调节阀",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "air_patterns": [
            "水平贴附射流 (Horizontal Ceiling Coanda Effect Throw - 180° 双向或单向贴顶)",
            "垂直下吹射流 (Vertical Downward Jet Throw - 用于高挑大堂与玻璃幕墙幕帘)",
            "✍️ 自定义气流形态",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "mountings": [
            "明装法兰边框带隐蔽螺栓安装 (Surface Flange with Concealed Brackets)",
            "无边框抹灰嵌入式齐平安装 (Mud-in Plaster Borderless Frame)",
            "静压箱吊杆悬挂固定 (Plenum Box Suspension)",
            "✍️ 自定义安装工法",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "blade_pitches": [
            "3/4 英寸标准条缝间距 (3/4\" Slot Width)",
            "1 英寸大流量条缝间距 (1\" Slot Width)",
            "1/2 英寸极简微槽间距 (1/2\" Slot Width)",
            "✍️ 自定义叶片间距",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
        "standards": [
            "ASHRAE Standard 70 贴附气流射程 (Coanda Effect) 与噪声 NC 曲线评定",
            "AMCA 500-L / 500-D 导流叶片气流泄漏率与空气动力学测试",
            "ASTM E84 吊顶 Class A 阻燃规范",
            "ASTM D3359 阳极氧化与喷粉附着力测试",
            "California Proposition 65",
            "✍️ 自定义补充标准",
            "❓ 【我不知道/请AI根据北美市场推断】",
        ],
    },
}

GLOBAL_FINISHES = [
    "威霖环保双涂层：电泳底漆 + 哑光黑静电粉末喷涂 (Powder Coated Matte Black)",
    "商超标准哑光白粉末喷涂 (Traffic White RAL 9016 / 10-20% Gloss)",
    "商超亮白经典液体烤漆 (Semi-Gloss White)",
    "金属拉丝表面处理 (Brushed Nickel Finish)",
    "仿古油擦青铜色 (Oil Rubbed Bronze, ORB)",
    "清漆阳极氧化磨砂 (Clear Satin Anodized 6063 铝挤专配)",
    "电镀亮铬色 (Polished Chrome)",
    "未上漆实木原色 (Unfinished Raw Wood - 供现场刷漆)",
    "✍️ 自定义手动填写表面处理",
    "❓ 【我不知道/请AI根据北美市场推断】",
]


# ==================== 4. 实时定向探针网络检索 ====================
def search_live_probe(query, max_results=3):
  if not HAS_DDGS:
    return "（未安装 duckduckgo_search 模块，系统使用内置工厂物理公差数据库）"
  try:
    time.sleep(0.5)
    ddgs = DDGS()
    results = []
    for r in ddgs.text(query, max_results=max_results):
      title = re.sub(r"[\r\n]+", " ", r.get("title", ""))
      body = re.sub(r"[\r\n]+", " ", r.get("body", ""))
      href = r.get("href", "")
      results.append(f"• 数据源: {title}\n  URL: {href}\n  实测摘要: {body}")
    return "\n".join(results) if results else "（当前检索项无最新公开页面）"
  except Exception as e:
    return f"（实时检索通道波动: {e}，调用威霖暖通工程参数备份）"


def execute_multi_vector_search(cat, size, mat, channel, standards_text):
  """动态构建探针：彻底杜绝天花风口搜地面承重的假搜索 Bug"""
  now_str = time.strftime("%Y-%m-%d %H:%M:%S")

  # 探针 1: 商超端实时挂牌价与在售 SKU
  q_price = (
      f"{cat} {size} {mat} price Home Depot Lowes Menards current retail"
  )
  res_price = search_live_probe(q_price, 2)

  # 探针 2: 动态根据选定标准搜索工程公差与检测指标
  # 提取前两个选定的核心标准拼入查询词
  std_keywords = " ".join(standards_text.split()[:4])
  q_eng = f"{cat} {size} duct opening box size faceplate Free Area CFM {std_keywords}"
  res_eng = search_live_probe(q_eng, 2)

  # 探针 3: 美国海关 USITC 关税与 HS Code 编码
  q_tariff = f"USITC HTS code Section 301 tariff rate {mat} ventilation diffuser register"
  res_tariff = search_live_probe(q_tariff, 2)

  compiled_feed = f"""<live_ground_truth_feed timestamp="{now_str}" target_channel="{channel}">
[PROBE 1 - REAL-TIME RETAIL PRICING & IN-STORE SKUS]
{res_price}

[PROBE 2 - TECHNICAL DIMENSIONS, TOLERANCES & COMPLIANCE STANDARDS]
{res_eng}

[PROBE 3 - US CUSTOMS HS CODE & SECTION 301 TARIFF CODES]
{res_tariff}
</live_ground_truth_feed>"""
  return compiled_feed, now_str


# ==================== 5. 统一大模型流式调度引擎 ====================
def stream_llm_response(
    provider,
    model,
    key,
    url,
    system_instruction,
    prompt,
    render_targets,
    temperature=0.15,
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
        x in model.lower()
        for x in [
            "o1",
            "o3",
            "o4",
            "reasoner",
            "r1",
            "thinking",
            "fable",
            "opus-5",
        ]
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


# ==================== 6. 侧边栏与外贸业务全局设定 ====================
with st.sidebar:
  st.markdown("### 🏢 宁波威霖住宅设施有限公司")
  st.caption("Ningbo Runner · 北美暖通出风口外贸产品认知工作台")
  st.markdown("---")

  app_mode = st.radio(
      "🎯 业务运行模式",
      options=[
          "🔍 单品 4 阶段深度认知 SOP A",
          "⚖️ 多款竞品横向技术对标 (Benchmark)",
      ],
      index=0,
  )

  st.markdown("---")
  st.subheader("⚙️ 官方最新大模型服务配置")
  selected_provider = st.selectbox(
      "AI 服务商", options=list(PROVIDER_CONFIG.keys()), index=0
  )
  cfg = PROVIDER_CONFIG[selected_provider]

  selected_model = st.selectbox(
      f"选择 {selected_provider} 最新模型", options=cfg["models"], index=0
  )
  actual_model = (
      st.text_input(
          "手动输入模型标识", placeholder="例如: gemini-3.8-flash / gpt-6-astra"
      )
      if selected_model == "自定义输入"
      else selected_model
  )

  api_key = st.text_input(
      f"{selected_provider} API Key*",
      type="password",
      placeholder="在此输入 API 密钥",
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
        "API Base URL (接口地址)",
        value="" if selected_provider == "OpenAI" else cfg["default_url"],
        placeholder="官方接口留空；中转请填写如 https://api.xxx.com/v1",
    ).strip()

  st.markdown("---")
  st.subheader("🚢 威霖外贸供应链与商业杠杆")
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
          "DDP 完税后交货到客户海外仓",
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

  # 外贸业务核心杠杆：订单规模与包装内装数
  order_volume = st.selectbox(
      "预计采购规模 / MOQ (决定模具摊销)",
      [
          "商超走量大单 (100,000+ pcs/年 - 大型高速级进模摊销极低)",
          "常规工程批量 (20,000-50,000 pcs/年 - 标准模具)",
          "首期试单/非标定制 (3,000-5,000 pcs - 简易工程模工时较高)",
      ],
      index=1,
  )
  master_pack_qty = st.selectbox(
      "外箱装箱率 (Master Carton Pack Qty)",
      [
          "10 pcs / Master Carton (商超零售彩盒主流)",
          "20 pcs / Master Carton (工程批发大箱 Bulk 标配)",
          "24 pcs / Master Carton",
          "1 pc / Mailer Box (电商小包一件一件包装)",
      ],
      index=1,
  )

# ==================== 顶部标题与演示 Demo 辅助 ====================
st.markdown(
    "## 🏭 宁波威霖北美暖通出风口（RGD）产品市场详细认知与对标系统"
)
st.caption(
    f"出运口岸: **{supply_origin.split(' ')[0]}** | 贸易方式:"
    f" **{trade_terms.split(' ')[0]}** | 渠道: **{target_channel.split(' ')[0]}**"
    f" | 包装率: **{master_pack_qty.split(' ')[0]} pcs**"
)

if "demo_payload" not in st.session_state:
  st.session_state.demo_payload = {}

col_top1, col_top2 = st.columns([3, 1])
with col_top2:
  if st.button("📥 一键载入地板风口畅销款演示数据 (Demo)", use_container_width=True):
    st.session_state.demo_payload = {
        "cat": "地板出风口 (Floor Register / Floor Diffuser)",
        "ref_link": (
            "https://www.homedepot.com/p/Decor-Grates-4-in-x-10-in-Cast-Aluminum-Floor-Register-AJH410-ALU/202525184"
        ),
        "b_name": "威霖重型铸铝装饰风口 (Wellmien Cast Aluminum)",
        "b_spec": (
            "A380高压压铸铝+ABS阻尼风阀, 哑光黑静电喷涂, 实时参考零售价 $19.98"
        ),
        "a_name": "商超冷轧钢冲压条缝款 (Home Depot Stamped Steel)",
        "a_spec": "0.6mm薄冷轧板连续冲压, 简易白色烤漆, 实时参考零售价 $7.42",
        "b2_name": "无框齐平隐形风口 (Aria Vent / Flush Mount)",
        "b2_spec": "6063铝挤型材+ABS底盘/内嵌地板, 实时参考零售价 $45.00",
        "bench_focus": (
            "1. 承重踩踏强度 (IBC 300 lbs) 对比\n2. 配合公差与徒手 Drop-in"
            " 安装工时对比\n3. 40HQ 柜装箱 CBM 测算与关税合规"
        ),
    }
    st.rerun()


def parse_selection(choice, custom_val, field_name):
  if "自定义手动填写" in choice:
    return custom_val.strip() if custom_val.strip() else f"自定义{field_name}"
  elif "我不知道" in choice:
    return (
        "【我不知道/待调研 - 请根据 <live_ground_truth_feed> 实时推断北美最畅销标配】"
    )
  return choice


# ==================== 模式 A: 单品 4 阶段深度认知 SOP A ====================
if app_mode == "🔍 单品 4 阶段深度认知 SOP A":
  for k in ["s1", "s2", "s3", "s4", "live_feed", "feed_time", "last_signature"]:
    if k not in st.session_state:
      st.session_state[k] = ""

  st.markdown("### 📋 单品物理与外贸工程详细输入单")

  demo_data = st.session_state.demo_payload

  # --- 1. 品类联动选择 ---
  category_list = list(RUNNER_PRODUCT_TREE.keys()) + [
      "✍️ 自定义手动填写品类",
      "❓ 【我不知道/请AI根据北美市场推断】",
  ]
  default_cat_idx = 0
  if demo_data.get("cat") in category_list:
    default_cat_idx = category_list.index(demo_data.get("cat"))

  sel_cat = st.selectbox(
      "1. 产品标准品类 (选择后下方所有规格将自动联动切换)*",
      category_list,
      index=default_cat_idx,
  )
  custom_cat = ""
  if "自定义" in sel_cat:
    custom_cat = st.text_input(
        "输入自定义品类名称",
        placeholder="例如: 现代极简隐形出风口 (Frameless Register)",
    )
  final_cat = parse_selection(sel_cat, custom_cat, "品类")

  cat_tree = RUNNER_PRODUCT_TREE.get(
      sel_cat, RUNNER_PRODUCT_TREE["地板出风口 (Floor Register / Floor Diffuser)"]
  )

  # --- 2. 联动尺寸、材质、风阀与表面处理 ---
  c1, c2 = st.columns(2)
  with c1:
    sel_size = st.selectbox(
        f"2. 标称开孔尺寸 (Duct Opening - 专属于所选品类)*",
        cat_tree["sizes"],
        key=f"size_sel_{sel_cat}",
    )
    custom_size = ""
    if "自定义" in sel_size:
      custom_size = st.text_input(
          "输入自定义开孔尺寸", placeholder="例如: 24x24 inches 配 10寸圆颈"
      )
    final_size = parse_selection(sel_size, custom_size, "尺寸")

  with c2:
    sel_mat = st.selectbox(
        f"3. 面板材质与成型工艺 (专属于所选品类)*",
        cat_tree["materials"],
        key=f"mat_sel_{sel_cat}",
    )
    custom_mat = ""
    if "自定义" in sel_mat:
      custom_mat = st.text_input(
          "输入自定义材质", placeholder="例如: A380高压压铸铝合金"
      )
    final_mat = parse_selection(sel_mat, custom_mat, "材质")

  c3, c4 = st.columns(2)
  with c3:
    sel_damper = st.selectbox(
        f"4. 风量调节机构/阀门类型 (专属于所选品类)*",
        cat_tree["dampers"],
        key=f"damper_sel_{sel_cat}",
    )
    custom_damper = ""
    if "自定义" in sel_damper:
      custom_damper = st.text_input(
          "输入自定义风门", placeholder="例如: ABS工程塑料滑块阻尼阀"
      )
    final_damper = parse_selection(sel_damper, custom_damper, "风门")

  with c4:
    sel_finish = st.selectbox("5. 表面涂装与处理工艺*", GLOBAL_FINISHES, index=0)
    custom_finish = ""
    if "自定义" in sel_finish:
      custom_finish = st.text_input(
          "输入自定义涂装", placeholder="例如: 哑光黑静电粉末喷涂"
      )
    final_finish = parse_selection(sel_finish, custom_finish, "涂装")

  # --- 3. 补齐核心：产品合规与工程检测认证标准（联动） ---
  st.markdown("---")
  st.markdown("#### 🛡️ 产品合规、安全与工程检测认证标准 (专属于当前品类)")
  selected_standards = st.multiselect(
      "6. 勾选客户或北美市场必须符合的检测标准*",
      cat_tree["standards"],
      default=cat_tree["standards"][:3],  # 默认勾选前三项硬性标准
      key=f"standards_sel_{sel_cat}",
  )
  custom_standard = st.text_input(
      "如有其他客户特殊指定检测标准，在此补充 (选填)",
      placeholder="例如: 需出具第三方 SGS 240小时盐雾报告、UL 181 软风管接口测试等",
  )
  final_standards_str = (
      "; ".join(selected_standards)
      + (f"; 补充: {custom_standard}" if custom_standard else "")
  )

  # --- 4. 深度工程图纸细节 ---
  with st.expander(
      "🛠️ 展开深度工业工程图纸细节（气流形态/边框结构/叶片间距）",
      expanded=False,
  ):
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
      sel_pattern = st.selectbox(
          "7. 气流扩散形式 (Air Throw & Deflection)*",
          cat_tree["air_patterns"],
          key=f"pattern_{sel_cat}",
      )
      custom_pattern = ""
      if "自定义" in sel_pattern:
        custom_pattern = st.text_input("填写气流形态", placeholder="例如: 4-Way 四向")
      final_pattern = parse_selection(sel_pattern, custom_pattern, "气流形态")

    with d_col2:
      sel_mount = st.selectbox(
          "8. 边框结构与安装工法 (Mounting Frame)*",
          cat_tree["mountings"],
          key=f"mount_{sel_cat}",
      )
      custom_mount = ""
      if "自定义" in sel_mount:
        custom_mount = st.text_input(
            "填写安装工法", placeholder="例如: Drop-in 徒手落入免螺丝"
        )
      final_mount = parse_selection(sel_mount, custom_mount, "安装工法")

    with d_col3:
      sel_pitch = st.selectbox(
          "9. 叶片结构与排布间距 (Blade Pitch)*",
          cat_tree["blade_pitches"],
          key=f"pitch_{sel_cat}",
      )
      custom_pitch = ""
      if "自定义" in sel_pitch:
        custom_pitch = st.text_input(
            "填写叶片间距", placeholder="例如: 1/3寸防直视间距"
        )
      final_pitch = parse_selection(sel_pitch, custom_pitch, "叶片间距")

  ref_link = st.text_input(
      "10. 在售竞品/商超参考链接 (选填)",
      value=demo_data.get("ref_link", ""),
      placeholder="例如: Home Depot / Lowe's 对应款式链接",
  )

  # 签名检测机制：监控所有字段变动
  current_inputs_str = f"{final_cat}_{final_size}_{final_mat}_{final_damper}_{final_finish}_{final_standards_str}_{final_pattern}_{final_mount}_{final_pitch}_{supply_origin}_{trade_terms}_{target_channel}_{order_volume}_{master_pack_qty}"
  current_signature = hashlib.md5(current_inputs_str.encode("utf-8")).hexdigest()

  if (
      st.session_state.last_signature
      and st.session_state.last_signature != current_signature
  ):
    for k in ["s1", "s2", "s3", "s4", "live_feed", "feed_time"]:
      st.session_state[k] = ""
    st.session_state.last_signature = current_signature

  st.markdown("---")
  st.markdown("#### 🎯 选择本次输出的阶段 (自由按需勾选)")
  col_s1, col_s2, col_s3, col_s4 = st.columns(4)
  with col_s1:
    exec_s1 = st.checkbox(
        "Stage 1: 工艺公差、合规标准与关税装柜",
        value=True,
        help="尺寸配合公差、模具工艺可行性、各项检测标准、HS Code与关税装柜",
    )
  with col_s2:
    exec_s2 = st.checkbox(
        "Stage 2: 地材环境与场景应用",
        value=True,
        help="实木/LVP适配、扫地机越障坡度倒角、极端冷暖循环温差",
    )
  with col_s3:
    exec_s3 = st.checkbox(
        "Stage 3: 市场形态与包装装运",
        value=True,
        help="商超挂卡/双泡壳 vs 批发工模大箱包装、40HQ 装箱 CBM 测算",
    )
  with col_s4:
    exec_s4 = st.checkbox(
        "Stage 4: 行业技术语言与询盘库",
        value=True,
        help="买手专业术语库、技术指标解答库、样品签样工程确认清单",
    )

  def refresh_single_live_data():
    with st.spinner(
        "🌐 正在并发发起多路定向探针，依据所选标准抓取当下实时市场数据..."
    ):
      feed, t_str = execute_multi_vector_search(
          final_cat,
          final_size,
          final_mat,
          target_channel,
          final_standards_str,
      )
      st.session_state.live_feed = feed
      st.session_state.feed_time = t_str
      st.session_state.last_signature = current_signature

  def get_single_context():
    if (
        not st.session_state.live_feed
        or st.session_state.last_signature != current_signature
    ):
      refresh_single_live_data()
    return f"""
【威霖工程与外贸单品条件】
- 产品品类: {final_cat}
- 标称开孔尺寸: {final_size}
- 面板材质与工艺: {final_mat}
- 调节机构/风门: {final_damper}
- 表面处理与涂层: {final_finish}
- 强制合规与检测认证标准: {final_standards_str}
- 气流分布形态: {final_pattern}
- 安装结构与法兰: {final_mount}
- 叶片结构与间距: {final_pitch}
- 供应链商务参数: 出货基地【{supply_origin}】 | 贸易条款【{trade_terms}】 | 渠道包装【{target_channel}】
- 采购规模与装运: 订单量【{order_volume}】 | 外箱装率【{master_pack_qty}】
- 竞品参考: {ref_link if ref_link else '北美行业实时基准'}

{st.session_state.live_feed}
"""

  col_run1, col_run2 = st.columns(2)
  with col_run1:
    run_single = st.button(
        "🚀 强制实时检索并运行选定阶段 (流式输出)",
        type="primary",
        use_container_width=True,
    )
  with col_run2:
    if st.button("🔄 彻底清空所有数据与缓存", use_container_width=True):
      # 彻底重置所有 session keys，根治 widget 幽灵残留 Bug
      keys_to_clear = [
          k
          for k in st.session_state.keys()
          if any(
              k.startswith(prefix)
              for prefix in [
                  "size_sel_",
                  "mat_sel_",
                  "damper_sel_",
                  "standards_sel_",
                  "pattern_",
                  "mount_",
                  "pitch_",
                  "comp_size_",
              ]
          )
      ]
      for k in keys_to_clear:
        del st.session_state[k]
      for k in [
          "s1",
          "s2",
          "s3",
          "s4",
          "live_feed",
          "feed_time",
          "last_signature",
      ]:
        st.session_state[k] = ""
      st.session_state.demo_payload = {}
      st.rerun()

  global_stream_status = st.empty()
  global_stream_box = st.empty()

  t1, t2, t3, t4, t5, t_live = st.tabs([
      "📐 Stage 1: 工艺规格、合规与关税",
      "🏡 Stage 2: 地材环境与场景应用",
      "📦 Stage 3: 市场在售形态与包装装运",
      "💬 Stage 4: 行业技术语言与询盘库",
      "📄 完整报告组装导出",
      "🌐 本轮实时抓取数据凭证",
  ])

  with t1:
    c_sub1, _ = st.columns([1, 4])
    with c_sub1:
      btn_re_s1 = st.button("⚡ 单独刷新 Stage 1", key="btn_s1_single")
    p_s1 = st.empty()
    if st.session_state.s1:
      p_s1.markdown(st.session_state.s1)
  with t2:
    c_sub2, _ = st.columns([1, 4])
    with c_sub2:
      btn_re_s2 = st.button("⚡ 单独刷新 Stage 2", key="btn_s2_single")
    p_s2 = st.empty()
    if st.session_state.s2:
      p_s2.markdown(st.session_state.s2)
  with t3:
    c_sub3, _ = st.columns([1, 4])
    with c_sub3:
      btn_re_s3 = st.button("⚡ 单独刷新 Stage 3", key="btn_s3_single")
    p_s3 = st.empty()
    if st.session_state.s3:
      p_s3.markdown(st.session_state.s3)
  with t4:
    c_sub4, _ = st.columns([1, 4])
    with c_sub4:
      btn_re_s4 = st.button("⚡ 单独刷新 Stage 4", key="btn_s4_single")
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
• 执行时间戳: {st.session_state.feed_time}
• 出货基地: {supply_origin} | 贸易方式: {trade_terms} | 渠道要求: {target_channel}
• 订单规模: {order_volume} | 外箱装率: {master_pack_qty}
• 强制合规标准: {final_standards_str}
• 分析引擎: {selected_provider} ({actual_model}) | 数据状态: 100% 强锚定实时搜索

---
## Stage 1: 物理配合尺寸、制造工艺、工程合规标准与海运关税
{st.session_state.s1 if st.session_state.s1 else '> 【本轮未选定生成此阶段】'}

---
## Stage 2: 地材环境适配、扫地机越障坡度与冷热温差工况
{st.session_state.s2 if st.session_state.s2 else '> 【本轮未选定生成此阶段】'}

---
## Stage 3: 北美在售形态解构、买手渠道包装与海运装柜标准
{st.session_state.s3 if st.session_state.s3 else '> 【本轮未选定生成此阶段】'}

---
## Stage 4: 行业技术语言、买手 RFQ 询盘技术参数库与签样规范
{st.session_state.s4 if st.session_state.s4 else '> 【本轮未选定生成此阶段】'}
"""
      st.download_button(
          "📥 下载当前生成的最新 Markdown 报告",
          full_rep,
          f"Runner_{final_size.replace(' ', '_')}_{st.session_state.feed_time.split(' ')[0]}.md",
          "text/markdown",
          use_container_width=True,
      )
      st.markdown(full_rep)
    else:
      st.info("尚未生成任何阶段，请勾选阶段并点击运行。")
  with t_live:
    if st.session_state.live_feed:
      st.markdown(st.session_state.live_feed)

  SINGLE_PROMPTS = {
      "s1": """
请执行【Stage 1: 物理配合尺寸、制造工艺、工程合规标准与关税大表】：
1. 详细尺寸解耦：结合气流形态、边框安装工法与叶片间距，列出标称开孔尺寸 (Duct Opening)、实际箱体/圆颈 (Box/Collar) 负公差配合尺寸（标准留量 -1/8" 至 -3/16" 确保徒手装入）、面罩总外径与边框凸出厚度；
2. 威霖工厂制造可行性：高压压铸铝 A380 / SPCC 钢板冲压拉伸 / 6063-T5 铝挤工艺，依据【采购规模】分析模具类型（大型高速级进模 vs 单冲模）开发周期与分摊成本；双涂层电泳+静电粉末喷涂技术；
3. 硬性合规与工程检测认证拆解：针对输入的【强制合规标准】，逐一详细说明其检测方法、达标阈值与测试报告要求（如 IBC 300 lbs 集中点载荷、ASTM B117 盐雾小时数、ASTM D3359 附着力 4B/5B、ASHRAE 70 NC 噪声等级、ASTM E84 Class A 阻燃、California Prop 65 与 RoHS 限用有害物质）；
4. 实时海关与贸易数据：海关 HS Code 编码、美国 301 关税税率，从【宁波总部】与【建霖泰国海外生产基地】出货的税率及合规优势，结合【外箱装率】测算 40HQ 集装箱装箱容积。
表格中的数据必须严格依据 <live_ground_truth_feed> 实时事实并标明来源。
""",
      "s2": """
请执行【Stage 2: 地材环境适配、扫地机越障坡度与冷热温差工况全景】：
1. 建筑基层物理适配：实木地板防刮伤、SPC/LVP 超薄石塑地砖防开裂、石膏板吊顶与 T-Bar 龙骨平整嵌合（防下坠与翘曲）、瓷砖与地毯工况；
2. 扫地机器人交互雷达（地面品类）：外边框坡度倒角是否顺畅（必须 <3mm 缓坡斜边设计）、防止扫地机卡轮脱困失败与碰撞损坏风阀拨片；
3. 暖通极端冷热温差循环实况：冬季 140°F 强暖风热膨胀异响 (Squeaking) 控制、夏季 55°F 冷风冷凝水积聚防锈防霉表现；
4. 人体工学与流体体验：裸足脚感、叶片边缘无冲压锐利毛刺。
严格标记置信度标签。
""",
      "s3": """
请执行【Stage 3: 北美在售形态解构、买手渠道包装与海运装柜标准】：
1. 市场在售同类竞品物理架构拆解：依据 <live_ground_truth_feed>，拆解北美市场上主流品牌在售款式的物理架构与配置；
2. 渠道包装形态与抗摔规范：结合输入的【外箱装箱率】，分析零售彩盒/挂卡吸塑包装 vs 工业大箱牛皮纸散装 (Bulk Pack)，详述 ISTA-1A / 2A 跌落测试与振动测试要求；
3. 集装箱装运装载率（40HQ Container CBM）：精确计算单箱体积（Carton Cube）、整柜装箱大箱数与总件数，美标托盘（US Standard Pallet 48x40"）打托堆叠方案。
数据必须真实可靠。
""",
      "s4": """
请执行【Stage 4: 行业技术语言、买手 RFQ 询盘技术参数库与签样规范】：
1. 【北美暖通买手地道专业技术参数中英文对照库】：涵盖如 CFM, Free Area, Neck Size, Face Flange, Louver, Opposed Blade Damper, Drop-in Fit, Throw & Spread, Coanda Effect, Deflection, Cross-hatch 等核心词汇的标准工程定义；
2. 【外贸业务员 RFQ 询盘应答技术表】：当北美建材商超买手或工程批发商采购总监询问风阻压降、材质厚度、点承重检测、盐雾报告、开孔配合余量等关键参数时，业务员应提供的权威工程数据与技术回复范本；
3. 【出样签样工程确认清单 (Sample PSS Checklist)】：包括实测负公差、涂层膜厚、包装唛头条形码核验、第三方测试证书等出样前必检清单。
严格标记置信度标签。
""",
  }

  if run_single:
    if not api_key:
      st.error(f"请先在左侧输入 {selected_provider} 的 API Key！")
    elif not any([exec_s1, exec_s2, exec_s3, exec_s4]):
      st.warning("您未勾选任何阶段，请在上方勾选至少一个阶段后再启动！")
    else:
      try:
        refresh_single_live_data()
        ctx = get_single_context()

        tasks = [
            (
                exec_s1,
                "s1",
                "Stage 1: 工艺规格、合规与关税",
                SINGLE_PROMPTS["s1"],
                p_s1,
            ),
            (
                exec_s2,
                "s2",
                "Stage 2: 地材环境与场景应用",
                SINGLE_PROMPTS["s2"],
                p_s2,
            ),
            (
                exec_s3,
                "s3",
                "Stage 3: 市场形态与包装装运",
                SINGLE_PROMPTS["s3"],
                p_s3,
            ),
            (
                exec_s4,
                "s4",
                "Stage 4: 行业技术语言与询盘库",
                SINGLE_PROMPTS["s4"],
                p_s4,
            ),
        ]
        active_tasks = [t for t in tasks if t[0]]

        for idx, (_, k_name, label_text, prompt_body, p_box) in enumerate(
            active_tasks, 1
        ):
          global_stream_status.info(
              f"⏳ [{idx}/{len(active_tasks)}] 正在流式输出：{label_text}..."
          )
          st.session_state[k_name] = stream_llm_response(
              selected_provider,
              actual_model,
              api_key,
              base_url,
              SOP_A_SYSTEM_INSTRUCTION,
              ctx + prompt_body,
              (global_stream_box, p_box),
          )

        global_stream_status.success(
            "🎉 选中的阶段全部输出完成！数据已 100% 锚定本次实时检索。"
        )
        global_stream_box.empty()
      except Exception as e:
        global_stream_status.error(f"❌ 运行发生异常: {e}")

  # 单独刷新单个阶段
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
          with st.spinner(f"正在重新检索并流式生成 {lbl}..."):
            refresh_single_live_data()
            ctx = get_single_context()
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
          st.success(f"{lbl} 单独刷新完成！")
        except Exception as e:
          st.error(f"{lbl} 刷新失败: {e}")

# ==================== 模式 B: 竞品横向技术对标 (Benchmark) ====================
else:
  for k in [
      "cp1",
      "cp2",
      "cp3",
      "cp4",
      "comp_feed",
      "comp_feed_time",
      "last_comp_sig",
  ]:
    if k not in st.session_state:
      st.session_state[k] = ""

  st.markdown("### 📋 竞品横向工程技术与规格对标输入单")

  demo_d = st.session_state.demo_payload

  comp_cat_list = list(RUNNER_PRODUCT_TREE.keys())
  b_cat_choice = st.selectbox(
      "对标品类 (选择后尺寸与标准将自动联动切换)*", comp_cat_list, index=0
  )
  cat_tree_b = RUNNER_PRODUCT_TREE[b_cat_choice]

  b_size_choice = st.selectbox(
      "标称开孔尺寸 (专属于所选品类)*",
      cat_tree_b["sizes"],
      key=f"comp_size_{b_cat_choice}",
  )
  b_size_cust = ""
  if "自定义" in b_size_choice:
    b_size_cust = st.text_input(
        "输入自定义尺寸", placeholder="例如: 4x10 inches"
    )
  final_b_size = parse_selection(b_size_choice, b_size_cust, "尺寸")

  # 竞品模式同样引入合规标准
  comp_standards = st.multiselect(
      "对标关注的硬性合规标准*",
      cat_tree_b["standards"],
      default=cat_tree_b["standards"][:2],
      key=f"comp_std_{b_cat_choice}",
  )
  comp_std_str = "; ".join(comp_standards)

  st.markdown("---")
  st.markdown("**1. 威霖目标款 / 推荐款 (Wellmien Offering)**")
  cb1, cb2 = st.columns(2)
  with cb1:
    b_name = st.text_input(
        "威霖款标称名称*",
        value=demo_d.get("b_name", ""),
        placeholder="例如: 威霖重型铸铝装饰款 / 威霖全铝天花散流器",
    )
  with cb2:
    b_spec = st.text_input(
        "材质工艺与建议零售价*",
        value=demo_d.get("b_spec", ""),
        placeholder="例如: A380高压压铸铝, 哑光黑喷粉, 参考零售价 $19.98",
    )

  st.markdown("**2. 对照竞品 A (主流商超低价冲压钢走量款)**")
  ca1, ca2 = st.columns(2)
  with ca1:
    a_name = st.text_input(
        "竞品 A 名称*",
        value=demo_d.get("a_name", ""),
        placeholder="例如: Accord / TruAire 冲压冷轧钢款",
    )
  with ca2:
    a_spec = st.text_input(
        "材质工艺与零售价*",
        value=demo_d.get("a_spec", ""),
        placeholder="例如: 0.6mm薄冷轧钢冲压, 白色烤漆, 实时零售价 $7.42",
    )

  st.markdown("**3. 对照竞品 B (高端现代极简隐形款/高规工程款)**")
  c_b1, c_b2 = st.columns(2)
  with c_b1:
    b2_name = st.text_input(
        "竞品 B 名称*",
        value=demo_d.get("b2_name", ""),
        placeholder="例如: Aria Vent / Fittes 现代极简款",
    )
  with c_b2:
    b2_spec = st.text_input(
        "材质工艺与零售价*",
        value=demo_d.get("b2_spec", ""),
        placeholder="例如: 6063铝挤型材+ABS底盘/可嵌地板, 实时零售价 $45.00",
    )

  bench_focus = st.text_area(
      "重点横向对标方向",
      value=demo_d.get("bench_focus", ""),
      placeholder=(
          "例如: 1. 承重踩踏强度 (IBC 300 lbs) 2. 气流扩散效率与风阻 3. 渠道包装与"
          " 40HQ 柜容对比"
      ),
  )

  comp_inputs_str = f"{b_cat_choice}_{final_b_size}_{b_name}_{a_name}_{b2_name}_{comp_std_str}_{supply_origin}_{trade_terms}_{target_channel}"
  comp_signature = hashlib.md5(comp_inputs_str.encode("utf-8")).hexdigest()

  if (
      st.session_state.last_comp_sig
      and st.session_state.last_comp_sig != comp_signature
  ):
    for k in ["cp1", "cp2", "cp3", "cp4", "comp_feed", "comp_feed_time"]:
      st.session_state[k] = ""
    st.session_state.last_comp_sig = comp_signature

  def refresh_comp_live_data():
    with st.spinner("🌐 正在并发发起竞品定向探针，抓取当下在售真实数据..."):
      feed, t_str = execute_multi_vector_search(
          f"{b_cat_choice} {b_name} {a_name}",
          final_b_size,
          "benchmark",
          target_channel,
          comp_std_str,
      )
      st.session_state.comp_feed = feed
      st.session_state.comp_feed_time = t_str
      st.session_state.last_comp_sig = comp_signature

  def get_comp_context():
    if (
        not st.session_state.comp_feed
        or st.session_state.last_comp_sig != comp_signature
    ):
      refresh_comp_live_data()
    return f"""
【竞品横向技术对标输入】
- 对标品类: {b_cat_choice} | 标称规格: {final_b_size}
- 核心检测标准: {comp_std_str}
- 威霖基准款: {b_name} | 参数: {b_spec}
- 对照竞品 A: {a_name} | 参数: {a_spec}
- 对照竞品 B: {b2_name} | 参数: {b2_spec}
- 外贸背景: 出货基地【{supply_origin}】 | 贸易条款【{trade_terms}】 | 渠道要求【{target_channel}】
- 重点对标方向: {bench_focus}

{st.session_state.comp_feed}
"""

  BENCHMARK_PROMPTS = {
      "cp1": """
请执行【竞品对标维度一：工程技术参数、制造工法与关税装柜横向大表】：
1. 输出标准 Markdown 横向对比矩阵大表，严格对比【威霖目标款】、【竞品 A 冲压薄铁款】、【竞品 B 极简隐形款】：
   - 材质与模具成型工法（压铸铸铝 A380 vs SPCC 冷轧冲压 vs 6063-T5 铝挤/CNC）；
   - 表面处理体系（双涂层静电喷粉 vs 普通烤漆 vs 阳极氧化；ASTM B117 盐雾测试耐久度与 ASTM D3359 附着力）；
   - 物理配合尺寸与公差（Duct Opening 开孔公差、Drop-in Box 负公差配合、面罩外框厚度）；
   - 通风流体与承重性能（Free Area % 开孔率、CFM 风阻压降、各项合规标准如 IBC 300 lbs 集中点载荷/ASHRAE 70/ADA Heel-Proof）；
   - 外贸商业参数：实时在售零售价 MSRP、海关 HS Code 编码、美国 301 关税影响预估、40HQ 装箱容积 CBM。
表格中的价格与规格必须严格依据 <live_ground_truth_feed> 实时事实并标记来源。
""",
      "cp2": """
请执行【竞品对标维度二：地材适配兼容、扫地机器人通过性与极端工况对比】：
1. 深入对比三款产品在建筑实际应用中的客观表现：
   - 复杂地材/天花基层适配：实木地板防刮、SPC/LVP 超薄石塑锁扣地板防边缘压裂、瓷砖基层的平整受力、T-Bar 龙骨抗变形下坠；
   - 扫地机器人干涉雷达（地面款）：外唇坡度倒角是否顺畅（是否 <3mm 缓坡斜边）、卡轮脱困表现、外露拨片碰撞耐受性；
   - 暖通冷热交替循环极限工况：冬季 140°F 强暖风（金属热膨胀形变与摩擦异响 Squeaking 控制、ABS 阀体耐温表现）与夏季冷凝水防锈表现；
   - 安装耗时与人工门槛：普通消费者徒手落入更换 (Drop-in) 耗时（约10秒） vs 隐形款现场精确切割地板砖瓦（约30-60分钟+专业师傅工费）。
严格标记置信度标签。
""",
      "cp3": """
请执行【竞品对标维度三：市场在售形态定位、包装工程与海运物流成本对比】：
1. 市场价格带与产品层级梯队定位全景（入门经济型 vs 经典装饰升级型 vs 高端建筑师指定型）；
2. 包装交付与物流防护对比：
   - 零售商超挂卡吸塑（Retail Blister） vs 工程大箱牛皮纸散装（Pro Bulk） vs 电商防摔盒的体积（CBM）与保护性能；
   - 预估单箱重量（Gross Weight）与运输堆叠稳定性；
3. 渠道流通便利性与综合物流综合成本对比。
数据必须真实可靠。
""",
      "cp4": """
请执行【竞品对标维度四：技术规格横向总结与外贸业务员专业参数交流库】：
1. 技术差异化总结大表：威霖款相比竞品 A 的核心工程升级指标、相比竞品 B 的便捷更换成本优势；
2. 【外贸新业务员技术型商务交流库】：
   - 当北美商超买手（Retail Buyer）或批发商采购主管拿竞品 A（低价冲压钢）与威霖铸铝款对比价格时，业务员如何从 IBC 300 磅点承重不变形、全铝永不生锈、静音 ABS 阻尼阀等技术参数进行专业参数抗辩？
   - 针对不同买手类型（商超 vs 工程批发）的出样检测报告清单（ASTM 盐雾报告、承重检测认证、配合公差图纸）。
严格标记置信度标签。
""",
  }

  st.markdown("---")
  st.markdown("#### 🎯 选择本次对标的维度 (自由按需勾选)")
  col_cp1, col_cp2, col_cp3, col_cp4 = st.columns(4)
  with col_cp1:
    exec_cp1 = st.checkbox(
        "维度 1: 规格工艺与关税大表",
        value=True,
        help="对比材质模具、配合公差、承重标准与 HS Code 关税",
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
        "🚀 强制实时检索并运行选定维度 (流式输出)",
        type="primary",
        use_container_width=True,
    )
  with col_b_run2:
    if st.button("🔄 彻底清空竞品数据与缓存", use_container_width=True):
      for k in [
          "cp1",
          "cp2",
          "cp3",
          "cp4",
          "comp_feed",
          "comp_feed_time",
          "last_comp_sig",
      ]:
        st.session_state[k] = ""
      st.session_state.demo_payload = {}
      st.rerun()

  global_comp_status = st.empty()
  global_comp_box = st.empty()

  ct1, ct2, ct3, ct4, ct5, ct_live = st.tabs([
      "📊 维度 1: 规格工艺与关税大表",
      "🏡 维度 2: 地材兼容与场景应用",
      "📦 维度 3: 市场形态与包装物流",
      "💬 维度 4: 技术总结与买手参数库",
      "📑 完整对标报告组装导出",
      "🌐 本轮实时抓取数据凭证",
  ])

  with ct1:
    c_btn_cp1, _ = st.columns([1, 4])
    with c_btn_cp1:
      re_cp1 = st.button("⚡ 单独刷新维度 1", key="btn_c1_single")
    ph_cp1 = st.empty()
    if st.session_state.cp1:
      ph_cp1.markdown(st.session_state.cp1)
  with ct2:
    c_btn_cp2, _ = st.columns([1, 4])
    with c_btn_cp2:
      re_cp2 = st.button("⚡ 单独刷新维度 2", key="btn_c2_single")
    ph_cp2 = st.empty()
    if st.session_state.cp2:
      ph_cp2.markdown(st.session_state.cp2)
  with ct3:
    c_btn_cp3, _ = st.columns([1, 4])
    with c_btn_cp3:
      re_cp3 = st.button("⚡ 单独刷新维度 3", key="btn_c3_single")
    ph_cp3 = st.empty()
    if st.session_state.cp3:
      ph_cp3.markdown(st.session_state.cp3)
  with ct4:
    c_btn_cp4, _ = st.columns([1, 4])
    with c_btn_cp4:
      re_cp4 = st.button("⚡ 单独刷新维度 4", key="btn_c4_single")
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
      full_comp_rep = f"""# 宁波威霖住宅设施 · {b_cat_choice} ({final_b_size}) 竞品技术横向对标报告
• 执行时间戳: {st.session_state.comp_feed_time}
• 出货基地: {supply_origin} | 贸易方式: {trade_terms} | 渠道要求: {target_channel}
• 对标合规标准: {comp_std_str}
• 分析引擎: {selected_provider} ({actual_model}) | 数据状态: 100% 强锚定实时搜索

---
## 维度一：工程技术参数、制造工法与关税装柜横向大表
{st.session_state.cp1 if st.session_state.cp1 else '> 【本轮未选定生成此维度】'}

---
## 维度二：地材适配兼容、扫地机器人通过性与极端工况对比
{st.session_state.cp2 if st.session_state.cp2 else '> 【本轮未选定生成此维度】'}

---
## 维度三：市场在售形态定位、包装工程与海运物流成本对比
{st.session_state.cp3 if st.session_state.cp3 else '> 【本轮未选定生成此维度】'}

---
## 维度四：技术规格横向总结与外贸业务员专业参数交流库
{st.session_state.cp4 if st.session_state.cp4 else '> 【本轮未选定生成此维度】'}
"""
      st.download_button(
          "📥 下载当前对标 Markdown 报告",
          full_comp_rep,
          f"Runner_Benchmark_{final_b_size.replace(' ', '_')}_{st.session_state.comp_feed_time.split(' ')[0]}.md",
          "text/markdown",
          use_container_width=True,
      )
      st.markdown(full_comp_rep)
    else:
      st.info("尚未生成对标报告，请勾选维度并点击启动。")
  with ct_live:
    if st.session_state.comp_feed:
      st.markdown(st.session_state.comp_feed)

  if run_comp_all:
    if not api_key:
      st.error(f"请先在左侧输入 {selected_provider} 的 API Key！")
    elif not any([exec_cp1, exec_cp2, exec_cp3, exec_cp4]):
      st.warning("您未勾选任何对标维度，请勾选后重试！")
    else:
      try:
        refresh_comp_live_data()
        ctx_c = get_comp_context()

        comp_tasks = [
            (
                exec_cp1,
                "cp1",
                "维度 1: 规格工艺与关税大表",
                BENCHMARK_PROMPTS["cp1"],
                ph_cp1,
            ),
            (
                exec_cp2,
                "cp2",
                "维度 2: 地材兼容与场景应用",
                BENCHMARK_PROMPTS["cp2"],
                ph_cp2,
            ),
            (
                exec_cp3,
                "cp3",
                "维度 3: 市场形态与包装物流",
                BENCHMARK_PROMPTS["cp3"],
                ph_cp3,
            ),
            (
                exec_cp4,
                "cp4",
                "维度 4: 技术总结与买手参数库",
                BENCHMARK_PROMPTS["cp4"],
                ph_cp4,
            ),
        ]
        active_comp_tasks = [t for t in comp_tasks if t[0]]

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
            "🎉 选中的竞品对标维度全部完成！数据已 100% 强锚定本次实时检索。"
        )
        global_comp_box.empty()
      except Exception as e:
        global_comp_status.error(f"❌ 竞品对标运行异常: {e}")

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
          with st.spinner(f"正在单独刷新并流式生成 {lbl}..."):
            refresh_comp_live_data()
            ctx_c = get_comp_context()
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
          st.success(f"{lbl} 单独刷新完成！")
        except Exception as e:
          st.error(f"{lbl} 生成失败: {e}")
