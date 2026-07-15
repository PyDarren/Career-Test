# AGENTS.md - Anchor AI 协作指南

> 本文件是所有 AI 编程助手（Cursor / Claude Code / Cline / Copilot 等）在本项目中工作的**唯一权威指令集**。开始任何代码修改前，必须完整阅读本文件。

---

## 1. 🎯 项目概览 (Project Context)

**一句话描述**：面向大学生与职场新人的职业人格测评 Web 应用，采用 IPIP 大五人格（OCEAN）+ 霍兰德 RIASEC 职业兴趣理论双框架，"免费人格认证卡 + 付费深度报告"的 Freemium 模式，用户打开即测、无需登录。

**品牌名称**：Anchor

**核心技术栈**：

| 层级 | 技术 | 版本约束 | 用途 |
|------|------|----------|------|
| 语言 | Python | >= 3.11 | 后端主语言 |
| Web 框架 | Django | >= 5.0 | 主框架，全栈开发（模板渲染 + API） |
| 辅助 API | FastAPI | >= 0.110 | 仅限高性能只读接口（如批量数据查询、统计聚合），不承载核心业务事务 |
| 数据库 | MySQL | >= 8.0 | 主数据存储，支持 JSON 字段与窗口函数 |
| 缓存/消息 | Redis | >= 7.0 | 缓存层 + Celery Broker |
| 任务队列 | Celery | >= 5.3 | 异步任务与定时任务 |
| 部署架构 | Nginx → Gunicorn → Django → MySQL + Redis | — | 四层架构，禁止变更 |

**关键业务约束（不可违反）**：

- 测评流程**免登录**，用户打开应用直接开始测试
- 测评体系采用 **IPIP 大五人格（OCEAN）+ 霍兰德 RIASEC** 双理论框架，**禁止使用 MBTI**（商标侵权风险）
- 测评题目共 **80 题**：IPIP-50（大五人格 50 题，每维度 10 题）+ RIASEC-30（职业兴趣 30 题，每类型 5 题）
- 量表格式为 **7 点李克特量表**（1=完全不符合 ~ 7=非常符合），**禁止使用 6 点强制选择**
- 大五人格每维度含 2-3 道反向计分题，用于检测作答一致性
- 人格画像原型为 **243 种**（大五五维度高/中/低三分组合 3^5=243），**禁止使用 16 种 MBTI 类型**
- RIASEC 职业兴趣码为 **3 字母**（六维度取前三，并列时按 R>I>A>S>E>C 字母顺序优先）
- 三层人格标签：画像名（如"VSN-SRN"）+ RIASEC 码（如"IRC"）+ 色彩光谱（5 色圆点）
- 深度报告定价为 **2.99 元**（非 9.90 元，非 49-99 元）
- 免费结果页采用"人格认证卡"格式，包含 3D 黏土风格吉祥物
- 网页风格**对标 https://www.16personalities.com**
- 色彩光谱 5 色固定映射：O=#9B7ED8 / C=#5a96b1 / E=#5ea67e / A=#deb45c / N=#e17055
- 夜览模式：全站通过 `data-theme` 属性 + CSS `[data-theme="dark"]` 选择器实现，`dark-mode.js` 管理切换逻辑，`dark-mode.css` 包含所有暗色覆盖样式。用户偏好持久化于 `localStorage`（key: `anchor-theme`）。

---

## 2. 📁 目录结构与架构约定 (Architecture & Structure)

### 2.1 目录结构

```
Career_Test/
├── manage.py
├── requirements.txt
├── .env                          # 环境变量（禁止提交到 Git）
├── .env.example                  # 环境变量模板
├── AGENTS.md                     # 本文件
├── career_test/                  # Django 项目配置
│   ├── settings/                 # 分环境配置（base / dev / prod）
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                   # 根路由
│   ├── celery.py                 # Celery 配置
│   └── wsgi.py
├── assessment/                   # 【App 1】测评核心模块
│   ├── models.py                 # question, assessment 表
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   ├── scoring/                  # 🔥 计分算法独立封装（与 Django ORM 解耦）
│   │   ├── __init__.py
│   │   ├── engine.py             # 评分引擎入口
│   │   ├── calculators.py        # 各维度计算器（OCEAN + RIASEC）
│   │   ├── normalizer.py         # 常模归一化（百分位标准化）
│   │   ├── archetype_matcher.py  # 243 种画像匹配
│   │   ├── color_spectrum.py     # 色彩光谱生成
│   │   └── validity.py           # 效度检测与置信度计算
│   └── services/                 # 业务逻辑层
│       ├── test_service.py       # 测评流程编排
│       └── result_service.py     # 三层标签生成
├── personality/                  # 【App 2】人格画像配置模块
│   ├── models.py                 # personality_archetype 表（14 字段）
│   ├── views.py
│   └── urls.py
├── careers/                      # 【App 3】职业推荐模块
│   ├── models.py                 # career 表
│   ├── views.py
│   └── urls.py
├── payment/                      # 【App 4】支付与订单模块
│   ├── models.py                 # order 表
│   ├── views.py
│   ├── urls.py
│   └── services/
│       ├── wechat_pay.py         # 微信支付封装
│       ├── alipay.py             # 支付宝封装
│       └── callback_handler.py   # 回调处理（幂等）
├── stats/                        # 【App 5】统计与数据看板模块
│   ├── models.py                 # tracking_event, stats_daily 表
│   ├── views.py
│   └── tasks.py                  # Celery 定时任务
├── common/                       # 公共模块
│   ├── constants.py              # 业务常量（定价、题量、维度定义等）
│   ├── middleware.py             # 全局中间件（异常处理、CORS 等）
│   ├── permissions.py            # 权限类
│   ├── pagination.py             # 分页类
│   └── utils.py                  # 工具函数
├── templates/                    # Django 模板（13 个 HTML 页面已完成）
│   ├── base.html
│   ├── index.html                # 首页
│   ├── guide.html                # 测评引导页
│   ├── question.html             # 答题页
│   ├── result-free.html          # 免费结果页
│   ├── deep-report.html          # 深度报告页
│   ├── payment.html              # 支付页
│   ├── account.html              # 账户设置页
│   ├── orders.html               # 订单管理页
│   ├── history.html              # 测评历史页
│   ├── admin-questions.html      # 后台-题库管理
│   ├── admin-orders.html         # 后台-订单管理
│   ├── admin-dashboard.html      # 后台-数据看板
│   └── admin-content.html        # 后台-内容配置
├── static/                       # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
│   └── mascots/                  # 3D 黏土风格吉祥物图片（243 种）
└── tests/                        # 测试目录
    ├── test_scoring.py
    ├── test_payment.py
    └── ...
```

### 2.2 架构分层原则

1. **三层分离**：`views.py`（路由入口）→ `services/`（业务逻辑）→ `models.py`（数据访问）。Views 层禁止直接操作 ORM 写数据。
2. **计分算法独立封装**：所有测评计分逻辑必须放在 `assessment/scoring/` 目录下，不得散落在 views 或 models 中。计分引擎只接收原始答题数据、返回结构化结果，不依赖 Django ORM。
3. **FastAPI 边界**：FastAPI 仅用于只读、无副作用的查询接口（如统计聚合、画像字典查询）。所有涉及数据写入、支付、测评提交的接口必须走 Django。
4. **模板渲染优先**：本项目建设期为前后端不分离架构，页面渲染使用 Django 模板引擎。交互逻辑通过模板内嵌 `<script>` 或 `static/js/` 中的 vanilla JS / 轻量库实现。

### 2.3 数据库表清单（共 9 张，禁止新增或删除）

| 表名 | 所属 App | 说明 |
|------|---------|------|
| `personality_archetype` | personality | 243 种人格画像原型配置（14 字段） |
| `question` | assessment | 测评题库（80 题：50 大五 + 30 RIASEC） |
| `career` | careers | 职业推荐数据 |
| `assessment` | assessment | 用户测评记录 |
| `order` | payment | 支付订单 |
| `feedback` | stats | 用户反馈 |
| `customer_service_message` | stats | 客服消息 |
| `tracking_event` | stats | 行为埋点 |
| `stats_daily` | stats | 每日统计聚合 |

### 2.4 `personality_archetype` 表字段定义（14 字段）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `archetype_id` | int | 原型编号 (1-243) | 5 |
| `archetype_code` | string | 维度组合码 | OHCHEHLNAHLN |
| `archetype_name` | string | 英文标签画像名 | VSN-SRN |
| `archetype_slogan` | string | 一句话描述 | 深思熟虑的系统设计者 |
| `rarity` | string | 稀有度标签 | 稀有 |
| `rarity_percentage` | float | 人口占比 | 3.2% |
| `famous_people` | json | 同型名人列表 | ["史蒂夫·乔布斯", "埃隆·马斯克"] |
| `best_partners` | json | 最佳协作原型 ID 列表 | [1, 17, 23] |
| `career_directions` | json | 推荐职业方向 | ["系统架构师", "战略规划"] |
| `o_range` | string | 开放性区间 (high/low) | high |
| `c_range` | string | 尽责性区间 (high/low) | high |
| `e_range` | string | 外向性区间 (high/low) | low |
| `a_range` | string | 宜人性区间 (high/low) | high |
| `n_range` | string | 神经质区间 (high/low) | low |
| `mascot_url` | string | 吉祥物图片路径 | /assets/mascots/05.png |

### 2.5 API 端点约束

- 全项目共 **19 个 API 端点**，覆盖核心与辅助功能。新增端点前必须确认不在现有清单中。
- 所有 API 路径以 `/api/` 为前缀。
- RESTful 风格，资源名用复数（如 `/api/assessments/`）。

### 2.6 Celery 定时任务清单（共 5 个，禁止变更调度规则）

| 任务 | 调度规则 | 说明 |
|------|---------|------|
| 订单过期 | 每 60 秒 | 清理超时未支付订单 |
| 数据清理 | 每日 02:00 | 清理过期临时数据 |
| 日报生成 | 每日 03:00 | 生成 `stats_daily` 记录 |
| 缓存刷新 | 每小时 | 刷新热点缓存 |
| 对账 | 每日 02:30 | 与支付渠道对账 |

---

## 3. ⚠️ 核心开发准则 (Core Directives - 必须严格遵守)

### 3.1 全局规则

- **类型安全**：所有 Python 函数必须使用 type hints（参数 + 返回值）。禁止使用 `Any` 类型，如需动态类型请用 `Union` 或 `TypedDict`。
- **错误处理**：所有外部调用（数据库、Redis、支付 API、第三方服务）必须 try-except 包裹，异常需记录到 Sentry 并返回统一错误格式：
  ```python
  # 统一错误响应格式
  {"code": "ERROR_CODE", "message": "用户可读消息", "detail": "开发调试信息(prod环境隐藏)"}
  ```
- **日志规范**：使用 Python `logging` 模块，禁止 `print()`。日志级别：`DEBUG`（开发调试）、`INFO`（业务关键节点）、`WARNING`（可恢复异常）、`ERROR`（需告警）。支付与测评提交必须记录 `INFO` 级日志。
- **配置管理**：所有敏感信息（密钥、数据库密码、支付密钥）必须通过环境变量读取（`django-environ`），禁止硬编码。`.env` 文件禁止提交 Git。
- **常量管理**：业务常量（如定价 2.99、题目数量 80、维度定义）统一在 `common/constants.py` 中定义，禁止在代码中散落魔法数字。

### 3.2 后端专属规则

- **API 设计**：
  - 所有 API 必须返回统一 JSON 信封：`{"code": 0, "data": {}, "message": "success"}`。
  - 分页接口返回：`{"code": 0, "data": {"list": [], "total": 0, "page": 1, "page_size": 20}}`。
  - HTTP 状态码语义化：200 成功、400 参数错误、401 未认证、403 无权限、404 不存在、429 限流、500 服务端错误。
- **数据库事务**：
  - 涉及订单创建、测评提交、支付回调的操作必须使用 `transaction.atomic()`。
  - 禁止在事务中调用外部 HTTP 服务（如支付 API），外部调用必须在事务外执行。
  - 查询优化：列表接口必须使用 `select_related()` / `prefetch_related()` 避免 N+1 问题。
- **缓存策略**：
  - 人格画像配置、题库等低频变更数据使用 Redis 缓存，TTL 设为 1 小时，通过 Celery 定时刷新。
  - 缓存 key 命名规范：`{app}:{model}:{id}:{version}`，如 `personality:archetype:5:v2`。
  - 禁止缓存用户敏感数据（测评原始答案、订单详情）。
- **Serializer 规范**：使用 Django REST Framework Serializer，敏感字段（如 `device_fingerprint`、`phone_number`）必须在 `fields` 中显式排除或使用 `extra_kwargs = {"field": {"write_only": True}}`。
- **免登录架构**：
  - 测评提交、结果查看、免费卡片生成均不需要用户认证。
  - 使用 `device_fingerprint` + `session_token`（Cookie 或 LocalStorage）关联匿名用户的测评记录。
  - 付费报告解锁前需验证该 session 下的测评记录是否存在且有效。

### 3.3 测评业务专属规则（🔥 重点）

#### 3.3.1 计分算法

- **算法封装位置**：所有计分逻辑必须在 `assessment/scoring/` 目录下实现，与 Django views/models 完全解耦。
- **理论框架**：采用 IPIP 大五人格（OCEAN）+ 霍兰德 RIASEC 双理论框架。**禁止使用 MBTI**（四维八极、INTJ 等类型码）。
- **输入输出契约**：
  ```python
  # scoring/engine.py
  def calculate_assessment_result(
      answers: list[AnswerInput],  # 80 题原始答题数据（1-7 分）
      norm_data: NormData,          # 常模数据
  ) -> AssessmentResult:
      """
      返回结构化结果，不访问数据库、不产生副作用。
      包含：OCEAN 五维度百分位、RIASEC 六维度得分与 3 字母码、
            243 画像匹配、色彩光谱、置信度。
      """
  ```
- **大五人格评分流程（IPIP-50）**：
  1. 收集 50 道大五题项的原始作答（1-7 分）
  2. 对反向计分题进行翻转（1↔7, 2↔6, 3↔5, 4↔4）
  3. 计算每个维度的总分（10 题之和，范围 10-70）
  4. 转换为百分位数（基于常模数据）
  5. 按三分位划分高(H)/中(M)/低(L)三档
  6. 将五维度高中低组合映射到 243 种原型之一
- **RIASEC 评分流程（RIASEC-30）**：
  1. 收集 30 道 RIASEC 题项的原始作答（1-7 分）
  2. 计算每个类型的总分（5 题之和，范围 5-35）
  3. 按总分降序排列六个类型
  4. 取前三名生成三字母职业兴趣码（如 IRC）
  5. 前三名中如有并列分，按 **R > I > A > S > E > C** 字母顺序优先
- **色彩光谱生成**：五维度百分位映射为 5 色圆点，色深随分数变化：
  - O（开放性）= #9B7ED8（紫色系）
  - C（尽责性）= #5a96b1（蓝色系）
  - E（外向性）= #5ea67e（绿色系）
  - A（宜人性）= #deb45c（金色系）
  - N（神经质）= #e17055（珊瑚色系）
- **效度检测**：测谎题（3 道）/ 矛盾题对（3 对）/ 直线作答检测（全选同一值）/ 响应时间异常。
- **置信度计算**：各异常项扣分，≥0.8 正常 / 0.5-0.8 仅供参考 / <0.5 建议重测。
- **计分确定性**：相同输入必须产生相同输出，禁止在计分过程中引入随机数或时间因子。
- **测试覆盖**：计分引擎必须有 >= 95% 的单元测试覆盖率，包含边界值测试（全选 1、全选 7、平局、极端比例、反向题验证等）。

#### 3.3.2 隐私数据保护

- **测评原始答案**：用户答题数据（`assessment.answers` 字段，80 题）使用应用层加密存储（AES-256），密钥从环境变量读取。
- **数据脱敏**：日志中禁止出现用户完整答题内容、人格画像结果、手机号。需要引用时使用脱敏格式（如 `answers: [***80 items***]`、`phone: 138****1234`）。
- **数据生命周期**：用户测评原始数据仅用于本次测评计分，不纳入长期用户画像。免费报告在用户主动删除后 7 日内清除关联数据。
- **分享隐私**：生成分享卡片时，默认使用"匿名用户"昵称，禁止在分享链接中暴露用户真实信息。

#### 3.3.3 支付安全（六道防线，缺一不可）

1. **订单防篡改**：订单创建时生成签名（`order_id + amount + timestamp + secret_key` 的 HMAC-SHA256），前端不可修改金额。
2. **回调签名验证**：微信/支付宝回调必须验证签名，签名不匹配的回调直接拒绝并记录告警日志。
3. **防重复支付**：回调处理必须幂等——通过 `order_id` + `transaction_id` 去重，已处理订单的回调返回成功但不重复执行业务逻辑。
4. **订单超时与对账**：未支付订单 60 秒后自动过期（Celery 定时任务）；每日 02:30 与支付渠道对账，不一致记录触发告警。
5. **金额一致性校验**：回调金额必须与订单金额一致，不一致时拒绝解锁并触发告警。
6. **前端轮询**：支付完成后前端轮询订单状态（间隔 2 秒，最多 30 次），超时后引导用户联系客服。

```python
# payment/services/callback_handler.py 标准模式
@transaction.atomic
def handle_payment_callback(raw_callback: dict, channel: str) -> CallbackResult:
    # 1. 验证签名
    if not verify_signature(raw_callback, channel):
        log_warning("支付回调签名验证失败", channel=channel)
        return CallbackResult(rejected=True, reason="signature_mismatch")

    # 2. 解析订单
    order_id = raw_callback["out_trade_no"]
    order = select_for_update(Order, order_id)
    if not order:
        return CallbackResult(rejected=True, reason="order_not_found")

    # 3. 防重复处理
    if order.status == OrderStatus.PAID:
        log_info("重复回调，订单已支付", order_id=order_id)
        return CallbackResult(success=True, duplicated=True)

    # 4. 金额一致性校验
    if raw_callback["amount"] != order.amount:
        log_error("金额不一致", order_id=order_id, expected=order.amount, actual=raw_callback["amount"])
        trigger_alert("金额不一致告警", order_id=order_id)
        return CallbackResult(rejected=True, reason="amount_mismatch")

    # 5. 更新订单状态
    order.mark_as_paid(transaction_id=raw_callback["transaction_id"])

    # 6. 解锁深度报告
    unlock_deep_report(order)

    return CallbackResult(success=True)
```

#### 3.3.4 微信环境兼容性

- **JS-SDK 配置**：分享卡片配置（`wx.config` → `wx.ready` → `wx.updateAppMessageShareData`）必须在页面加载时完成。`jsapi_ticket` 通过后端接口获取并缓存（TTL 7200 秒）。
- **分享内容**：分享标题、描述、缩略图（人格认证卡缩略图）需根据用户测评结果动态生成。缩略图尺寸必须为 300×300 像素，格式为 JPG，大小 <= 32KB。
- **支付兼容**：微信内支付必须使用 JSAPI 支付（非 H5 支付），需获取用户 `openid`。支付宝使用手机网站支付（H5）。
- **UA 检测**：前端必须检测是否在微信浏览器内运行，据此切换支付方式和分享组件的渲染逻辑。

---

## 4. 🚫 禁止事项 (Anti-Patterns / Never Do This)

| # | 禁止事项 | 原因 |
|---|---------|------|
| 1 | **Never** 在前端代码（模板、JS）中实现或暴露测评计分算法 | 算法是核心 IP，计分必须在后端完成 |
| 2 | **Never** 使用 `Any` 类型或省略 type hints | 类型安全是项目基线要求 |
| 3 | **Never** 明文存储用户测评答案、手机号等敏感数据 | 合规要求（个人信息保护法） |
| 4 | **Never** 在 Django views 层直接编写复杂业务逻辑 | 必须下沉到 `services/` 层 |
| 5 | **Never** 在数据库事务中调用外部 HTTP 服务 | 会导致事务长时间占用连接 |
| 6 | **Never** 硬编码定价、题目数量、维度定义等业务常量 | 统一在 `common/constants.py` 管理 |
| 7 | **Never** 使用 MBTI 理论、INTJ 等类型码、四维八极模型 | MBTI 商标侵权风险，项目已切换至 IPIP+RIASEC |
| 8 | **Never** 使用 6 点强制选择量表 | 项目硬约束：7 点李克特量表（1-7 分） |
| 9 | **Never** 将深度报告定价改为非 2.99 元 | 项目硬约束 |
| 10 | **Never** 在支付回调中跳过签名验证或金额校验 | 支付安全六道防线不可省略 |
| 11 | **Never** 使用 `print()` 输出调试信息 | 必须使用 `logging` 模块 |
| 12 | **Never** 在日志中记录用户完整答题内容或人格画像结果 | 隐私数据脱敏要求 |
| 13 | **Never** 新增数据库表或删除已有表 | 表结构固定为 9 张 |
| 14 | **Never** 在测评流程中要求用户注册或登录 | 免登录是核心体验约束 |
| 15 | **Never** 使用 `.objects.all()` 返回全表数据 | 必须分页或限定查询范围 |
| 16 | **Never** 将 `DEBUG=True` 用于生产环境 | 生产环境配置必须从 `settings/prod.py` 加载 |
| 17 | **Never** 使用 `mbti_types` 作为 App 名称或 `mbti_type` 作为表名 | 已重命名为 `personality` / `personality_archetype` |
| 18 | **Never** 将深度报告第 8 章命名为"荣格八维专项解读" | 第 8 章为"大五人格五维度深度解读" |

---

## 5. 🛠️ 常用命令与工作流 (Commands & Workflows)

### 5.1 标准命令

```bash
# 环境搭建
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 数据库迁移
python manage.py makemigrations --check          # 检查是否有未生成的迁移
python manage.py migrate                          # 执行迁移
python manage.py loaddata initial_data.json       # 加载初始数据（243 画像 + 80 题 + 职业数据）

# 本地开发
python manage.py runserver 0.0.0.0:8000           # 启动开发服务器
python manage.py celery -A career_test worker -l info   # 启动 Celery Worker
python manage.py celery -A career_test beat -l info     # 启动 Celery Beat

# 代码质量
ruff check .                                      # Lint 检查
ruff check . --fix                                # 自动修复
ruff format .                                     # 代码格式化
mypy . --strict                                   # 类型检查

# 测试
python manage.py test                             # 运行全部测试
python manage.py test assessment.tests.test_scoring  # 运行指定模块测试
coverage run --source='.' manage.py test && coverage report  # 覆盖率报告
```

### 5.2 AI 修改代码后的自检清单 (Checklist)

每次代码修改完成后，AI 必须逐项确认以下清单：

- [ ] **类型检查通过**：`mypy . --strict` 无错误
- [ ] **Lint 通过**：`ruff check .` 无错误
- [ ] **格式化**：`ruff format .` 已执行
- [ ] **测试通过**：`python manage.py test` 全部通过，无新增失败
- [ ] **无敏感信息泄露**：代码中无硬编码密钥、密码、Token
- [ ] **无 `print()` 调用**：所有输出使用 `logging`
- [ ] **无 `Any` 类型**：所有函数有完整 type hints
- [ ] **无 MBTI 残留**：代码中无 MBTI / INTJ / mbti_types / mbti_type 引用
- [ ] **业务逻辑在 services 层**：Views 层无复杂业务逻辑
- [ ] **计分逻辑在 scoring 目录**：算法未泄露到 views 或 models
- [ ] **支付安全完整**：回调处理包含签名验证 + 幂等 + 金额校验
- [ ] **数据库查询优化**：无 N+1 问题，列表接口有分页
- [ ] **迁移文件已生成**：如有 model 变更，`makemigrations` 已执行
- [ ] **常量已提取**：无新增魔法数字或硬编码字符串

### 5.3 Git 提交规范

```
<type>(<scope>): <subject>

<body>
```

- **type**：`feat`（新功能）、`fix`（修复）、`refactor`（重构）、`test`（测试）、`docs`（文档）、`chore`（杂项）
- **scope**：`assessment`、`payment`、`personality`、`careers`、`stats`、`common`
- **subject**：祈使句，不超过 50 字符

示例：`feat(assessment): 实现 IPIP+RIASEC 双框架计分引擎`

---

## 6. 🤖 多 Agent 协作指南 (Multi-Agent Routing)

当使用多 Agent 协作时，各 Agent 的职责边界和交接物定义如下：

### 6.1 后端 Agent (Backend Agent)

| 维度 | 定义 |
|------|------|
| **职责范围** | Django apps 全部代码（models, views, services, urls, serializers, middleware）、Celery tasks、FastAPI 辅助接口 |
| **输入** | PRD 功能描述、数据库表设计、API 接口文档 |
| **输出** | 可运行的 Django 项目代码、迁移文件、API 接口、单元测试 |
| **禁止触碰** | `templates/` 目录下的 HTML 模板、`static/` 目录下的 JS/CSS |
| **交接物** | API 接口文档（含请求/响应格式、字段说明），提供给前端 Agent 对接 |

### 6.2 前端 Agent (Frontend Agent)

| 维度 | 定义 |
|------|------|
| **职责范围** | Django 模板（HTML，13 个页面已完成）、`static/js/` 交互逻辑、`static/css/` 样式、微信 JS-SDK 集成、3D 黏土吉祥物渲染 |
| **输入** | 后端 Agent 提供的 API 文档、PRD 中的 UI 描述、16personalities.com 参考页面 |
| **输出** | 完整的模板文件、静态资源、前端交互逻辑 |
| **禁止触碰** | Django models、views、services 层代码；计分算法；支付后端逻辑 |
| **交接物** | 模板中需后端渲染的变量清单（context requirements），提供给后端 Agent |

### 6.3 算法/内容 Agent (Algorithm & Content Agent)

| 维度 | 定义 |
|------|------|
| **职责范围** | `assessment/scoring/` 计分引擎、常模数据处理、深度报告 12 章节内容生成、243 种人格画像配置数据 |
| **深度报告 12 章结构** | 1.你的人格画像 2.人格特征分析 3.人口比例 4.相同人格名人 5.人格优势 6.人格劣势 7.成长建议 8.大五人格五维度深度解读 9.人格恋爱专题 10.最佳恋爱对象 11.深度职业专题 12.合适的职业（以 `docs/人格测试报告.md` 为权威模板）|
| **输入** | IPIP 大五人格量表规范、霍兰德 RIASEC 理论、竞品调研报告、243 种画像描述素材 |
| **输出** | 计分引擎代码（纯函数，无 Django 依赖）、深度报告内容模板（JSON/HTML 片段）、初始数据 fixture（243 画像 + 80 题 + 职业数据） |
| **禁止触碰** | Django views/models、前端模板、支付逻辑 |
| **交接物** | 计分引擎的输入输出接口定义（供后端 Agent 集成）、报告内容结构（供前端 Agent 渲染） |

### 6.4 Agent 协作流转规则

```
PRD 需求
    │
    ▼
后端 Agent ──API 文档──→ 前端 Agent
    │                          │
    │                          │
    ▼                          ▼
算法 Agent ──计分接口──→ 后端 Agent ──context 变量──→ 前端 Agent
    │                          │
    └──报告内容结构──→ 前端 Agent  │
                                ▼
                           集成测试
```

- 任何 Agent 修改代码后，必须执行第 5.2 节的自检清单。
- Agent 之间通过**接口文档**和**交接物清单**通信，禁止直接修改其他 Agent 的代码区域。
- 遇到跨 Agent 的接口变更，必须先更新接口文档，再通知相关 Agent 调整。

---

## 7. 📐 测评体系速查 (Assessment System Reference)

### 7.1 大五人格五维度（IPIP-50）

| 维度 | 英文 | 高分特征 | 低分特征 | 题量 | 维度前缀 |
|------|------|---------|---------|------|---------|
| 开放性 | Openness (O) | 好奇、创造、求新 | 务实、传统、保守 | 10 题 | BO |
| 尽责性 | Conscientiousness (C) | 自律、计划、负责 | 灵活、随性、自发 | 10 题 | BC |
| 外向性 | Extraversion (E) | 热情、社交、活跃 | 内敛、安静、独处 | 10 题 | BE |
| 宜人性 | Agreeableness (A) | 亲和、合作、信任 | 独立、理性、竞争 | 10 题 | BA |
| 神经质 | Neuroticism (N) | 敏感、焦虑、情绪化 | 稳定、冷静、自信 | 10 题 | BN |

### 7.2 霍兰德 RIASEC 六类型（RIASEC-30）

| 类型 | 英文 | 核心特征 | 典型职业 | 题量 | 维度前缀 |
|------|------|---------|---------|------|---------|
| 现实型 | Realistic (R) | 喜欢动手操作、使用工具 | 工程师、技术员 | 5 题 | RR |
| 研究型 | Investigative (I) | 喜欢分析、研究、解决复杂问题 | 科学家、分析师 | 5 题 | RI |
| 艺术型 | Artistic (A) | 喜欢创造、表达、审美设计 | 设计师、作家 | 5 题 | RA |
| 社会型 | Social (S) | 喜欢帮助、教导、服务他人 | 教师、咨询师 | 5 题 | RS |
| 企业型 | Enterprising (E) | 喜欢领导、说服、影响他人 | 管理者、销售 | 5 题 | RE |
| 常规型 | Conventional (C) | 喜欢组织、整理、处理数据 | 会计、行政 | 5 题 | RC |

### 7.3 三层人格标签体系

| 层级 | 标签类型 | 生成逻辑 | 示例 | 数量 |
|------|---------|---------|------|------|
| 第一层 | 人格画像名 | 大五五维度高/中/低三分组合映射 | VSN-SRN | 243 种原型 |
| 第二层 | RIASEC 职业兴趣码 | 六维度得分取前三，降序排列 | IRC | 120 种组合 |
| 第三层 | 色彩光谱码 | 五维度得分映射为渐变色点序列 | ●●●●● | 连续唯一 |

### 7.4 243 种人格画像原型速查

大五人格五维度各分为高(H)/中(M)/低(L)三档，组合产生 3^5 = 243 种原型。采用「族群码-修饰词码」英文大写两段式标签。完整列表见 `人格原型扩展方案-243型.md`。

| 族群码 | 全称 | O | C | 中文名 | 亚型数 |
|--------|------|---|---|--------|--------|
| VSN | VISIONARY | H | H | 战略家 | 27 |
| INS | INSPIRED | H | M | 创想家 | 27 |
| AER | AERIAL | H | L | 探索者 | 27 |
| PRG | PRAGMATIC | M | H | 执行者 | 27 |
| BAL | BALANCED | M | M | 协调者 | 27 |
| ADP | ADAPTIVE | M | L | 适应者 | 27 |
| STD | STEADY | L | H | 守护者 | 27 |
| GRD | GROUNDED | L | M | 务实者 | 27 |
| CTN | CONTENT | L | L | 安然者 | 27 |

---

## 8. 📄 前端页面清单（13 个，已全部完成）

以下页面已全部完成静态开发，品牌统一为"Anchor"：

| 序号 | 页面 | 文件名 | 说明 |
|------|------|--------|------|
| 1 | 首页 | `index.html` | Hero + 核心优势 + 用户评价 |
| 2 | 测评引导页 | `guide.html` | 三步引导 + CTA |
| 3 | 答题页 | `question.html` | 7 点李克特量表 + 进度条 |
| 4 | 免费结果页 | `result-free.html` | 三层标签 + 雷达图 + 认证卡 |
| 5 | 深度报告页 | `deep-report.html` | 12 章目录导航 + 内容展示 |
| 6 | 支付页 | `payment.html` | 微信/支付宝 + 订单摘要 |
| 7 | 账户设置页 | `account.html` | 昵称/隐私/删除账户 |
| 8 | 订单管理页 | `orders.html` | 订单列表 + 退款 + 发票 |
| 9 | 测评历史页 | `history.html` | 历史记录 + 趋势对比 |
| 10 | 后台-题库管理 | `admin-questions.html` | 题目 CRUD + 预览 |
| 11 | 后台-订单管理 | `admin-orders.html` | 订单筛选 + 导出 |
| 12 | 后台-数据看板 | `admin-dashboard.html` | KPI + 趋势图 + 漏斗 |
| 13 | 后台-内容配置 | `admin-content.html` | 报告模板 + A/B 测试 |

> 前端页面已完成静态开发，后续仅需对接后端 API。页面中当前使用模拟数据（mock data），对接时替换为真实 API 调用。

---

## 附录：关键业务常量速查

| 常量 | 值 | 定义位置 |
|------|-----|---------|
| 品牌名称 | Anchor | 全站统一 |
| 深度报告价格 | 2.99 元 | `common/constants.py: DEEP_REPORT_PRICE` |
| 题目总量 | 80 题 | `common/constants.py: QUESTION_COUNT` |
| 大五人格题量 | 50 题（每维度 10 题） | `common/constants.py: IPIP_QUESTION_COUNT` |
| RIASEC 题量 | 30 题（每类型 5 题） | `common/constants.py: RIASEC_QUESTION_COUNT` |
| 大五维度 | O/C/E/A/N | `common/constants.py: OCEAN_DIMENSIONS` |
| RIASEC 类型 | R/I/A/S/E/C | `common/constants.py: RIASEC_DIMENSIONS` |
| 维度编码前缀 | BO/BC/BE/BA/BN + RR/RI/RA/RS/RE/RC | `common/constants.py` |
| 量表格式 | 7 点李克特量表（1=完全不符合 ~ 7=非常符合） | `common/constants.py: SCALE_TYPE` |
| 人格画像数量 | 243 种（3^5） | `common/constants.py: ARCHETYPE_COUNT` |
| RIASEC 码长度 | 3 字母 | `common/constants.py: RIASEC_CODE_LENGTH` |
| RIASEC 并列优先级 | R > I > A > S > E > C | `common/constants.py` |
| 深度报告章节数 | 12 章 | `common/constants.py: REPORT_CHAPTER_COUNT` |
| 订单超时时间 | 60 秒 | `common/constants.py: ORDER_TIMEOUT_SECONDS` |
| 支付渠道 | 微信支付 + 支付宝 | `common/constants.py: PAYMENT_CHANNELS` |
| 支付轮询间隔 | 2 秒 | 前端 `payment.js` |
| 支付轮询上限 | 30 次 | 前端 `payment.js` |
| 缓存 TTL | 1 小时 | Redis 配置 |
| jsapi_ticket TTL | 7200 秒 | 微信 JS-SDK |
| 分享缩略图 | 300×300 px, JPG, ≤ 32KB | 微信 JS-SDK |
| 计分引擎测试覆盖率 | ≥ 95% | 本文件 3.3.1 节 |
| 画像配置字段数 | 14 字段 | `personality/models.py` |
| 数据库表数 | 9 张 | 禁止变更 |
| API 端点数 | 19 个 | 禁止变更 |
| Celery 定时任务数 | 5 个 | 禁止变更 |
| 色彩光谱-O | #9B7ED8 | `common/constants.py` |
| 色彩光谱-C | #5a96b1 | `common/constants.py` |
| 色彩光谱-E | #5ea67e | `common/constants.py` |
| 色彩光谱-A | #deb45c | `common/constants.py` |
| 色彩光谱-N | #e17055 | `common/constants.py` |
