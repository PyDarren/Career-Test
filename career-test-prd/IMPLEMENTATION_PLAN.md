# 职探 — 项目实施计划

**文档版本**：v1.0
**创建日期**：2026-07-09
**关联文档**：PRD.md v3.5 / TECH_DESIGN.md v1.2 / AGENTS.md
**文档状态**：评审稿

---

## 目录

- [实施计划](#实施计划)
  - [阶段一：需求确认与前期准备](#阶段一需求确认与前期准备)
  - [阶段二：数据准备与素材制作](#阶段二数据准备与素材制作)
  - [阶段三：基础设施搭建与项目初始化](#阶段三基础设施搭建与项目初始化)
  - [阶段四：核心测评模块开发](#阶段四核心测评模块开发)
  - [阶段五：结果页与支付模块开发](#阶段五结果页与支付模块开发)
  - [阶段六：深度报告与支撑功能开发](#阶段六深度报告与支撑功能开发)
  - [阶段七：测试与质量保障](#阶段七测试与质量保障)
  - [阶段八：部署上线](#阶段八部署上线)
  - [阶段九：运营监控与首周复盘](#阶段九运营监控与首周复盘)
- [阶段依赖关系图](#阶段依赖关系图)
- [里程碑节点](#里程碑节点)

---

## 实施计划

### 阶段一：需求确认与前期准备

**阶段核心目标**：完成产品需求终审、技术方案确认、资质合规准备、预测试验证

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 1.1 | 需求侧 | PRD v3.5 评审通过：确认 15 项功能范围、12 章深度报告内容标准、2.99 元定价、Freemium 商业模式 | PRD 评审签字稿 | 无 |
| 1.2 | 需求侧 | 确认用户画像（在校大学生 18-24 岁 + 职场新人 22-28 岁）和核心 KPI 目标值（测评完成率 ≥ 72%、付费转化率 ≥ 8%、分享率 ≥ 15%） | KPI 目标确认书 | 1.1 |
| 1.3 | 需求侧 | 确认 48 题量表设计：四维度 × 三面向 × 四题（含 1 道反向题），每维度 12 题 | 量表题库终稿（含题号、维度、面向、A/B 极描述、pole_a/pole_b 字母、is_reverse 标记） | 1.1 |
| 1.4 | 需求侧 | 组织 30-50 人预测试：对比 6 点刻度版与标准 MBTI（93 题）信效度一致性 ≥ 80% | 预测试报告（含重测信度 ≥ 0.85 的验证结果） | 1.3 |
| 1.5 | 需求侧 | 确认职业数据库收录范围：80-120 个职业，来源为《职业分类大典（2022 年版）》，薪资数据来源 Boss 直聘/拉勾网 | 职业数据库收录清单 | 1.1 |
| 1.6 | 需求侧 | 确认 16 型 MBTI 配置数据：type_code/type_name/type_slogan/rarity（精确百分比）/famous_people（2-3 人）/best_partners/romantic_matches/mascot_url/type_description（200-300 字） | 16 型配置数据终稿 | 1.1 |
| 1.7 | 需求侧 | 确认深度报告 12 章内容模板：每章字数标准（第二章 400-500 字、第五章每项 150-200 字等）、占位符格式 `{{placeholder}}`、个性化底线 ≥ 60% | 12 章报告模板终稿（含占位符定义表） | 1.6 |
| 1.8 | 需求侧 | 确认荣格八维认知功能栈映射表：16 型各对应 dominant/auxiliary/tertiary/inferior 四功能 | 认知功能栈映射表 | 1.6 |
| 1.9 | 合规侧 | 完成 ICP 备案（个人主体或企业主体），确认是否需 ICP 经营许可证 | ICP 备案号 | 无 |
| 1.10 | 合规侧 | 确认支付资质：微信支付商户号申请、支付宝商户入驻，预留 2 周缓冲 | 微信支付商户号 + 支付宝 APPID | 无 |
| 1.11 | 合规侧 | 编写隐私声明（≤ 200 字）和免责声明（固定文案），确认数据最小化原则合规 | 隐私声明 + 免责声明文本 | 1.1 |
| 1.12 | 技术侧 | TECH_DESIGN v1.2 评审通过：确认 9 张数据库表、19 个 API 端点、6 个 Django app 划分、缓存策略、部署架构 | 技术评审签字稿 | 1.1 |
| 1.13 | 技术侧 | 确认服务器配置：2C4G 云服务器、MySQL 8.0、Redis 7.0、域名 + SSL 证书 | 服务器购买清单 + 域名 | 1.9 |

---

### 阶段二：数据准备与素材制作

**阶段核心目标**：完成所有静态数据制作、视觉素材生产、可并行于阶段三

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 2.1 | 数据制作 | 编写 48 题的 Django fixture JSON：question_order(1-48)/dimension(EI,SN,TF,JP)/facet/facet_order/text_a/text_b/pole_a/pole_b/is_reverse/display_order | `apps/assessment/fixtures/questions.json` | 阶段一 1.3 |
| 2.2 | 数据制作 | 编写 16 型 MBTI 配置的 fixture JSON：包含 9 张表中 mbti_type 表的全部字段（type_code 到 report_career_list），report_* 字段使用 `{{placeholder}}` 占位符 | `apps/mbti_types/fixtures/mbti_types.json` | 阶段一 1.6、1.7、1.8 |
| 2.3 | 数据制作 | 编写 80-120 个职业的 fixture JSON：career_id/career_name/category/mbti_fit(JSON 数组)/mbti_ideal(JSON 维度画像)/cognitive_fit/work_style/skill_required/salary_range/growth_prospect/description/match_tags | `apps/careers/fixtures/careers.json` | 阶段一 1.5 |
| 2.4 | 数据制作 | 编写认知功能栈映射表 Python 常量：`COGNITIVE_STACK_MAP` 字典，16 型各对应 4 功能 | `apps/assessment/scoring.py` 中的常量定义 | 阶段一 1.8 |
| 2.5 | 视觉素材 | 制作 16 种 MBTI 类型 3D 黏土风格人偶插画：PNG + WebP 格式，单张 ≤ 80KB，尺寸适配认证卡右侧区域 | 16 张 WebP 人偶图片 → CDN | 阶段一 1.6 |
| 2.6 | 视觉素材 | 制作产品二维码：指向首页 `https://careertest.example.com/`，用于分享卡片底部 | 产品二维码 PNG | 阶段一 1.13 |
| 2.7 | 视觉素材 | 确认视觉设计系统 CSS 变量值：品牌主色 `#4D3E8C`、四角色组色、6 点刻度渐变色、认证卡渐变背景 | 设计系统确认书 | 阶段一 1.12 |
| 2.8 | 数据验证 | 交叉验证职业数据库：选取 30 个典型职业，与 16Personalities、北森对比一致性 ≥ 70% | 职业数据库交叉验证报告 | 2.3 |

---

### 阶段三：基础设施搭建与项目初始化

**阶段核心目标**：完成开发环境、项目骨架、数据库表结构、基础配置

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 3.1 | 技术开发 | 搭建 Python 3.12 虚拟环境，安装全部依赖（Django 5.0.6/redis/django-redis/celery/cryptography/Pillow/PyMySQL） | `requirements.txt` + `venv/` | 阶段一 1.12 |
| 3.2 | 技术开发 | 创建 Django 项目 `caretest`，分拆 settings 为 base/development/production 三层，配置 INSTALLED_APPS（6 个 app）、MIDDLEWARE（含自定义 RateLimitMiddleware） | `caretest/settings/` 目录 | 3.1 |
| 3.3 | 技术开发 | 创建 6 个 Django app：assessment/mbti_types/careers/payment/stats/common，各含 models/views/urls/migrations/tests | `apps/` 目录结构 | 3.2 |
| 3.4 | 技术开发 | 编写 9 张数据库表的 Django Model：mbti_type(16 行)/question(48 行)/career(80-120 行)/assessment/order/feedback/customer_service_message/tracking_event/stats_daily | `apps/*/models.py` | 3.3 |
| 3.5 | 技术开发 | 配置 MySQL 8.0 数据库连接（production.py）和 SQLite（development.py），charset=utf8mb4，sql_mode='STRICT_TRANS_TABLES' | settings 数据库配置 | 3.2 |
| 3.6 | 技术开发 | 配置 Redis 缓存：`django.core.cache.backends.redis.RedisCache`，DB 1，会话引擎 `signed_cookies`，SESSION_COOKIE_AGE=86400×90 | settings 缓存配置 | 3.2 |
| 3.7 | 技术开发 | 创建 base.html 基础模板：HTML5 + lang="zh-CN" + CSS/JS 引入 + data-role 属性 + nav 导航栏 + footer 页脚 | `templates/base.html` | 3.3 |
| 3.8 | 技术开发 | 创建静态文件目录结构：static/css/main.css（设计系统 CSS 变量）/static/js/main.js（工具函数）/static/images/mascots//static/libs/ | `static/` 目录 | 3.3 |
| 3.9 | 技术开发 | 执行 `makemigrations` + `migrate` 生成全部迁移文件并建表 | migration 文件 + db.sqlite3 | 3.4、3.5 |
| 3.10 | 技术开发 | 编写 common app 公共模块：RateLimitMiddleware（/api/ 路径 60 次/分钟限流）、APIError 异常类、api_success_response/api_error_response 函数、site_settings 上下文处理器 | `apps/common/middleware.py` + `responses.py` + `context_processors.py` | 3.3 |
| 3.11 | 技术开发 | 加载初始 fixture 数据：`loaddata mbti_types.json questions.json careers.json` | 数据库填充 16 型 + 48 题 + 80-120 职业 | 3.9、阶段二 2.1-2.3 |
| 3.12 | 技术开发 | 配置 .env 环境变量模板：DB_USER/DB_PASSWORD/REDIS_URL/WECHAT_APP_ID/WECHAT_MCH_ID/WECHAT_API_KEY/ALIPAY_APP_ID/ALIPAY_PRIVATE_KEY/SENTRY_DSN | `.env.example` | 3.2 |

---

### 阶段四：核心测评模块开发

**阶段核心目标**：完成首页、答题页、评分引擎、职业匹配算法

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 4.1 | 技术开发 | 开发首页 view + 模板：GET `/` → HomeView → `pages/home.html`，展示 slogan、测评入口卡片、已完成人数（读取 Redis `stats:completed_count`） | HomeView + home.html | 阶段三 3.7、3.11 |
| 4.2 | 技术开发 | 开发答题页 view + 模板：GET `/assessment/` → AssessmentView → `pages/assessment.html`，从 question 表加载 48 题（按 display_order 排序）传入模板 | AssessmentView + assessment.html | 阶段三 3.11 |
| 4.3 | 技术开发 | 开发答题页前端 JS（assessment.js）：IIFE 封装 Assessment 对象，管理 questions/currentIdx/answers；selectPosition(position) 选择后 300ms 延迟跳转；每 5 题保存进度到 `localStorage['ct_assessment_progress']`；loadProgress() 7 天过期检查；恢复时弹窗询问"是否继续上次测评" | `static/js/assessment.js` | 4.2 |
| 4.4 | 技术开发 | 开发 6 点刻度量表选择器组件：6 个渐变色圆点（位置 1 大圆 36px → 位置 3 小圆 20px → 位置 4 小圆 → 位置 6 大圆），A 侧紫色 B 侧青色，选中后弹性放大动画 200ms | `templates/partials/scale_selector.html` + CSS | 4.2 |
| 4.5 | 技术开发 | 开发评分引擎 ScoringEngine 类（scoring.py）：10 步算法实现 — POSITION_MAP 映射、面向计分（4 题/面向）、维度计分（12 题/维度，满分 36）、倾向强度计算、类型判定（临界 → X）、一致性检测（面向一致性 + 反向题 + 极端作答 ≥ 8 题连续）、认知功能栈查表推导 | `apps/assessment/scoring.py` | 阶段二 2.4 |
| 4.6 | 技术开发 | 开发评分 API：POST `/api/score/` → ScoreView，校验 answers 长度=48 且 position ∈ [1,6]、校验 Referer、调用 ScoringEngine.calculate()、查询 mbti_type 配置、调用 CareerMatcher、创建 Assessment 记录、返回完整 JSON 结果 | ScoreView + 评分结果 JSON 响应 | 4.5、4.7 |
| 4.7 | 技术开发 | 开发职业匹配算法 CareerMatcher 类（matching.py）：匹配度 = type_score×0.6 + strength_score×0.4；类型直接匹配（100/70/0 分）、维度强度余弦相似度、过滤 < 50 分、按 match_score 降序返回 top 5 | `apps/careers/matching.py` | 阶段三 3.11 |
| 4.8 | 技术开发 | 开发评分结果缓存：答案指纹 MD5 → Redis key `score:{hash}`，TTL 1 小时，缓存命中时仍创建 assessment 记录但跳过计算 | scoring.py 中的缓存逻辑 | 4.5 |
| 4.9 | 技术开发 | 开发前端降级评分 FallbackScoring（fallback_scoring.js）：position 1-3 → A 极 +1，4-6 → B 极 +1，分母 12，返回 `degraded: true`，无面向分析和认知功能 | `static/js/fallback_scoring.js` | 4.5 |
| 4.10 | 测试 | 编写评分引擎单元测试：全选位置 1 → 全 A 极、临界维度 6:6 → X、面向不一致标记、极端作答 8 题连续 → extreme_response、INTJ 认知功能栈 Ni>Te>Fi>Se，覆盖率 ≥ 90% | `apps/assessment/tests/test_scoring.py` | 4.5 |
| 4.11 | 测试 | 编写职业匹配单元测试：类型直接匹配 100 分、相邻类型 70 分、余弦相似度计算、低于 50 分过滤，覆盖率 ≥ 85% | `apps/careers/tests/test_matching.py` | 4.7 |
| 4.12 | 测试 | 编写评分 API 集成测试：正常 48 题请求、答案数量不足返回 400、非本站 Referer 返回 403、异常处理 | `apps/assessment/tests/test_views.py` | 4.6 |

---

### 阶段五：结果页与支付模块开发

**阶段核心目标**：完成基础结果页（人格认证卡）、分享功能、支付流程、深度报告页

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 5.1 | 技术开发 | 开发结果页 view + 模板：GET `/result/<uuid>/` → ResultView → `pages/result.html`，查询 Assessment 记录 + mbti_type 配置，渲染认证卡（双色挂签 + 类型代码渐变大字 + 3D 人偶 + 稀有度 + 名人 + 最佳搭子 + 四维度倾向条 + 推荐职业 + 分享按钮 + 付费墙） | ResultView + result.html | 阶段四 4.6 |
| 5.2 | 技术开发 | 开发认证卡可复用组件：cert_card.html（传入 type_code/type_name/type_slogan/rarity/famous_people/best_partners/mascot_url）+ dimension_bars.html（四维度水平条形图，A 侧紫色渐变到 B 侧青色） | `templates/partials/cert_card.html` + `dimension_bars.html` | 5.1 |
| 5.3 | 技术开发 | 开发结果页前端 JS（result.js）：ECharts 渲染维度倾向条形图（800ms 动画）、职业标签点击展开详情、1.5 秒生成动画后卡片从底部滑入（500ms）、人偶图片懒加载 | `static/js/result.js` | 5.1 |
| 5.4 | 技术开发 | 开发分享功能 ShareCard 类（result.js）：750×1334 Canvas 画布、渐变紫底背景 → 加载 3D 人偶 → 类型代码（渐变紫 72px）→ 类型标语 → 稀有度 → 产品二维码 → `canvas.toDataURL('image/png')` → 保存/分享至微信 | ShareCard Canvas 合成逻辑 | 5.1、阶段二 2.5、2.6 |
| 5.5 | 技术开发 | 开发支付弹窗 UI：点击"解锁深度报告"弹出模态框，展示 12 章内容概览 + 部分章节模糊化预览 + 2.99 元价格 + 微信支付/支付宝选择按钮 | `pages/result.html` 中的支付弹窗 HTML + CSS | 5.1 |
| 5.6 | 技术开发 | 开发创建订单 API：POST `/api/payment/create/` → CreatePaymentView，校验 assessment_id 归属、检查已有 paid 订单（唯一约束）、过期旧 pending 订单、创建新 Order（amount 服务端硬编码 `Decimal('2.99')`）、调用支付 SDK 生成支付链接、返回 `{order_no, pay_url, amount, expires_in: 900}` | CreatePaymentView | 阶段三 3.4 |
| 5.7 | 技术开发 | 开发微信支付 V3 封装（wechat_pay.py）：WechatPay 类，create_payment（统一下单 NATIVE 扫码）、verify_notify（V3 回调验签：提取签名 → 获取平台证书缓存 Redis TTL 12h → RSA-SHA256 验证 → AES-256-GCM 解密 resource.ciphertext） | `apps/payment/wechat_pay.py` | 阶段一 1.10 |
| 5.8 | 技术开发 | 开发支付宝 V3 封装（alipay_pay.py）：AlipayPay 类，create_payment、verify_notify（RSA2 签名验证） | `apps/payment/alipay_pay.py` | 阶段一 1.10 |
| 5.9 | 技术开发 | 开发支付回调处理：POST `/payment/wechat/notify/` → WechatNotifyView（`@csrf_exempt` + 验签 + 幂等处理 `select_for_update` + 更新 Order.status='paid'）；POST `/payment/alipay/notify/` → AlipayNotifyView | WechatNotifyView + AlipayNotifyView | 5.7、5.8 |
| 5.10 | 技术开发 | 开发订单状态查询 API：GET `/api/order/status/<order_no>/` → OrderStatusView，返回 `{order_no, status, amount, payment_method, created_at, paid_at}` | OrderStatusView | 5.6 |
| 5.11 | 技术开发 | 开发前端支付轮询（payment.js）：PaymentPoller 每 2 秒轮询 `/api/order/status/`，最多 60 次（2 分钟），收到 `paid` 跳转 `/report/<order_no>/`，超时展示"支付确认中" | `static/js/payment.js` | 5.10 |
| 5.12 | 技术开发 | 开发深度报告页 view + 模板：GET `/report/<order_no>/` → ReportView，校验订单 status='paid' 且 paid_at ≤ 90 天、查询 mbti_type 的 report_* 字段、ReportRenderer 替换 `{{placeholder}}` 占位符、渲染 12 章内容 + 章节导航 | ReportView + report.html | 5.9、阶段二 2.2 |
| 5.13 | 技术开发 | 开发 ReportRenderer 类：根据用户实际得分替换占位符（dim_EI_percentage/facet_X_Y_pole/cog_dominant 等），个性化底线 ≥ 60% 内容基于具体得分 | `apps/mbti_types/report_renderer.py` | 阶段二 2.2 |
| 5.14 | 技术开发 | 开发报告访问凭证管理：localStorage `ct_paid_reports` 列表写入、访问 /report/ 时校验订单状态 + 90 天有效期、多设备限制（同一订单仅单设备访问）、过期标记 expired | 凭证管理逻辑 | 5.12 |
| 5.15 | 技术开发 | 开发报告找回 API：POST `/api/report/recover/` → ReportRecoverView，输入 order_no 校验 status='paid' 且 ≤ 90 天，返回 report_url | ReportRecoverView | 5.12 |
| 5.16 | 测试 | 编写支付安全测试：金额篡改防护（前端传 amount 被忽略）、防重复支付（已有 paid 返回 400）、回调验签（正确/错误签名）、金额一致性校验、订单超时过期，覆盖率 ≥ 90% | `apps/payment/tests/test_security.py` | 5.6、5.9 |
| 5.17 | 测试 | 编写微信支付验签测试：签名生成、正确签名通过、错误签名返回 401、回调解密，覆盖率 ≥ 95% | `apps/payment/tests/test_wechat.py` | 5.7 |
| 5.18 | 测试 | 编写深度报告渲染测试：占位符替换正确性、60% 个性化底线检查、90 天过期校验、多设备访问限制 | `apps/mbti_types/tests/test_report.py` | 5.12、5.13 |

---

### 阶段六：深度报告与支撑功能开发

**阶段核心目标**：完成 7 项支撑功能、SEO、前端埋点、Celery 定时任务

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 6.1 | 技术开发 | 开发测评历史 API：GET `/api/history/<uuid>/` → HistoryView，基于 UUID 查询 Assessment 记录，最多返回 3 条（含 mbti_type/created_at/dimensions），按 created_at 降序 | HistoryView | 阶段四 4.6 |
| 6.2 | 技术开发 | 开发浏览器指纹生成（fingerprint.js）：Canvas 200×50 绘制 'CareerTest_fp_2026' → 像素数据 → 64 位哈希 → 发送至后端 → 后端存储 SHA-256 到 Redis `fp:{hash}` TTL 90 天 | `static/js/fingerprint.js` | 阶段三 3.10 |
| 6.3 | 技术开发 | 开发复测提醒：完成测评 30 天后再次访问时弹窗"距上次测评已 30 天"，检查 `localStorage['ct_last_result']` 的 timestamp | result.js 中的复测检查逻辑 | 阶段四 4.3 |
| 6.4 | 技术开发 | 开发用户反馈 API：POST `/api/feedback/` → FeedbackView，支持 career_mismatch/career_partial/report_rating/report_text 四种类型，同一 uuid+assessment_id 防重复提交，写入 feedback 表 | FeedbackView | 阶段三 3.4 |
| 6.5 | 技术开发 | 开发用户反馈 UI：基础结果页推荐职业旁"推荐不准"按钮（选项：方向完全不对/部分匹配/其他）、深度报告底部 👍/👎 + 文字反馈（限 200 字） | result.html + report.html 中的反馈 UI | 6.4 |
| 6.6 | 技术开发 | 开发帮助中心页面：GET `/help/` → HelpView → `pages/help.html`，8 条 FAQ（测评原理/结果准确性/推荐职业不匹配/深度报告内容/支付后看不到报告/重新查看已购报告/清除数据/联系方式），支持搜索和折叠展开 | HelpView + help.html | 阶段三 3.7 |
| 6.7 | 技术开发 | 开发数据清除页面：GET `/settings/` → SettingsView → `pages/settings.html`，清除 localStorage 中 ct_uuid/ct_assessment_progress/ct_last_result/ct_paid_reports，二次确认弹窗，逐项清除展示完成状态 | SettingsView + settings.html | 阶段三 3.7 |
| 6.8 | 技术开发 | 开发客服联系功能：POST `/api/customer-service/` → CustomerServiceView，留言表单（微信号/手机号选填、问题描述必填限 500 字、订单号选填），写入 customer_service_message 表 | CustomerServiceView | 阶段三 3.4 |
| 6.9 | 技术开发 | 开发客服联系 UI：支付弹窗底部、支付失败弹窗、帮助中心 Q8、深度报告页底部，展示客服微信号（长按复制）+ 在线留言表单 | 各页面中的客服 UI 组件 | 6.8 |
| 6.10 | 技术开发 | 开发分享回流落地页：URL 参数 ref（分享者 UUID）/type（MBTI 类型）/name（昵称），顶部展示"你的朋友测出了 ENFP 竞选者"引导卡片，3 秒后展示"开始测评"按钮 + 倒计时动效，type 参数存在时展示人偶缩略图 | home.html 中的回流卡片逻辑 | 阶段四 4.1 |
| 6.11 | 技术开发 | 开发 SEO 优化：各页面独立 title/description/og 标签（首页"职探 — 8 分钟 MBTI 职业性格测评"、结果页"我是 ENFP 竞选者，来测测你的 MBTI 职业性格"）、JSON-LD 结构化数据（@type: WebApplication）、sitemap.xml + robots.txt | SEO 标签 + sitemap.xml + robots.txt | 阶段四 4.1、5.1 |
| 6.12 | 技术开发 | 开发前端埋点 SDK（tracking.js）：Tracker 对象，17 个事件（page_view/assessment_start/assessment_answer/assessment_pause/assessment_resume/assessment_submit/result_view/career_click/career_feedback/share_click/share_success/payment_click/payment_success/payment_fail/report_view/report_scroll/report_feedback/referral_landing），批量上报每 5 条或页面隐藏时发送，使用 sendBeacon | `static/js/tracking.js` | 阶段三 3.10 |
| 6.13 | 技术开发 | 开发埋点上报 API：POST `/api/track/` → TrackView，高频事件存 Redis list `track:{uuid}`，低频事件直接入 tracking_event 表 | TrackView | 阶段三 3.4 |
| 6.14 | 技术开发 | 开发已完成测评人数 API：GET `/api/stats/completed-count/` → CompletedCountView，读取 Redis `stats:completed_count`（TTL 1 小时），首页展示 | CompletedCountView | 阶段三 3.6 |
| 6.15 | 技术开发 | 配置 Celery：app = Celery('careertest')，autodiscover_tasks，配置 broker=Redis | `caretest/celery.py` | 阶段三 3.6 |
| 6.16 | 技术开发 | 开发 Celery 定时任务 4 个：①expire_pending_orders（每 60 秒，过期 pending 订单标记 expired）②cleanup_old_assessments（每天 02:00，清理 30 天前未付费记录）③generate_daily_stats（每天 03:00，聚合前一天 UV/完成率/付费数/收入写入 stats_daily）④refresh_completed_count（每小时，刷新 Redis 已完成人数缓存） | `apps/stats/tasks.py` | 6.15 |
| 6.17 | 技术开发 | 开发每日对账任务：daily_reconciliation（每天 02:00），拉取微信/支付宝前一天交易流水，与本地 paid 订单逐一核对，处理漏单（补单）/多单（标记异常） | `apps/payment/tasks.py` | 6.15 |
| 6.18 | 技术开发 | 开发全局异常捕获中间件：ExceptionMiddleware 捕获 APIError 返回对应错误响应（9 个错误码），捕获未处理异常返回 code=5001 + 记录日志 | `apps/common/middleware.py` 中的 ExceptionMiddleware | 阶段三 3.10 |
| 6.19 | 技术开发 | 配置 LocalStorage 键名规范：ct_uuid（永久）/ct_assessment_progress（7 天）/ct_last_result（会话级）/ct_paid_reports（90 天标记过期）/ct_referrer_type（会话级）/ct_settings（永久），各键写入/读取/清除时机 | 前端 JS 中的 localStorage 管理 | 4.3、5.14 |
| 6.20 | 测试 | 编写支撑功能测试：反馈防重复提交、客服留言存储、数据清除完整性、报告找回校验、测评历史返回条数限制 | `apps/stats/tests/` + `apps/payment/tests/` | 6.4-6.8 |

---

### 阶段七：测试与质量保障

**阶段核心目标**：完成全量测试、性能验证、安全审计、兼容性验证

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 7.1 | 测试 | 运行全量单元测试：`python manage.py test`，确保评分引擎（≥ 90%）、职业匹配（≥ 85%）、支付安全（≥ 90%）、微信验签（≥ 95%）、评分 API（≥ 80%）覆盖率达标 | 测试覆盖率报告 | 阶段四-六全部开发 |
| 7.2 | 测试 | 端到端全流程测试：首页 → 答题 48 题 → 评分 → 结果页认证卡 → 职业推荐 → 分享 Canvas 合成 → 支付弹窗 → 微信支付 → 深度报告 12 章 → 反馈 → 历史记录 → 复测提醒 | E2E 测试报告 | 阶段四-六全部开发 |
| 7.3 | 测试 | 支付全链路沙箱测试：微信支付沙箱下单 → 扫码支付 → 回调验签 → 订单状态更新 → 报告页跳转；支付宝沙箱同流程；防重复支付、订单超时过期、金额篡改防护 | 支付沙箱测试报告 | 阶段五 5.16-5.17 |
| 7.4 | 测试 | 降级方案验证：评分接口不可用时前端 FallbackScoring 本地计算、分享图生成失败降级纯文字链接、3D 人偶加载失败文字占位、职业数据库不可用不展示推荐 | 降级测试报告 | 阶段四 4.9、阶段五 5.4 |
| 7.5 | 测试 | 性能测试：首屏渲染 ≤ 2 秒（FCP）、答题切换 ≤ 200ms、评分接口响应 ≤ 1 秒、支付回调 ≤ 3 秒、分享图生成 ≤ 2 秒、首屏页面 ≤ 500KB、并发 500 QPS | 性能测试报告 | 阶段四-六全部开发 |
| 7.6 | 测试 | 兼容性测试：iOS Safari 14.0+、Chrome Android 90+、微信内置浏览器、支付宝内置浏览器、Firefox 88+、Edge 90+、IE 11 展示升级提示、PC 端布局居中（最大宽度 600px） | 兼容性测试矩阵 | 阶段四-六全部开发 |
| 7.7 | 测试 | 安全审计：全站 HTTPS + HSTS、CSRF 防护、Referer 校验、CSP 策略、XSS 转义、支付签名验证、敏感数据不记日志、限流 30 次/分钟 | 安全审计报告 | 阶段六 6.18 |
| 7.8 | 测试 | 30-50 人真实用户预测试：验证 6 点刻度版与标准 MBTI 信效度一致性 ≥ 80%、重测信度 ≥ 0.85、答题完成率 ≥ 60%、付费转化率 ≥ 5% | 预测试报告 | 7.1-7.4 |
| 7.9 | 需求侧 | 确认职业数据库交叉验证一致性 ≥ 70%（选取 30 个典型职业与 16Personalities/北森对比） | 职业数据库验证报告 | 阶段二 2.8 |

---

### 阶段八：部署上线

**阶段核心目标**：完成生产环境部署、SSL 配置、CDN 接入、监控告警

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 8.1 | 部署 | 配置生产环境服务器：MySQL 8.0 安装建库（`careertest`，charset=utf8mb4）、Redis 7.0 安装、Python 3.12 安装、venv 创建、依赖安装 | 生产环境服务器 | 阶段一 1.13 |
| 8.2 | 部署 | 配置 production.py settings：MySQL 连接（从环境变量读取）、Redis 缓存、DEBUG=False、ALLOWED_HOSTS（从环境变量解析）、SECRET_KEY（从环境变量） | production.py 最终配置 | 8.1 |
| 8.3 | 部署 | 执行 `migrate` 建表 + `loaddata` 加载初始数据（mbti_types.json/questions.json/careers.json）+ `collectstatic` 收集静态文件 | 生产数据库 + staticfiles/ | 8.2 |
| 8.4 | 部署 | 配置 Gunicorn（config/gunicorn.conf.py）：4 workers（CPU×2+1）、sync worker、timeout=30、max_requests=1000、preload_app=True、bind 127.0.0.1:8000 | `config/gunicorn.conf.py` | 8.1 |
| 8.5 | 部署 | 配置 Nginx（config/nginx.conf）：443 端口 SSL 证书、HTTP→HTTPS 301 重定向、静态文件 expires 30d + immutable、人偶图片代理 CDN、API 限流 30r/m per IP、HSTS 头部、proxy_pass → 127.0.0.1:8000 | `config/nginx.conf` | 8.4 |
| 8.6 | 部署 | 配置 Supervisord：管理 Gunicorn 进程，自动重启崩溃的 worker | `config/supervisord.conf` | 8.4 |
| 8.7 | 部署 | 接入 CDN：16 张 3D 人偶 WebP 图片上传至 OSS/七牛云、JS/CSS 文件上传、CDN 域名配置 | CDN 接入完成 | 阶段二 2.5 |
| 8.8 | 部署 | 配置 Celery worker + beat：启动 Celery worker 处理异步任务、启动 Celery beat 执行定时任务（4 个定时任务 + 1 个对账任务） | Celery worker + beat 运行 | 8.2、阶段六 6.16-6.17 |
| 8.9 | 部署 | 配置 SSL 证书：申请 Let's Encrypt 证书（certbot）或购买商业证书，配置自动续期 | SSL 证书 + 自动续期 | 8.5 |
| 8.10 | 部署 | 配置 Sentry 错误监控：接入 Sentry SDK，设置告警规则（Nginx 5xx > 1%、评分接口 > 2 秒/错误率 > 0.5%、支付回调连续 3 次失败、MySQL 连接 > 80%、Redis 内存 > 80%、磁盘 > 85%） | Sentry 接入 + 告警规则 | 8.2 |
| 8.11 | 部署 | 配置 UptimeRobot：每 5 分钟探测服务可用性，SLA 目标 99.5% | UptimeRobot 监控 | 8.5 |
| 8.12 | 部署 | 配置日志系统：logger 名 `careertest`，关键事件日志（score_request/score_success/score_failed/payment_success/payment_failed/orders_expired/reconciliation_mismatch/wechat_notify_verify_failed） | 日志配置 | 8.2 |
| 8.13 | 测试 | 生产环境冒烟测试：全流程走通（首页→答题→评分→结果→支付沙箱→报告）、所有 19 个 API 端点可访问、静态文件 CDN 加载正常、SSL 证书有效 | 冒烟测试报告 | 8.1-8.12 |
| 8.14 | 部署 | 配置支付回调地址：微信 notify_url = `https://careertest.example.com/payment/wechat/notify/`、支付宝 notify_url = `https://careertest.example.com/payment/alipay/notify/` | 支付回调配置 | 8.5、阶段一 1.10 |

---

### 阶段九：运营监控与首周复盘

**阶段核心目标**：上线后首周监控、1-2 所高校试点、数据复盘、迭代优化

| 序号 | 工作分类 | 具体落地任务 | 产出交付物 | 前置依赖 |
|:---:|---------|------------|----------|---------|
| 9.1 | 运维 | 首日监控：UV/PV、答题完成率、评分接口响应时间、支付成功率、错误日志、Redis/MySQL 资源使用 | 首日监控报告 | 阶段八全部完成 |
| 9.2 | 运维 | 设置日均 UV 上限告警：超 5000 触发成本评估（答题页纯前端 + CDN 缓解服务器压力） | UV 告警规则 | 9.1 |
| 9.3 | 需求侧 | 1-2 所高校就业指导群试点 1 周：提供免费深度报告供老师体验，收集反馈 | 试点反馈报告 | 阶段八全部完成 |
| 9.4 | 需求侧 | 首周数据复盘：对比冷启动基线指标（日均 UV ≥ 200、测评完成率 ≥ 60%、付费转化率 ≥ 5%、分享率 ≥ 10%、深度报告阅读完成率 ≥ 60%），低于基线启动对应优化 | 首周数据复盘报告 | 9.1 |
| 9.5 | 需求侧 | 启动定价 A/B 测试（若付费转化率 < 5%）：1.99 vs 2.99 vs 4.99，每组 500 UV | A/B 测试方案 | 9.4 |
| 9.6 | 运维 | 监控过程指标：答题中断率（识别流失高发题号）、职业推荐点击率（< 10% 触发数据库校准）、MBTI 类型分布（监控无人测出的类型）、极端作答率（> 15% 审查题目区分度） | 过程指标周报 | 9.1 |
| 9.7 | 运维 | 每日对账验证：确认 daily_reconciliation 任务正常运行，核对微信/支付宝流水与本地订单 | 对账报告 | 阶段八 8.8 |
| 9.8 | 需求侧 | 全量上线决策：试点 1 周后数据达标 → 全量上线；数据不达标 → 迭代优化后重新试点 | 全量上线决策书 | 9.3、9.4 |
| 9.9 | 运维 | 内容预热（全量上线前 1 周）：小红书 3 篇"我的人格认证卡"笔记、微信公众号 1 篇软文、知乎回答 MBTI/职业规划相关问题 | 内容预热物料 | 9.8 |
| 9.10 | 运维 | 增长飞轮启动：完成测评 → 分享认证卡 → 新用户点击链接进入 → 落地页 3 秒展示"开始测评" → 完成测评 → 分享循环 | 增长飞轮运行监控 | 9.8 |

---

## 阶段依赖关系图

```
阶段一（需求确认与前期准备）
  │
  ├──→ 阶段二（数据准备与素材制作）──────┐
  │                                      │
  └──→ 阶段三（基础设施搭建与初始化）←───┘
        │
        ├──→ 阶段四（核心测评模块开发）
        │      │
        │      └──→ 阶段五（结果页与支付模块）
        │             │
        │             └──→ 阶段六（深度报告与支撑功能）
        │                      │
        │                      └──→ 阶段七（测试与质量保障）
        │                               │
        │                               └──→ 阶段八（部署上线）
        │                                        │
        │                                        └──→ 阶段九（运营监控与复盘）
        │
        └──（阶段三~六可部分并行：数据制作与视觉素材与开发并行）
```

---

## 里程碑节点

| 里程碑 | 完成标志 | 对应阶段 |
|--------|---------|---------|
| M1 需求冻结 | PRD + TECH_DESIGN 评审通过、ICP 备案完成、支付资质到位 | 阶段一完成 |
| M2 数据就绪 | 48 题 + 16 型配置 + 80-120 职业 + 16 张人偶 + 认知功能栈映射表全部完成 | 阶段二完成 |
| M3 项目可运行 | Django 项目可启动、数据库建表完成、初始数据加载、基础页面可访问 | 阶段三完成 |
| M4 核心闭环 | 首页 → 答题 → 评分 → 职业匹配 全流程跑通 | 阶段四完成 |
| M5 商业闭环 | 结果页 → 支付 → 深度报告 → 分享 全流程跑通 | 阶段五完成 |
| M6 功能完备 | 7 项支撑功能 + SEO + 埋点 + Celery 定时任务 全部完成 | 阶段六完成 |
| M7 质量达标 | 全量测试通过、性能指标达标、安全审计通过、30-50 人预测试完成 | 阶段七完成 |
| M8 正式上线 | 生产环境部署完成、SSL 有效、CDN 接入、监控告警就绪、冒烟测试通过 | 阶段八完成 |
| M9 首周复盘 | 试点 1 周数据达标、全量上线决策完成、增长飞轮启动 | 阶段九完成 |
