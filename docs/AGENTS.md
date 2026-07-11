# AGENTS.md - 职业测评 Web 应用 AI 协作指南

> 本文件是所有 AI 编程助手（Cursor / Claude Code / Cline / Copilot 等）在本项目中工作的**唯一权威指令集**。开始任何代码修改前，必须完整阅读本文件。

---

## 1. 🎯 项目概览 (Project Context)

**一句话描述**：面向大学生与职场新人的 MBTI 职业测评 Web 应用，采用"免费人格认证卡 + 付费深度报告"的 Freemium 模式，用户打开即测、无需登录。

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
- MBTI 采用**单量表架构**（四维八极），三量表模型已废弃，禁止使用
- 深度报告定价为 **2.99 元**（非 9.90 元，非 49-99 元）
- 免费结果页采用"人格认证卡"格式，包含 3D 黏土风格吉祥物
- 测评题目使用 **6 点量表强制选择**格式，配渐变色选项
- 网页风格**对标 https://www.16personalities.com**

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
│   │   ├── calculators.py        # 各维度计算器
│   │   └── normalizer.py         # 常模归一化
│   └── services/                 # 业务逻辑层
│       ├── test_service.py       # 测评流程编排
│       └── result_service.py     # 结果生成
├── mbti_types/                   # 【App 2】人格类型配置模块
│   ├── models.py                 # mbti_type 表（9 字段）
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
│   ├── middleware.py             # 全局中间件（异常处理、CORS 等）
│   ├── permissions.py            # 权限类
│   ├── pagination.py             # 分页类
│   └── utils.py                  # 工具函数
├── templates/                    # Django 模板
│   ├── base.html
│   ├── assessment/
│   ├── result/
│   └── payment/
├── static/                       # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
│   └── mascots/                  # 3D 黏土风格吉祥物图片
└── tests/                        # 测试目录
    ├── test_scoring.py
    ├── test_payment.py
    └── ...
```

### 2.2 架构分层原则

1. **三层分离**：`views.py`（路由入口）→ `services/`（业务逻辑）→ `models.py`（数据访问）。Views 层禁止直接操作 ORM 写数据。
2. **计分算法独立封装**：所有测评计分逻辑必须放在 `assessment/scoring/` 目录下，不得散落在 views 或 models 中。计分引擎只接收原始答题数据、返回结构化结果，不依赖 Django ORM。
3. **FastAPI 边界**：FastAPI 仅用于只读、无副作用的查询接口（如统计聚合、类型字典查询）。所有涉及数据写入、支付、测评提交的接口必须走 Django。
4. **模板渲染优先**：本项目建设期为前后端不分离架构，页面渲染使用 Django 模板引擎。交互逻辑通过模板内嵌 `<script>` 或 `static/js/` 中的 vanilla JS / 轻量库实现。

### 2.3 数据库表清单（共 9 张，禁止新增或删除）

| 表名 | 所属 App | 说明 |
|------|---------|------|
| `mbti_type` | mbti_types | 16 种人格类型配置（9 字段） |
| `question` | assessment | 测评题库 |
| `career` | careers | 职业推荐数据 |
| `assessment` | assessment | 用户测评记录 |
| `order` | payment | 支付订单 |
| `feedback` | stats | 用户反馈 |
| `customer_service_message` | stats | 客服消息 |
| `tracking_event` | stats | 行为埋点 |
| `stats_daily` | stats | 每日统计聚合 |

### 2.4 API 端点约束

- 全项目共 **19 个 API 端点**，覆盖核心与辅助功能。新增端点前必须确认不在现有清单中。
- 所有 API 路径以 `/api/` 为前缀。
- RESTful 风格，资源名用复数（如 `/api/assessments/`）。

### 2.5 Celery 定时任务清单（共 5 个，禁止变更调度规则）

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
- **常量管理**：业务常量（如定价 2.99、题目数量、维度定义）统一在 `common/constants.py` 中定义，禁止在代码中散落魔法数字。

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
  - MBTI 类型配置、题库等低频变更数据使用 Redis 缓存，TTL 设为 1 小时，通过 Celery 定时刷新。
  - 缓存 key 命名规范：`{app}:{model}:{id}:{version}`，如 `mbti_types:type:INTJ:v2`。
  - 禁止缓存用户敏感数据（测评原始答案、订单详情）。
- **Serializer 规范**：使用 Django REST Framework Serializer，敏感字段（如 `device_fingerprint`、`phone_number`）必须在 `fields` 中显式排除或使用 `extra_kwargs = {"field": {"write_only": True}}`。
- **免登录架构**：
  - 测评提交、结果查看、免费卡片生成均不需要用户认证。
  - 使用 `device_fingerprint` + `session_token`（Cookie 或 LocalStorage）关联匿名用户的测评记录。
  - 付费报告解锁前需验证该 session 下的测评记录是否存在且有效。

### 3.3 测评业务专属规则（🔥 重点）

#### 3.3.1 计分算法

- **算法封装位置**：所有计分逻辑必须在 `assessment/scoring/` 目录下实现，与 Django views/models 完全解耦。
- **输入输出契约**：
  ```python
  # scoring/engine.py
  def calculate_mbti_result(
      answers: list[AnswerInput],  # 原始答题数据
      norm_data: NormData,          # 常模数据
  ) -> MBTIResult:
      """
      返回结构化结果，不访问数据库、不产生副作用。
      """
  ```
- **单量表架构**：使用 MBTI 四维八极单量表模型（E/I, S/N, T/F, J/P）。禁止引入三量表或多模型混合计算。
- **计分确定性**：相同输入必须产生相同输出，禁止在计分过程中引入随机数或时间因子。
- **测试覆盖**：计分引擎必须有 >= 95% 的单元测试覆盖率，包含边界值测试（全选 A、全选 B、极端比例等）。

#### 3.3.2 隐私数据保护

- **测评原始答案**：用户答题数据（`assessment.answers` 字段）使用应用层加密存储（AES-256），密钥从环境变量读取。
- **数据脱敏**：日志中禁止出现用户完整答题内容、人格类型结果、手机号。需要引用时使用脱敏格式（如 `answers: [***86 items***]`、`phone: 138****1234`）。
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
| 7 | **Never** 使用三量表模型或混合多理论计分 | 项目硬约束：单量表架构 |
| 8 | **Never** 将深度报告定价改为非 2.99 元 | 项目硬约束 |
| 9 | **Never** 在支付回调中跳过签名验证或金额校验 | 支付安全六道防线不可省略 |
| 10 | **Never** 使用 `print()` 输出调试信息 | 必须使用 `logging` 模块 |
| 11 | **Never** 在日志中记录用户完整答题内容或人格类型结果 | 隐私数据脱敏要求 |
| 12 | **Never** 新增数据库表或删除已有表 | 表结构固定为 9 张 |
| 13 | **Never** 在测评流程中要求用户注册或登录 | 免登录是核心体验约束 |
| 14 | **Never** 使用 `.objects.all()` 返回全表数据 | 必须分页或限定查询范围 |
| 15 | **Never** 将 `DEBUG=True` 用于生产环境 | 生产环境配置必须从 `settings/prod.py` 加载 |

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
python manage.py loaddata initial_data.json       # 加载初始数据（159 条）

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
- **scope**：`assessment`、`payment`、`mbti_types`、`careers`、`stats`、`common`
- **subject**：祈使句，不超过 50 字符

示例：`feat(assessment): 实现 MBTI 单量表计分引擎`

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
| **职责范围** | Django 模板（HTML）、`static/js/` 交互逻辑、`static/css/` 样式、微信 JS-SDK 集成、3D 黏土吉祥物渲染 |
| **输入** | 后端 Agent 提供的 API 文档、PRD 中的 UI 描述、16personalities.com 参考页面 |
| **输出** | 完整的模板文件、静态资源、前端交互逻辑 |
| **禁止触碰** | Django models、views、services 层代码；计分算法；支付后端逻辑 |
| **交接物** | 模板中需后端渲染的变量清单（context requirements），提供给后端 Agent |

### 6.3 算法/内容 Agent (Algorithm & Content Agent)

| 维度 | 定义 |
|------|------|
| **职责范围** | `assessment/scoring/` 计分引擎、常模数据处理、深度报告 12 章节内容生成、MBTI 类型配置数据 |
| **深度报告 12 章结构** | 1.你的人格类型 2.人格特征分析 3.人口比例 4.相同人格名人 5.人格优势 6.人格劣势 7.成长建议 8.荣格八维专项解读 9.人格恋爱专题 10.最佳恋爱对象 11.深度职业专题 12.合适的职业（以 `Report/人格测试报告.md` 为权威模板）|
| **输入** | MBTI 理论规范、竞品调研报告中的算法差异化策略、16 种人格类型描述素材 |
| **输出** | 计分引擎代码（纯函数，无 Django 依赖）、深度报告内容模板（JSON/HTML 片段）、初始数据 fixture |
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

## 附录：关键业务常量速查

| 常量 | 值 | 定义位置 |
|------|-----|---------|
| 深度报告价格 | 2.99 元 | `common/constants.py: DEEP_REPORT_PRICE` |
| 题目数量 | 86 题 | `common/constants.py: QUESTION_COUNT` |
| 测评维度 | E/I, S/N, T/F, J/P（单量表） | `common/constants.py: MBTI_DIMENSIONS` |
| 量表格式 | 6 点强制选择 | `common/constants.py: SCALE_TYPE` |
| 深度报告章节数 | 12 章 | `common/constants.py: REPORT_CHAPTER_COUNT`，以 `Report/人格测试报告.md` 为权威模板 |
| 订单超时时间 | 60 秒 | `common/constants.py: ORDER_TIMEOUT_SECONDS` |
| 支付渠道 | 微信支付 + 支付宝 | `common/constants.py: PAYMENT_CHANNELS` |
| MBTI 类型配置字段数 | 9 字段 | `mbti_types/models.py` |
| 数据库表数 | 9 张 | — |
| API 端点数 | 19 个 | — |
| Celery 定时任务数 | 5 个 | — |
