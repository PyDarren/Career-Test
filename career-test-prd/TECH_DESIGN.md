# 职探 — 技术设计文档

**轻量化 MBTI 职业性格测评网页**

| 项目 | 说明 |
|------|------|
| 文档版本 | v1.2 |
| 创建日期 | 2026-07-09 |
| 关联文档 | PRD.md v3.5 |
| 技术栈 | Django 5.0 + MySQL 8.0 + Redis 7 + Nginx |
| 文档状态 | 评审稿 |

---

## 目录

- [系统架构](#系统架构)
- [技术选型](#技术选型)
- [视觉设计系统](#视觉设计系统)
- [数据库设计](#数据库设计)
- [Django 项目结构](#django-项目结构)
- [后端 API 设计](#后端-api-设计)
- [前端架构](#前端架构)
- [核心业务逻辑](#核心业务逻辑)
- [支付系统设计](#支付系统设计)
- [缓存策略](#缓存策略)
- [部署架构](#部署架构)
- [安全设计](#安全设计)
- [监控与告警](#监控与告警)
- [关键技术点](#关键技术点)
- [支撑系统设计](#支撑系统设计)

---

## 系统架构

### 整体架构图

```
┌──────────────────────────────────────────────────────┐
│                    用户（移动端浏览器）                  │
│              微信内置浏览器 / 支付宝内置浏览器              │
└──────────────┬───────────────────────────────────────┘
               │ HTTPS
               ▼
┌──────────────────────────────────────────────────────┐
│                    Nginx 反向代理                      │
│  · SSL 终止 · 静态文件分发 · 负载均衡 · 限流            │
└──────┬───────────────┬───────────────────────────────┘
       │               │
       ▼               ▼
┌──────────┐    ┌──────────────────────────────────────┐
│  CDN     │    │          Gunicorn (Django WSGI)        │
│ 静态资源  │    │   · 前端页面 · API 接口 · 评分计算     │
│ 人偶图片  │    │   · 支付回调 · 报告渲染                │
│ JS/CSS   │    └──────┬────────────┬──────────────────┘
└──────────┘           │            │
                       ▼            ▼
                 ┌──────────┐  ┌──────────┐
                 │  Redis   │  │  MySQL   │
                 │  缓存    │  │  持久化   │
                 │  会话    │  │  订单    │
                 │  限流    │  │  类型库  │
                 └──────────┘  └──────────┘
```

### 架构原则

- **无状态服务**：Gunicorn worker 不持有会话状态，所有会话数据存入 Redis，便于水平扩展
- **前后端不分离**：Django 模板渲染页面（SSR），减少前端 JS 体积，降低首屏加载时间
- **评分接口可降级**：后端评分接口不可用时，前端使用预置的简化评分规则本地计算维度级结果
- **答题数据不持久化**：答题刻度数据仅存浏览器 localStorage，提交评分后服务端不保存原始答案

---

## 技术选型

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| Web 框架 | Django | 5.0 LTS | 自带 ORM、模板引擎、中间件，开发效率高；内置 CSRF/XSS 防护 |
| 数据库 | MySQL | 8.0 | 成熟稳定、社区资源丰富；JSON 字段支持存储 mbti_ideal 等结构化数据 |
| 缓存 | Redis | 7.0 | 会话存储、评分结果缓存、限流计数器 |
| WSGI 服务器 | Gunicorn | 22.0 | 同步 worker 处理评分/支付，异步 worker 处理静态请求 |
| 反向代理 | Nginx | 1.24 | SSL 终止、静态文件分发、负载均衡、限流 |
| 前端 | Django 模板 + Vanilla JS | — | 不引入 Vue/React 等框架，首屏体积控制在 500KB 以内 |
| 图表 | ECharts | 5.5 | 维度倾向条形图、认知功能雷达图 |
| 支付 | 微信支付 SDK + 支付宝 SDK | V3 | 官方 Python SDK，服务端签名 |
| 任务队列 | Celery | 5.4 | 支付回调异步处理、数据统计定时任务（非 V1.0 必须） |
| 监控 | Sentry + 日志 | — | 错误追踪 + 业务日志 |
| Python | CPython | 3.12 | 性能提升，Django 5.0 最低要求 3.10+ |

---

## 视觉设计系统

参照 [16personalities.com](https://www.16personalities.com) 的视觉风格，建立职探的设计系统。16personalities 的核心设计语言是：紫色品牌主色 + 四角色组配色 + 卡片式布局 + 圆角 + 充足留白 + 温暖亲和的品牌个性。职探在此基础上融入认证卡设计。

### 色彩体系

```css
:root {
  /* 品牌主色 — 紫色系（参照 16personalities 品牌紫） */
  --color-primary: #4D3E8C;        /* 品牌紫 */
  --color-primary-light: #6B5BB3;  /* 浅紫 */
  --color-primary-dark: #2D1B69;   /* 深紫 */

  /* 四角色组配色（16personalities 核心编码系统） */
  --color-analyst: #8B5CF6;     /* 分析家（NT）紫色 */
  --color-diplomat: #4ADE80;    /* 外交家（NF）绿色 */
  --color-sentinel: #3B82F6;    /* 守护者（SJ）蓝色 */
  --color-explorer: #FACC15;    /* 探险家（SP）黄色 */

  /* 认证卡专用 */
  --color-card-bg: linear-gradient(135deg, #EDE9FE, #DDD6FE);  /* 浅紫渐变背景 */
  --color-badge: #FBBF24;       /* "已认证"徽章黄色 */
  --color-accent: #06B6D4;       /* 青色辅助色（双色挂签的青色端） */

  /* 中性色 */
  --color-bg: #FFFFFF;            /* 页面背景 */
  --color-surface: #F9FAFB;       /* 卡片表面 */
  --color-text: #1F2937;          /* 正文文字 */
  --color-text-muted: #6B7280;    /* 次要文字 */
  --color-border: #E5E7EB;        /* 边框 */
  --color-border-light: #F3F4F6;  /* 浅边框 */

  /* 功能色 */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;

  /* 6 点刻度渐变（A 侧紫 → B 侧青） */
  --color-scale-a-1: #4D3E8C;    /* 位置1 · 大圆 · 最深紫 */
  --color-scale-a-2: #6B5BB3;    /* 位置2 · 中圆 */
  --color-scale-a-3: #A78BFA;    /* 位置3 · 小圆 */
  --color-scale-b-1: #67E8F9;    /* 位置4 · 小圆 */
  --color-scale-b-2: #22D3EE;    /* 位置5 · 中圆 */
  --color-scale-b-3: #06B6D4;    /* 位置6 · 大圆 · 最深青 */
}
```

### 角色组配色映射

MBTI 16 型按 16personalities 的四角色分组着色，结果页、认证卡、维度条的颜色随用户类型动态切换：

| 角色组 | 成员 | 主题色 | CSS 变量 |
|--------|------|--------|---------|
| 分析家 | INTJ, INTP, ENTJ, ENTP | 紫色 | `--color-analyst` |
| 外交家 | INFJ, INFP, ENFJ, ENFP | 绿色 | `--color-diplomat` |
| 守护者 | ISTJ, ISFJ, ESTJ, ESFJ | 蓝色 | `--color-sentinel` |
| 探险家 | ISTP, ISFP, ESTP, ESFP | 黄色 | `--color-explorer` |

> Django 模板中通过 `mbti_type` 首字母判断角色组，在 `<body>` 上设置 `data-role="analyst|diplomat|sentinel|explorer"` 属性，CSS 通过 `[data-role="analyst"]` 选择器切换主题色。

### 字体排印

```css
:root {
  --font-sans: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei',
               -apple-system, 'Helvetica Neue', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --font-display: 'Noto Sans SC', 'PingFang SC', sans-serif;
}

/* 字号层级 */
--fs-hero: 48px;      /* 类型代码大字（渐变紫色） */
--fs-h1: 32px;
--fs-h2: 24px;
--fs-h3: 20px;
--fs-body: 16px;
--fs-small: 14px;
--fs-tiny: 12px;

/* 字重 */
--fw-regular: 400;
--fw-medium: 500;
--fw-bold: 700;
--fw-black: 900;
```

### 布局规范

| 规范 | 值 | 说明 |
|------|-----|------|
| 最大内容宽度 | 480px | 移动端优先，PC 端居中模拟手机宽度 |
| 卡片圆角 | 16px | 统一圆角，柔和视觉 |
| 按钮圆角 | 12px | — |
| 标签圆角 | 20px | 胶囊形标签 |
| 内边距 | 20px | 卡片内边距 |
| 区块间距 | 32px | 页面区块间垂直间距 |
| 字段间距 | 16px | 表单字段间垂直间距 |

### 组件样式

#### 按钮组件

```css
/* 主按钮 — 实心填充，参照 16personalities 风格 */
.btn-primary {
  background: var(--color-primary);
  color: #fff;
  padding: 14px 32px;
  border-radius: 12px;
  font-weight: var(--fw-bold);
  font-size: var(--fs-body);
  border: none;
  transition: all 0.2s ease;
}
.btn-primary:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(77, 62, 140, 0.3);
}

/* 次级按钮 — 描边幽灵样式 */
.btn-outline {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  padding: 12px 28px;
  border-radius: 12px;
  font-weight: var(--fw-medium);
}
```

#### 6 点刻度选择器

```css
/* 答题页 6 点刻度组件 */
.scale-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  gap: 8px;
}
.scale-dot {
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 3px solid var(--color-border);
}
.scale-dot.pos-1 { width: 36px; height: 36px; background: var(--color-scale-a-1); }
.scale-dot.pos-2 { width: 28px; height: 28px; background: var(--color-scale-a-2); }
.scale-dot.pos-3 { width: 20px; height: 20px; background: var(--color-scale-a-3); }
.scale-dot.pos-4 { width: 20px; height: 20px; background: var(--color-scale-b-1); }
.scale-dot.pos-5 { width: 28px; height: 28px; background: var(--color-scale-b-2); }
.scale-dot.pos-6 { width: 36px; height: 36px; background: var(--color-scale-b-3); }
.scale-dot.selected {
  transform: scale(1.3);
  box-shadow: 0 0 0 4px rgba(77, 62, 140, 0.2);
  border-color: var(--color-primary);
}
```

#### 维度倾向条

```css
/* 结果页四维度水平条形图 */
.dimension-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.dimension-bar-track {
  flex: 1;
  height: 24px;
  background: var(--color-surface);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}
.dimension-bar-fill {
  height: 100%;
  border-radius: 12px;
  transition: width 0.8s ease;
  /* 填充色随角色组变化 */
}
[data-role="analyst"] .dimension-bar-fill { background: var(--color-analyst); }
[data-role="diplomat"] .dimension-bar-fill { background: var(--color-diplomat); }
[data-role="sentinel"] .dimension-bar-fill { background: var(--color-sentinel); }
[data-role="explorer"] .dimension-bar-fill { background: var(--color-explorer); }
```

#### 人格认证卡

```css
/* 认证卡容器 — 渐变紫底 + 白色圆角卡片 */
.cert-card {
  background: var(--color-card-bg);
  border-radius: 24px;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(77, 62, 140, 0.12);
}
.cert-card-inner {
  background: #fff;
  border-radius: 20px;
  margin: 8px;
  padding: 32px 24px;
  position: relative;
}
/* 双色挂签 */
.cert-ribbon {
  position: absolute;
  top: 0;
  left: 24px;
  width: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.cert-ribbon-purple { flex: 1; background: var(--color-primary); }
.cert-ribbon-cyan { flex: 1; background: var(--color-accent); }
/* "已认证"徽章 */
.cert-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-badge);
  color: #fff;
  padding: 6px 16px;
  border-radius: 16px;
  font-size: var(--fs-small);
  font-weight: var(--fw-bold);
}
/* 类型代码 — 渐变紫色大字 */
.cert-type-code {
  font-size: var(--fs-hero);
  font-weight: var(--fw-black);
  background: linear-gradient(135deg, var(--color-primary-dark), var(--color-primary-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.05em;
}
```

### 动画规范

| 动画 | 时长 | 缓动函数 | 场景 |
|------|------|---------|------|
| 淡入 | 300ms | `ease-out` | 页面切换、结果卡出现 |
| 弹性放大 | 200ms | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 刻度圆点选中 |
| 条形填充 | 800ms | `ease-out` | 维度倾向条动画 |
| 卡片滑入 | 500ms | `ease-out` | 认证卡从底部滑入 |
| 进度条增长 | 300ms | `linear` | 答题进度条 |

---

## 数据库设计

### ER 概览

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  mbti_type  │     │  question    │     │  career          │
│  (16 行)    │     │  (48 行)     │     │  (80-120 行)     │
└──────┬──────┘     └──────────────┘     └────────┬────────┘
       │                                           │
       │              ┌──────────────┐              │
       └──────────────│  order       │──────────────┘
                      │  (订单表)     │
                      └──────┬───────┘
                             │
                      ┌──────┴───────┐
                      │  assessment   │
                      │  (测评记录)   │
                      └──────────────┘
```

### 表结构

#### `mbti_type` — MBTI 类型配置表

```sql
CREATE TABLE mbti_type (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    type_code       VARCHAR(4) NOT NULL UNIQUE,          -- 'ENFP'
    type_name       VARCHAR(32) NOT NULL,                 -- '竞选者'
    type_slogan     VARCHAR(64) NOT NULL,                 -- '活力四射的创意家'
    role_group      ENUM('analyst','diplomat','sentinel','explorer') NOT NULL,
    rarity          DECIMAL(5,2) NOT NULL,                -- 8.49
    rarity_label    VARCHAR(32) NOT NULL,                 -- '超受欢迎人格~'
    famous_people   JSON NOT NULL,                        -- ["罗宾·威廉姆斯","蕾哈娜"]
    best_partners   JSON NOT NULL,                        -- ["INTJ","INFJ","ENTJ"]
    romantic_matches JSON NOT NULL,                       -- ["INTP","ENTP","ENFP"]
    mascot_url      VARCHAR(256) NOT NULL,                -- CDN 地址
    type_description TEXT NOT NULL,                       -- 200-300 字简述
    cognitive_stack JSON NOT NULL,                        -- {"dominant":"Ne","auxiliary":"Fi","tertiary":"Te","inferior":"Si"}

    -- 深度报告内容模板（按章节存储，渲染时替换占位符）
    report_personality_analysis TEXT NOT NULL,            -- 第二章：人格特征分析
    report_strengths   JSON NOT NULL,                    -- 第五章：4 项优势
    report_weaknesses   JSON NOT NULL,                    -- 第六章：4 项劣势
    report_growth       JSON NOT NULL,                    -- 第七章：4 条成长建议
    report_cognitive    JSON NOT NULL,                    -- 第八章：荣格八维解读
    report_romance      TEXT NOT NULL,                    -- 第九章：恋爱专题
    report_romantic_matches JSON NOT NULL,                -- 第十章：3 个最佳恋爱对象
    report_career       JSON NOT NULL,                    -- 第十一章：职业专题
    report_career_list  JSON NOT NULL,                    -- 第十二章：按行业分类职业

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `question` — 量表题目表

```sql
CREATE TABLE question (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    question_order  INT NOT NULL UNIQUE,                  -- 题目顺序（1-48）
    dimension       ENUM('EI','SN','TF','JP') NOT NULL,    -- 所属维度
    facet           VARCHAR(32) NOT NULL,                 -- 面向名称（如 '社交能量'）
    facet_order     INT NOT NULL,                         -- 面向内序号（1-3）
    text_a          VARCHAR(256) NOT NULL,                -- A 极描述
    text_b          VARCHAR(256) NOT NULL,                -- B 极描述
    pole_a          VARCHAR(2) NOT NULL,                  -- A 极对应字母（如 'E'）
    pole_b          VARCHAR(2) NOT NULL,                  -- B 极对应字母（如 'I'）
    is_reverse      BOOLEAN DEFAULT FALSE,                -- 是否反向题
    display_order   INT NOT NULL,                         -- 展示顺序（打乱后）

    INDEX idx_dimension (dimension),
    INDEX idx_facet (dimension, facet_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `career` — 职业数据库

```sql
CREATE TABLE career (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    career_id       VARCHAR(16) NOT NULL UNIQUE,          -- 'CAREER_001'
    career_name     VARCHAR(64) NOT NULL,                 -- 'UI/UX 设计师'
    category        VARCHAR(32) NOT NULL,                 -- '互联网/产品'
    mbti_fit        JSON NOT NULL,                        -- ["ENFP","INFP","ENFJ","INFJ"]
    mbti_ideal      JSON NOT NULL,                        -- {"E":60,"S":30,"T":40,"J":30}
    cognitive_fit   JSON NOT NULL,                        -- ["Ne","Ni","Fi"]
    work_style      VARCHAR(256) NOT NULL,                -- 理想工作环境描述
    skill_required  JSON NOT NULL,                        -- ["创意设计","用户研究"]
    salary_range    VARCHAR(128) NOT NULL,                -- '应届 8-12K，1-3年 12-20K'
    growth_prospect VARCHAR(256) NOT NULL,                -- 发展前景描述
    description     TEXT NOT NULL,                        -- 职业简介
    match_tags      JSON NOT NULL,                        -- ["创意","审美"]

    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `assessment` — 测评记录表

```sql
CREATE TABLE assessment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    uuid            VARCHAR(36) NOT NULL,                  -- 浏览器生成的临时会话 ID
    browser_fingerprint VARCHAR(64),                      -- Canvas Fingerprint 哈希值
    mbti_type_code  VARCHAR(4) NOT NULL,                  -- 测评结果 'ENFP'
    dimension_scores JSON NOT NULL,                       -- {"EI":{"E":24,"I":12,"pct":33},...}
    facet_scores    JSON NOT NULL,                        -- 12 面向得分明细
    consistency_flag ENUM('normal','low_consistency','extreme_response') DEFAULT 'normal',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_uuid (uuid),
    INDEX idx_fingerprint (browser_fingerprint),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> 测评记录仅存储结果（类型代码 + 得分），不存储原始答题数据。原始刻度位置仅存浏览器 localStorage，提交评分后丢弃。

#### `order` — 支付订单表

```sql
CREATE TABLE order (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_no        VARCHAR(32) NOT NULL UNIQUE,          -- 订单号（UUID + 时间戳生成）
    uuid            VARCHAR(36) NOT NULL,                  -- 用户临时会话 ID
    assessment_id   BIGINT NOT NULL,                       -- 关联的测评记录
    amount          DECIMAL(6,2) NOT NULL DEFAULT 2.99,   -- 支付金额
    status          ENUM('pending','paid','failed','expired','refunded') DEFAULT 'pending',
    payment_method  ENUM('wechat','alipay') NULL,         -- 支付方式
    payment_id      VARCHAR(64),                          -- 第三方支付流水号
    paid_at         DATETIME NULL,                        -- 支付成功时间
    expires_at      DATETIME NOT NULL,                    -- 15 分钟后过期
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_uuid (uuid),
    INDEX idx_status (status),
    INDEX idx_order_no (order_no),
    FOREIGN KEY (assessment_id) REFERENCES assessment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Django 项目结构

```
careertest/
├── manage.py
├── requirements.txt
├── caretest/                     # 项目配置
│   ├── settings/
│   │   ├── base.py               # 基础配置
│   │   ├── development.py        # 开发环境
│   │   └── production.py         # 生产环境
│   ├── urls.py                   # 根路由
│   └── wsgi.py
├── apps/
│   ├── assessment/               # 测评模块
│   │   ├── models.py             # Question, Assessment
│   │   ├── views.py              # 测评页、评分接口
│   │   ├── scoring.py            # 评分算法（核心）
│   │   ├── urls.py
│   │   └── migrations/
│   ├── mbti_types/               # 类型配置模块
│   │   ├── models.py             # MBTIType
│   │   ├── views.py              # 类型数据接口
│   │   ├── urls.py
│   │   └── fixtures/             # 16 型初始数据 JSON
│   │       └── mbti_types.json
│   ├── careers/                  # 职业数据库模块
│   │   ├── models.py             # Career
│   │   ├── matching.py           # 职业匹配算法
│   │   ├── urls.py
│   │   └── fixtures/
│   │       └── careers.json      # 职业初始数据
│   ├── payment/                  # 支付模块
│   │   ├── models.py             # Order
│   │   ├── views.py              # 支付发起、回调
│   │   ├── wechat_pay.py         # 微信支付封装
│   │   ├── alipay_pay.py         # 支付宝封装
│   │   └── urls.py
│   └── stats/                    # 统计模块
│       ├── models.py
│       └── views.py              # 首页已完成人数等
├── templates/                    # Django 模板
│   ├── base.html                 # 基础模板（导航、页脚、CSS 引入）
│   ├── pages/
│   │   ├── home.html             # 首页
│   │   ├── assessment.html       # 答题页
│   │   ├── result.html           # 基础结果页（认证卡）
│   │   ├── report.html           # 深度报告页
│   │   └── payment.html          # 支付弹窗页
│   └── partials/
│       ├── cert_card.html        # 人格认证卡组件
│       ├── dimension_bars.html   # 维度倾向条组件
│       └── scale_selector.html   # 6 点刻度选择器组件
├── static/
│   ├── css/
│   │   └── main.css              # 主样式（含设计系统变量）
│   ├── js/
│   │   ├── assessment.js         # 答题交互（刻度选择、进度、localStorage）
│   │   ├── result.js             # 结果页交互（分享图 Canvas 合成）
│   │   └── payment.js            # 支付交互
│   ├── images/
│   │   └── mascots/              # 16 型 3D 人偶图片（WebP）
│   │       ├── INTJ.webp
│   │       ├── ENFP.webp
│   │       └── ...               # 16 张
│   └── libs/
│       └── echarts.min.js        # ECharts 图表库
└── config/
    ├── nginx.conf                # Nginx 配置
    ├── gunicorn.conf.py          # Gunicorn 配置
    └── supervisord.conf          # 进程管理
```

### Django settings 关键配置

```python
# caretest/settings/base.py

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'apps.assessment',
    'apps.mbti_types',
    'apps.careers',
    'apps.payment',
    'apps.stats',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 自定义限流中间件
    'apps.common.middleware.RateLimitMiddleware',
]

# 数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'careertest',
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Redis 缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# 会话（存入 Redis，不依赖 Cookie 中的 sessionid）
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = 86400 * 90  # 90 天

# 静态文件
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# 支付配置
WECHAT_PAY = {
    'app_id': os.environ['WECHAT_APP_ID'],
    'mch_id': os.environ['WECHAT_MCH_ID'],
    'api_key': os.environ['WECHAT_API_KEY'],
    'notify_url': 'https://careertest.example.com/payment/wechat/notify/',
}
ALIPAY = {
    'app_id': os.environ['ALIPAY_APP_ID'],
    'private_key': os.environ['ALIPAY_PRIVATE_KEY'],
    'notify_url': 'https://careertest.example.com/payment/alipay/notify/',
}
```

---

## 后端 API 设计

### API 总览

| 方法 | 路径 | 功能 | 认证 | 响应类型 |
|------|------|------|------|---------|
| GET | `/` | 首页 | 无 | HTML |
| GET | `/assessment/` | 答题页 | 无 | HTML |
| POST | `/api/score/` | 提交评分 | CSRF + Referer | JSON |
| GET | `/result/<uuid>/` | 基础结果页 | 无 | HTML |
| GET | `/api/mbti-type/<code>/` | 获取类型配置数据 | 无 | JSON |
| GET | `/api/careers/match/` | 获取职业匹配 | 无 | JSON |
| POST | `/api/payment/create/` | 创建支付订单 | CSRF | JSON |
| POST | `/payment/wechat/notify/` | 微信支付回调 | 签名验证 | XML |
| POST | `/payment/alipay/notify/` | 支付宝回调 | 签名验证 | JSON |
| GET | `/report/<order_no>/` | 深度报告页 | 订单状态校验 | HTML |
| GET | `/api/stats/completed-count/` | 已完成测评人数 | 无 | JSON |
| GET | `/api/order/status/<order_no>/` | 查询订单支付状态 | 无 | JSON |
| GET | `/api/history/<uuid>/` | 获取用户测评历史 | 无 | JSON |
| POST | `/api/feedback/` | 提交用户反馈 | CSRF | JSON |
| POST | `/api/customer-service/` | 提交客服留言 | CSRF | JSON |
| POST | `/api/report/recover/` | 凭订单号找回报告 | CSRF | JSON |
| GET | `/help/` | 帮助中心 | 无 | HTML |
| GET | `/settings/` | 设置页（数据清除） | 无 | HTML |

### 核心接口详细设计

#### POST `/api/score/` — 评分接口

```python
# 请求体
{
    "answers": [
        {"question_id": 1, "position": 3},
        {"question_id": 2, "position": 5},
        ...
    ],
    "uuid": "550e8400-e29b-41d4-a716-446655440000"
}

# 响应体（200）
{
    "mbti_type": "ENFP",
    "role_group": "diplomat",
    "dimensions": {
        "EI": {"pole": "E", "score_a": 24, "score_b": 12, "percentage": 33, "level": "中等倾向"},
        "SN": {"pole": "N", "score_a": 10, "score_b": 26, "percentage": 44, "level": "中等倾向"},
        "TF": {"pole": "F", "score_a": 12, "score_b": 24, "percentage": 33, "level": "中等倾向"},
        "JP": {"pole": "P", "score_a": 10, "score_b": 26, "percentage": 44, "level": "中等倾向"}
    },
    "facets": [
        {"dimension": "EI", "facet": "社交能量", "pole": "E", "score_a": 9, "score_b": 3, "percentage": 50},
        {"dimension": "EI", "facet": "注意力焦点", "pole": "I", "score_a": 3, "score_b": 9, "percentage": 50},
        ...
    ],
    "cognitive_stack": {
        "dominant": "Ne", "auxiliary": "Fi", "tertiary": "Te", "inferior": "Si"
    },
    "consistency_flag": "normal",
    "type_info": {
        "type_name": "竞选者",
        "type_slogan": "活力四射的创意家",
        "rarity": 8.49,
        "rarity_label": "超受欢迎人格~",
        "famous_people": ["罗宾·威廉姆斯", "蕾哈娜"],
        "best_partners": ["INTJ", "INFJ", "ENTJ"],
        "mascot_url": "https://cdn.example.com/mascots/ENFP.webp"
    },
    "recommended_careers": [
        {"career_name": "UI/UX 设计师", "match_score": 88, "category": "互联网/产品"},
        ...
    ],
    "assessment_id": 12345
}
```

```python
# apps/assessment/views.py

from django.views import View
from django.http import JsonResponse
from .scoring import ScoringEngine
from apps.mbti_types.models import MBTIType
from apps.careers.matching import CareerMatcher
import json, uuid as uuid_lib

class ScoreView(View):
    def post(self, request):
        data = json.loads(request.body)
        answers = data['answers']
        user_uuid = data['uuid']

        # 1. 评分计算
        engine = ScoringEngine()
        result = engine.calculate(answers)

        # 2. 查询类型配置
        mbti_type = MBTIType.objects.get(type_code=result['mbti_type'])

        # 3. 职业匹配
        matcher = CareerMatcher()
        careers = matcher.match(result['mbti_type'], result['dimensions'])

        # 4. 存储测评记录
        assessment = Assessment.objects.create(
            uuid=user_uuid,
            mbti_type_code=result['mbti_type'],
            dimension_scores=result['dimensions'],
            facet_scores=result['facets'],
            consistency_flag=result['consistency_flag'],
        )

        # 5. 返回完整结果
        return JsonResponse({
            'mbti_type': result['mbti_type'],
            'role_group': mbti_type.role_group,
            'dimensions': result['dimensions'],
            'facets': result['facets'],
            'cognitive_stack': result['cognitive_stack'],
            'consistency_flag': result['consistency_flag'],
            'type_info': mbti_type.to_dict(),
            'recommended_careers': careers[:5],
            'assessment_id': assessment.id,
        })
```

#### 评分引擎

```python
# apps/assessment/scoring.py

class ScoringEngine:
    """MBTI 48 题 6 点刻度评分引擎"""

    DIMENSION_MAX = 36  # 12 题 × 满分 3 = 36

    def calculate(self, answers):
        """
        answers: [{"question_id": 1, "position": 3}, ...]
        position: 1-6, 对应 A极3分 / A极2分 / A极1分 / B极1分 / B极2分 / B极3分
        """
        # 步骤 1-2: 题目计分 + 面向计分
        facet_results = self._score_facets(answers)

        # 步骤 3-4: 维度计分 + 倾向强度
        dimension_results = self._score_dimensions(facet_results)

        # 步骤 5-6: 类型判定 + 临界处理
        mbti_type = self._determine_type(dimension_results)

        # 步骤 7-9: 一致性检测
        consistency_flag = self._check_consistency(answers, facet_results)

        # 步骤 10: 认知功能推导
        cognitive_stack = self._derive_cognitive_stack(mbti_type)

        return {
            'mbti_type': mbti_type,
            'dimensions': dimension_results,
            'facets': facet_results,
            'cognitive_stack': cognitive_stack,
            'consistency_flag': consistency_flag,
        }

    def _position_to_score(self, position):
        """刻度位置 → 分值"""
        mapping = {1: (3, 'a'), 2: (2, 'a'), 3: (1, 'a'),
                  4: (1, 'b'), 5: (2, 'b'), 6: (3, 'b')}
        return mapping[position]

    def _score_facets(self, answers):
        """面向级计分：每个面向 4 题，统计 A/B 两端总分"""
        # 按面向分组，累加分值
        ...

    def _score_dimensions(self, facet_results):
        """维度级计分：3 个面向共 12 题，统计总分"""
        # 倾向百分比 = |A总分 - B总分| / 36 × 100%
        ...

    def _determine_type(self, dimension_results):
        """四字母类型判定，处理临界（X）"""
        ...

    def _check_consistency(self, answers, facet_results):
        """面向一致性 + 反向题一致性 + 极端作答检测"""
        ...

    def _derive_cognitive_stack(self, mbti_type):
        """查表推导认知功能栈"""
        stack_map = {
            'INTJ': {'dominant': 'Ni', 'auxiliary': 'Te', 'tertiary': 'Fi', 'inferior': 'Se'},
            'ENFP': {'dominant': 'Ne', 'auxiliary': 'Fi', 'tertiary': 'Te', 'inferior': 'Si'},
            # ... 完整 16 型
        }
        return stack_map.get(mbti_type, {})
```

#### 职业匹配算法

```python
# apps/careers/matching.py

import math
from .models import Career

class CareerMatcher:
    """职业匹配引擎"""

    NEIGHBOR_TYPES = {
        'INTJ': ['ENTJ', 'INFJ', 'INTP', 'ISTJ'],
        'ENFP': ['ESFP', 'ENFJ', 'ENTP', 'INFP'],
        # ... 16 型的相邻类型（仅一个维度不同）
    }

    def match(self, mbti_type, dimensions):
        """
        匹配度 = 类型直接匹配(0.6) + 维度强度匹配(0.4)
        """
        careers = Career.objects.all()
        results = []

        for career in careers:
            # 类型直接匹配
            type_score = self._type_match(mbti_type, career.mbti_fit)

            # 维度强度匹配（余弦相似度）
            strength_score = self._cosine_similarity(dimensions, career.mbti_ideal)

            # 加权
            final_score = type_score * 0.6 + strength_score * 0.4

            if final_score >= 50:  # 低于 50 不展示
                results.append({
                    'career_name': career.career_name,
                    'match_score': round(final_score),
                    'category': career.category,
                })

        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results

    def _type_match(self, user_type, fit_list):
        if user_type in fit_list:
            return 100
        neighbors = self.NEIGHBOR_TYPES.get(user_type, [])
        if any(n in fit_list for n in neighbors):
            return 70
        return 0

    def _cosine_similarity(self, user_dims, ideal_json):
        """用户四维度倾向百分比与职业理想画像的余弦相似度"""
        user_vec = [user_dims['EI']['percentage'],
                    user_dims['SN']['percentage'],
                    user_dims['TF']['percentage'],
                    user_dims['JP']['percentage']]
        ideal_vec = [ideal_json['E'], ideal_json['S'],
                     ideal_json['T'], ideal_json['J']]

        dot = sum(a * b for a, b in zip(user_vec, ideal_vec))
        norm_a = math.sqrt(sum(a ** 2 for a in user_vec))
        norm_b = math.sqrt(sum(b ** 2 for b in ideal_vec))

        if norm_a == 0 or norm_b == 0:
            return 0

        return (dot / (norm_a * norm_b)) * 100
```

#### 支付创建接口

```python
# apps/payment/views.py

class CreatePaymentView(View):
    def post(self, request):
        data = json.loads(request.body)
        assessment_id = data['assessment_id']
        uuid = data['uuid']
        method = data['method']  # 'wechat' or 'alipay'

        # 检查是否有未完成订单
        existing = Order.objects.filter(
            uuid=uuid, status='pending'
        ).first()
        if existing:
            existing.status = 'expired'
            existing.save()

        # 创建新订单
        order = Order.objects.create(
            order_no=self._gen_order_no(uuid),
            uuid=uuid,
            assessment_id=assessment_id,
            amount=Decimal('2.99'),
            status='pending',
            payment_method=method,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        # 调用支付 SDK 生成支付链接/二维码
        if method == 'wechat':
            pay_url = WechatPay.create_payment(order)
        else:
            pay_url = AlipayPay.create_payment(order)

        return JsonResponse({
            'order_no': order.order_no,
            'pay_url': pay_url,
            'amount': '2.99',
            'expires_in': 900,  # 15 分钟
        })
```

---

## 前端架构

### 页面交互流程

```
首页 (/)
  │
  ├── GET / → Django 渲染 home.html
  │
  ▼
答题页 (/assessment/)
  │
  ├── GET /assessment/ → Django 渲染 assessment.html
  ├── 前端 JS 从 /static/questions.json 加载题目（或内嵌在模板中）
  ├── 用户逐题答题，数据存 localStorage
  ├── 全部答完 → POST /api/score/
  │
  ▼
结果页 (/result/<uuid>/)
  │
  ├── POST /api/score/ 返回 JSON → 前端渲染认证卡
  │   或
  ├── GET /result/<uuid>/ → Django 渲染 result.html（SSR）
  │
  ├── 用户点击"解锁深度报告" → 弹出支付弹窗
  ├── POST /api/payment/create/ → 返回支付链接
  ├── 支付成功 → 跳转 /report/<order_no>/
  │
  ▼
报告页 (/report/<order_no>/)
  │
  ├── GET /report/<order_no>/ → Django 校验订单状态 → 渲染 report.html
  └── 报告内容从 mbti_type 表的 report_* 字段读取，模板替换占位符
```

### 关键前端 JS 模块

#### 答题交互 (`assessment.js`)

```javascript
// 核心逻辑：题目加载、刻度选择、进度管理、localStorage 存储

const Assessment = {
    questions: [],           // 题目数组
    currentIdx: 0,          // 当前题号
    answers: {},             // {question_id: position}

    init(questions) {
        this.questions = questions;
        this.currentIdx = 0;
        this.answers = this.loadProgress();
        this.render();
    },

    selectPosition(position) {
        const q = this.questions[this.currentIdx];
        this.answers[q.id] = position;

        // 每 5 题存一次
        if (Object.keys(this.answers).length % 5 === 0) {
            this.saveProgress();
        }

        // 300ms 后跳下一题
        setTimeout(() => this.next(), 300);
    },

    saveProgress() {
        const data = {
            answers: this.answers,
            currentIdx: this.currentIdx,
            timestamp: Date.now()
        };
        localStorage.setItem('assessment_progress', JSON.stringify(data));
    },

    loadProgress() {
        const saved = localStorage.getItem('assessment_progress');
        if (!saved) return {};
        const data = JSON.parse(saved);

        // 7 天过期检查
        if (Date.now() - data.timestamp > 7 * 86400000) {
            localStorage.removeItem('assessment_progress');
            return {};
        }
        return data.answers || {};
    },

    submit() {
        const uuid = localStorage.getItem('user_uuid') || this.genUUID();
        localStorage.setItem('user_uuid', uuid);

        fetch('/api/score/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                answers: Object.entries(this.answers).map(
                    ([qid, pos]) => ({question_id: parseInt(qid), position: pos})
                ),
                uuid: uuid
            })
        }).then(r => r.json()).then(data => {
            // 清除答题进度
            localStorage.removeItem('assessment_progress');
            // 跳转结果页
            window.location.href = `/result/${uuid}/?a=${data.assessment_id}`;
        });
    },

    genUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(
            /[xy]/g, c => {
                const r = Math.random() * 16 | 0;
                return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
            }
        );
    },

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
};
```

#### 分享图 Canvas 合成 (`result.js`)

```javascript
const ShareCard = {
    async generate(typeInfo) {
        const canvas = document.createElement('canvas');
        canvas.width = 750;
        canvas.height = 1334;  // 适配朋友圈图片尺寸
        const ctx = canvas.getContext('2d');

        // 1. 绘制渐变紫底背景
        const grad = ctx.createLinearGradient(0, 0, 750, 1334);
        grad.addColorStop(0, '#EDE9FE');
        grad.addColorStop(1, '#DDD6FE');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 750, 1334);

        // 2. 加载并绘制 3D 人偶图片
        const mascot = await this.loadImage(typeInfo.mascot_url);
        ctx.drawImage(mascot, 460, 200, 250, 250);

        // 3. 绘制类型代码（渐变紫色大字）
        ctx.font = 'bold 72px "Noto Sans SC"';
        ctx.fillStyle = '#4D3E8C';
        ctx.fillText(typeInfo.type_code, 60, 380);

        // 4. 绘制类型标语
        ctx.font = '28px "Noto Sans SC"';
        ctx.fillStyle = '#6B7280';
        ctx.fillText(typeInfo.type_slogan, 60, 430);

        // 5. 绘制稀有度
        ctx.font = 'bold 32px "Noto Sans SC"';
        ctx.fillStyle = '#4D3E8C';
        ctx.fillText(`稀有度 ${typeInfo.rarity}%`, 60, 520);

        // 6. 绘制产品二维码
        const qr = await this.loadImage('/static/images/qr-code.png');
        ctx.drawImage(qr, 60, 1100, 150, 150);

        // 7. 导出为图片
        return canvas.toDataURL('image/png');
    },

    loadImage(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = url;
        });
    }
};
```

---

## 核心业务逻辑

### 评分流程

```
用户提交 48 题答案（position 1-6）
    │
    ▼
ScoringEngine.calculate(answers)
    │
    ├── 1. 题目计分：position → (score, pole)
    │      1→(3,a) 2→(2,a) 3→(1,a) 4→(1,b) 5→(2,b) 6→(3,b)
    │
    ├── 2. 面向计分：4 题/面向，分别累加 A/B 两端
    │      → facet_results[12 条]
    │
    ├── 3. 维度计分：3 面向共 12 题，累加 A/B 总分
    │      → dimension_results[4 条]，满分 36
    │
    ├── 4. 倾向强度：|A-B| / 36 × 100%
    │
    ├── 5. 类型判定：较高端为类型字母
    │      临界(E==I) → X
    │
    ├── 6. 一致性检测：
    │      面向一致性 + 反向题一致性 + 极端作答
    │
    └── 7. 认知功能推导：查表 cognitive_stack_map[mbti_type]
         → {dominant, auxiliary, tertiary, inferior}
```

### 深度报告渲染

深度报告内容以模板形式存储在 `mbti_type` 表的 `report_*` 字段中，包含占位符（如 `{{dim_E_percentage}}`），Django 视图在渲染时替换为用户实际得分：

```python
# apps/payment/views.py

class ReportView(View):
    def get(self, request, order_no):
        order = get_object_or_404(Order, order_no=order_no, status='paid')
        assessment = order.assessment
        mbti_type = assessment.mbti_type_code
        type_config = MBTIType.objects.get(type_code=mbti_type)

        # 替换报告模板中的占位符
        report_content = self._render_report(
            type_config, assessment
        )

        return render(request, 'pages/report.html', {
            'report': report_content,
            'order': order,
            'type_config': type_config,
            'assessment': assessment,
        })

    def _render_report(self, type_config, assessment):
        """将类型模板中的占位符替换为用户实际得分"""
        import re
        content = {}
        scores = json.loads(assessment.dimension_scores)
        facets = json.loads(assessment.facet_scores)

        # 替换维度得分占位符
        for key, raw in type_config.report_personality_analysis.items():
            rendered = raw.replace(
                '{{dim_EI_percentage}}', str(scores['EI']['percentage'])
            ).replace(
                '{{dim_EI_pole}}', scores['EI']['pole']
            )
            # ... 其他维度占位符
            content[key] = rendered

        return content
```

---

## 支付系统设计

### 支付流程时序

```
用户              前端              Django            微信/支付宝
  │                │                 │                    │
  │ 点击"解锁"     │                 │                    │
  │───────────────>│                 │                    │
  │                │ POST /api/payment/create/           │
  │                │────────────────>│                    │
  │                │                 │ 创建 Order(pending)│
  │                │                 │ 调用支付 SDK       │
  │                │                 │───────────────────>│
  │                │                 │<───────────────────│
  │                │                 │ 返回支付链接/二维码 │
  │                │<────────────────│                    │
  │                │ 展示支付弹窗     │                    │
  │                │                 │                    │
  │ 完成支付       │                 │                    │
  │───────────────────────────────────────────────────────>│
  │                │                 │                    │
  │                │                 │<─────异步回调──────│
  │                │                 │ 验签 + 更新 Order   │
  │                │                 │ (status='paid')    │
  │                │                 │                    │
  │                │ 前端轮询订单状态  │                    │
  │                │ GET /api/order/status/              │
  │                │────────────────>│                    │
  │                │                 │ 返回 'paid'        │
  │                │<────────────────│                    │
  │                │ 跳转 /report/<order_no>/            │
  │                │                 │                    │
```

### 支付安全

```python
# apps/payment/wechat_pay.py

import hashlib, hmac, xml.etree.ElementTree as ET
from django.conf import settings

class WechatPay:
    @staticmethod
    def create_payment(order):
        """统一下单接口"""
        params = {
            'appid': settings.WECHAT_PAY['app_id'],
            'mch_id': settings.WECHAT_PAY['mch_id'],
            'nonce_str': order.order_no,
            'body': '职探 MBTI 深度报告',
            'out_trade_no': order.order_no,
            'total_fee': int(order.amount * 100),  # 分
            'notify_url': settings.WECHAT_PAY['notify_url'],
            'trade_type': 'NATIVE',  # 扫码支付
        }
        # 生成签名
        params['sign'] = WechatPay._sign(params)
        # 请求微信统一下单接口...
        return pay_url

    @staticmethod
    def verify_notify(notify_data):
        """验签回调"""
        sign = notify_data.get('sign')
        calculated = WechatPay._sign(notify_data)
        return hmac.compare_digest(sign, calculated)

    @staticmethod
    def _sign(params):
        """MD5 签名"""
        sorted_params = sorted(
            [(k, v) for k, v in params.items() if v and k != 'sign']
        )
        sign_str = '&'.join(f'{k}={v}' for k, v in sorted_params)
        sign_str += f'&key={settings.WECHAT_PAY["api_key"]}'
        return hashlib.md5(sign_str.encode()).hexdigest().upper()
```

---

## 缓存策略

| 缓存对象 | 存储位置 | TTL | 失效策略 |
|---------|---------|-----|---------|
| MBTI 类型配置（16 条） | Redis | 24h | 数据更新时主动清除 |
| 职业数据库（80-120 条） | Redis | 24h | 数据更新时主动清除 |
| 评分结果（相同答案组合） | Redis | 1h | 自然过期 |
| 已完成测评人数 | Redis | 5min | 定时刷新 |
| 题目列表（48 题） | Redis | 永久 | 题目更新时清除 |
| 限流计数器 | Redis | 1min | 自然过期 |

```python
# 评分结果缓存示例
from django.core.cache import cache

class ScoreView(View):
    def post(self, request):
        # 生成答案指纹
        answer_key = '-'.join(
            f"{a['question_id']}:{a['position']}" for a in answers
        )
        cache_key = f'score:{hashlib.md5(answer_key.encode()).hexdigest()}'

        cached = cache.get(cache_key)
        if cached:
            cached['assessment_id'] = self._create_assessment(cached, uuid)
            return JsonResponse(cached)

        # 评分计算...
        cache.set(cache_key, result, 3600)  # 1 小时
```

---

## 部署架构

### 生产环境部署

```
┌─────────────────────────────────────────────────┐
│              云服务器 (2C4G 起步)                │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Nginx (1 进程)                        │   │
│  │  · 443 端口 · SSL 证书 · 静态文件分发   │   │
│  │  · 反向代理 → 127.0.0.1:8000            │   │
│  │  · 限流：30 req/min per IP              │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  Gunicorn (4 workers)                   │   │
│  │  · 127.0.0.1:8000                       │   │
│  │  · Django WSGI app                      │   │
│  └──────┬──────────────────┬───────────────┘   │
│         │                  │                    │
│  ┌──────▼──────┐  ┌──────▼──────┐              │
│  │  Redis      │  │  MySQL      │              │
│  │  127.0.0.1  │  │  127.0.0.1  │              │
│  │  6379       │  │  3306       │              │
│  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────┘
         │
         │ CDN
         ▼
┌─────────────────┐
│  OSS / 七牛云     │
│  · 人偶图片       │
│  · JS/CSS 文件   │
└─────────────────┘
```

### Gunicorn 配置

```python
# config/gunicorn.conf.py

bind = '127.0.0.1:8000'
workers = 4                 # CPU 核数 × 2 + 1
worker_class = 'sync'       # 同步 worker（评分/支付需要同步处理）
timeout = 30                # 请求超时
keepalive = 5
max_requests = 1000         # 防止内存泄漏
max_requests_jitter = 50
preload_app = True          # 预加载应用，减少 worker 启动时间
accesslog = '-'
errorlog = '-'
loglevel = 'warning'
```

### Nginx 配置

```nginx
# config/nginx.conf

server {
    listen 443 ssl http2;
    server_name careertest.example.com;

    ssl_certificate     /etc/ssl/certs/careertest.pem;
    ssl_certificate_key /etc/ssl/private/careertest.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 静态文件
    location /static/ {
        alias /opt/careertest/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 人偶图片代理到 CDN
    location /mascots/ {
        proxy_pass https://cdn.example.com/mascots/;
        expires 30d;
    }

    # API 限流
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
    }

    # 其他请求
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name careertest.example.com;
    return 301 https://$server_name$request_uri;
}

# 限流区域定义
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
```

---

## 安全设计

### 限流中间件

```python
# apps/common/middleware.py

from django.core.cache import cache
from django.http import JsonResponse
import time

class RateLimitMiddleware:
    """IP 维度限流：评分/支付接口 30 次/分钟"""
    RATE_LIMIT = 30
    WINDOW = 60  # 秒

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            ip = self._get_client_ip(request)
            key = f'ratelimit:{ip}'
            count = cache.get(key, 0)
            if count >= self.RATE_LIMIT:
                return JsonResponse(
                    {'error': '请求过于频繁，请稍后再试'},
                    status=429
                )
            cache.set(key, count + 1, self.WINDOW)
        return self.get_response(request)

    def _get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

### Referer 校验

```python
# 评分和支付接口校验 Referer，防止跨站调用
class ScoreView(View):
    def post(self, request):
        referer = request.META.get('HTTP_REFERER', '')
        if 'careertest.example.com' not in referer:
            return JsonResponse({'error': '非法请求来源'}, status=403)
        # ... 正常处理
```

### CSP 策略

```python
# settings/base.py

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # 允许内联脚本
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "cdn.example.com", "data:")
CSP_CONNECT_SRC = ("'self'",)
```

---

## 监控与告警

### 监控项

| 监控对象 | 指标 | 告警阈值 | 告警方式 |
|---------|------|---------|---------|
| Nginx | 5xx 错误率 | > 1% | Sentry + 邮件 |
| Gunicorn | worker 状态 | worker 崩溃 | Supervisord 自动重启 |
| 评分接口 | 响应时间 | > 2 秒 | Sentry 性能监控 |
| 评分接口 | 错误率 | > 0.5% | Sentry + 邮件 |
| 支付回调 | 回调失败 | 连续 3 次失败 | Sentry + 短信 |
| MySQL | 连接数 | > 80% 最大连接 | 邮件 |
| Redis | 内存使用 | > 80% | 邮件 |
| 磁盘 | 使用率 | > 85% | 邮件 |

### 日志规范

```python
# 业务日志记录
import logging
logger = logging.getLogger('careertest')

class ScoreView(View):
    def post(self, request):
        logger.info('score_request', extra={
            'uuid': uuid,
            'answer_count': len(answers),
            'ip': self._get_client_ip(request),
        })

        try:
            result = engine.calculate(answers)
            logger.info('score_success', extra={
                'uuid': uuid,
                'mbti_type': result['mbti_type'],
                'duration_ms': elapsed_ms,
            })
        except Exception as e:
            logger.error('score_failed', extra={
                'uuid': uuid,
                'error': str(e),
            })
            raise
```

---

## 关键技术点

### 浏览器指纹与会话标识

用户免注册是产品的核心卖点，但支付流程需要标识用户身份。系统通过浏览器指纹 + UUID 的双重标识方案，在无需收集个人信息的前提下完成支付追溯。

#### Canvas Fingerprint 生成

```python
# apps/common/fingerprint.py
# 后端接收前端生成的 Canvas 指纹哈希值，不自行生成

import hashlib

def store_fingerprint(fingerprint_raw: str, uuid: str):
    """
    前端通过 Canvas API 生成设备指纹字符串后，
    将原始值发送至后端，后端仅存储 SHA-256 哈希值
    """
    fingerprint_hash = hashlib.sha256(fingerprint_raw.encode()).hexdigest()
    # 存入 Redis，关联 UUID，90 天过期
    cache.set(f'fp:{fingerprint_hash}', uuid, 86400 * 90)
    return fingerprint_hash
```

```javascript
// static/js/fingerprint.js — 前端 Canvas 指纹生成

function generateCanvasFingerprint() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 200;
    canvas.height = 50;

    // 绘制一段带有特定字体和颜色的文字
    // 不同设备、浏览器、显卡驱动渲染结果存在微小差异
    ctx.textBaseline = 'top';
    ctx.font = "14px 'Arial'";
    ctx.fillStyle = '#f60';
    ctx.fillRect(0, 0, 100, 30);
    ctx.fillStyle = '#069';
    ctx.fillText('CareerTest_fp_2026', 2, 2);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('CareerTest_fp_2026', 4, 4);

    // 提取像素数据并生成哈希
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const hash = simpleHash(imageData.data);
    return hash;
}

function simpleHash(data) {
    // 将像素数据转为简洁哈希字符串
    let str = '';
    for (let i = 0; i < data.length; i += 4096) {
        str += data[i].toString(16);
    }
    return str.substring(0, 64);
}
```

> 指纹方案仅用于关联同一设备的多次测评记录和支付订单，不用于跨站追踪。用户清除浏览器数据后指纹关联即失效。指纹哈希值 90 天后自动从 Redis 清除。

### 6 点刻度评分引擎

48 题 × 6 点刻度的评分逻辑是系统的核心算法。以下为完整实现：

```python
# apps/assessment/scoring.py

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Answer:
    question_id: int
    position: int          # 1-6

@dataclass
class FacetResult:
    dimension: str         # 'EI'
    facet_name: str        # '社交能量'
    pole: str              # 'E' or 'I'
    score_a: int           # A 极总分（1-12）
    score_b: int           # B 极总分（1-12）
    percentage: float      # |A-B| / 12 * 100

@dataclass
class DimensionResult:
    dimension: str         # 'EI'
    pole: str              # 'E' or 'I' or 'X'（临界）
    score_a: int           # A 极总分（1-36）
    score_b: int           # B 极总分（1-36）
    percentage: float      # |A-B| / 36 * 100
    level: str             # '明显倾向' / '中等倾向' / '轻微倾向'
    facets: List[FacetResult] = field(default_factory=list)


POSITION_MAP = {
    1: (3, 'a'),   # 位置1 → A极 +3
    2: (2, 'a'),   # 位置2 → A极 +2
    3: (1, 'a'),   # 位置3 → A极 +1
    4: (1, 'b'),   # 位置4 → B极 +1
    5: (2, 'b'),   # 位置5 → B极 +2
    6: (3, 'b'),   # 位置6 → B极 +3
}

DIMENSION_MAX = 36  # 12 题 × 3 分 = 36

# 认知功能栈配置表（16 型完整映射）
COGNITIVE_STACK_MAP = {
    'INTJ': {'dominant': 'Ni', 'auxiliary': 'Te', 'tertiary': 'Fi', 'inferior': 'Se'},
    'INTP': {'dominant': 'Ti', 'auxiliary': 'Ne', 'tertiary': 'Si', 'inferior': 'Fe'},
    'ENTJ': {'dominant': 'Te', 'auxiliary': 'Ni', 'tertiary': 'Se', 'inferior': 'Fi'},
    'ENTP': {'dominant': 'Ne', 'auxiliary': 'Ti', 'tertiary': 'Fe', 'inferior': 'Si'},
    'INFJ': {'dominant': 'Ni', 'auxiliary': 'Fe', 'tertiary': 'Ti', 'inferior': 'Se'},
    'INFP': {'dominant': 'Fi', 'auxiliary': 'Ne', 'tertiary': 'Si', 'inferior': 'Te'},
    'ENFJ': {'dominant': 'Fe', 'auxiliary': 'Ni', 'tertiary': 'Se', 'inferior': 'Ti'},
    'ENFP': {'dominant': 'Ne', 'auxiliary': 'Fi', 'tertiary': 'Te', 'inferior': 'Si'},
    'ISTJ': {'dominant': 'Si', 'auxiliary': 'Te', 'tertiary': 'Fi', 'inferior': 'Ne'},
    'ISFJ': {'dominant': 'Si', 'auxiliary': 'Fe', 'tertiary': 'Ti', 'inferior': 'Ne'},
    'ESTJ': {'dominant': 'Te', 'auxiliary': 'Si', 'tertiary': 'Ne', 'inferior': 'Fi'},
    'ESFJ': {'dominant': 'Fe', 'auxiliary': 'Si', 'tertiary': 'Ne', 'inferior': 'Ti'},
    'ISTP': {'dominant': 'Ti', 'auxiliary': 'Se', 'tertiary': 'Ni', 'inferior': 'Fe'},
    'ISFP': {'dominant': 'Fi', 'auxiliary': 'Se', 'tertiary': 'Ni', 'inferior': 'Te'},
    'ESTP': {'dominant': 'Se', 'auxiliary': 'Ti', 'tertiary': 'Fe', 'inferior': 'Ni'},
    'ESFP': {'dominant': 'Se', 'auxiliary': 'Fi', 'tertiary': 'Te', 'inferior': 'Ni'},
}


class ScoringEngine:

    def calculate(self, answers: List[Answer], questions: List[dict]) -> dict:
        # 构建题目索引 {question_id: question_meta}
        q_map = {q['id']: q for q in questions}

        # 步骤 1-2: 题目计分 + 面向计分
        facet_groups = defaultdict(lambda: {'a': 0, 'b': 0, 'details': []})
        for ans in answers:
            q = q_map[ans.question_id]
            score, pole = POSITION_MAP[ans.position]
            facet_key = (q['dimension'], q['facet'])
            facet_groups[facet_key][pole] += score
            facet_groups[facet_key]['details'].append({
                'question_id': ans.question_id,
                'position': ans.position,
                'score': score,
                'pole': pole,
                'is_reverse': q.get('is_reverse', False),
            })

        facet_results = self._build_facet_results(facet_groups, q_map)

        # 步骤 3-4: 维度计分 + 倾向强度
        dim_results = self._score_dimensions(facet_results)

        # 步骤 5-6: 类型判定 + 临界处理
        mbti_type = self._determine_type(dim_results)

        # 步骤 7-9: 一致性检测
        consistency = self._check_consistency(answers, facet_results, dim_results)

        # 步骤 10: 认知功能推导
        cognitive_stack = COGNITIVE_STACK_MAP.get(mbti_type, {})

        return {
            'mbti_type': mbti_type,
            'dimensions': {d.dimension: self._dim_to_dict(d) for d in dim_results},
            'facets': [self._facet_to_dict(f) for f in facet_results],
            'cognitive_stack': cognitive_stack,
            'consistency_flag': consistency,
        }

    def _build_facet_results(self, groups, q_map):
        results = []
        for (dim, facet), data in sorted(groups.items()):
            a, b = data['a'], data['b']
            pole = self._pole_from_scores(a, b, q_map, dim)
            pct = abs(a - b) / 12 * 100
            results.append(FacetResult(dim, facet, pole, a, b, pct))
        return results

    def _score_dimensions(self, facets: List[FacetResult]) -> List[DimensionResult]:
        dim_map = defaultdict(lambda: {'a': 0, 'b': 0, 'facets': []})
        for f in facets:
            dim_map[f.dimension]['a'] += f.score_a
            dim_map[f.dimension]['b'] += f.score_b
            dim_map[f.dimension]['facets'].append(f)

        results = []
        for dim, data in sorted(dim_map.items()):
            a, b = data['a'], data['b']
            pct = abs(a - b) / DIMENSION_MAX * 100
            pole = 'X' if a == b else (self._dim_pole_letter(dim, a, b))
            level = self._level_from_pct(pct)
            results.append(DimensionResult(dim, pole, a, b, pct, level, data['facets']))
        return results

    def _determine_type(self, dims: List[DimensionResult]) -> str:
        code = ''
        for d in dims:
            code += d.pole if d.pole != 'X' else 'X'
        # 临界处理：X 标记保留，报告中提示
        return code

    def _check_consistency(self, answers, facet_results, dim_results):
        flags = []

        # 面向一致性检测
        for dim in dim_results:
            facet_poles = [f.pole for f in dim.facets]
            unique_poles = set(p for p in facet_poles if p != 'X')
            if len(unique_poles) >= 3 or (len(unique_poles) == 2 and 'X' in facet_poles):
                flags.append('low_consistency')

        # 极端作答检测：连续 8 题以上选位置 1 或 6
        positions = [a.position for a in answers]
        consecutive_extreme = 0
        max_consecutive = 0
        for p in positions:
            if p in (1, 6):
                consecutive_extreme += 1
                max_consecutive = max(max_consecutive, consecutive_extreme)
            else:
                consecutive_extreme = 0
        if max_consecutive >= 8:
            flags.append('extreme_response')

        if flags:
            return flags[0]
        return 'normal'

    def _level_from_pct(self, pct):
        if pct >= 50:
            return '明显倾向'
        elif pct >= 25:
            return '中等倾向'
        return '轻微倾向'

    def _dim_pole_letter(self, dim, a, b):
        """根据维度和得分返回类型字母"""
        letter_map = {'EI': ('E', 'I'), 'SN': ('S', 'N'),
                      'TF': ('T', 'F'), 'JP': ('J', 'P')}
        a_letter, b_letter = letter_map[dim]
        return a_letter if a > b else b_letter

    def _pole_from_scores(self, a, b, q_map, dim):
        if a == b:
            return 'X'
        return self._dim_pole_letter(dim, a, b)

    def _dim_to_dict(self, d):
        return {'pole': d.pole, 'score_a': d.score_a, 'score_b': d.score_b,
                'percentage': round(d.percentage, 1), 'level': d.level}

    def _facet_to_dict(self, f):
        return {'dimension': f.dimension, 'facet': f.facet_name, 'pole': f.pole,
                'score_a': f.score_a, 'score_b': f.score_b,
                'percentage': round(f.percentage, 1)}
```

### 支付安全体系

支付是系统中唯一涉及资金流转的环节，安全等级最高。以下从六个维度构建完整的支付安全防线。

#### 1. 订单防篡改

订单金额、关联测评记录、用户标识均在服务端生成，前端不参与金额计算。攻击者即使篡改前端请求参数，也无法影响实际扣款金额。

```python
# apps/payment/views.py

from django.core.exceptions import ValidationError

class CreatePaymentView(View):
    def post(self, request):
        data = json.loads(request.body)
        assessment_id = data['assessment_id']
        uuid = data['uuid']
        method = data['method']

        # 金额完全由服务端决定，不从前端读取
        amount = Decimal('2.99')

        # 校验 assessment_id 是否属于该 UUID
        assessment = Assessment.objects.filter(
            id=assessment_id, uuid=uuid
        ).first()
        if not assessment:
            return JsonResponse(
                {'error': '测评记录不存在或不属于当前用户'},
                status=403
            )

        # 检查是否已有已完成（paid）的订单
        paid_order = Order.objects.filter(
            uuid=uuid, assessment_id=assessment_id, status='paid'
        ).exists()
        if paid_order:
            return JsonResponse(
                {'error': '该测评已解锁，请直接查看报告'},
                status=400
            )

        # 过期旧订单
        Order.objects.filter(
            uuid=uuid, status='pending'
        ).update(status='expired')

        # 创建订单
        order = Order.objects.create(
            order_no=self._gen_order_no(uuid),
            uuid=uuid,
            assessment_id=assessment_id,
            amount=amount,                    # 服务端硬编码金额
            status='pending',
            payment_method=method,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        # 调用支付 SDK，金额取自 order.amount（非前端传入）
        if method == 'wechat':
            pay_url = WechatPay.create_payment(order)
        else:
            pay_url = AlipayPay.create_payment(order)

        return JsonResponse({
            'order_no': order.order_no,
            'pay_url': pay_url,
            'amount': str(order.amount),      # 仅展示用途
            'expires_in': 900,
        })

    def _gen_order_no(self, uuid):
        """生成订单号：时间戳 + UUID 短哈希 + 随机数"""
        ts = timezone.now().strftime('%Y%m%d%H%M%S')
        uuid_hash = hashlib.md5(uuid.encode()).hexdigest()[:8]
        rand = secrets.token_hex(4)
        return f'CT{ts}{uuid_hash}{rand}'
```

#### 2. 回调验签

支付回调是资金确认的唯一入口，必须验证请求确实来自微信/支付宝官方服务器。通过 API V3 的 RSA 签名校验和证书自动更新，防止伪造回调。

```python
# apps/payment/wechat_pay.py

import json
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from django.conf import settings
from django.core.cache import cache
import requests

class WechatPay:
    """
    微信支付 V3 API 封装
    使用 RSA-SHA256 签名 + 平台证书自动下载与缓存
    """

    BASE_URL = 'https://api.mch.weixin.qq.com/v3'

    @classmethod
    def verify_notify(cls, headers, body):
        """
        V3 回调验签流程：
        1. 从 Wechatpay-Signature 头提取签名值
        2. 从 Wechatpay-Serial 头提取平台证书序列号
        3. 获取对应的微信平台公钥（自动下载并缓存）
        4. 用公钥验证签名（RSA-SHA256）
        5. 验证通过后解密回调体中的 resource.ciphertext
        """
        signature = headers.get('Wechatpay-Signature', '')
        serial = headers.get('Wechatpay-Serial', '')
        timestamp = headers.get('Wechatpay-Timestamp', '')
        nonce = headers.get('Wechatpay-Nonce', '')

        # 拼接验签字符串
        sign_str = f'{timestamp}\n{nonce}\n{body}\n'

        # 获取平台证书公钥
        public_key = cls._get_platform_cert(serial)

        # RSA-SHA256 验签
        try:
            sig_bytes = base64.b64decode(signature)
            public_key.verify(
                sig_bytes,
                sign_str.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    @classmethod
    def _get_platform_cert(cls, serial):
        """
        从 Redis 缓存获取平台证书公钥；
        缓存未命中时从微信 API 下载并缓存
        """
        cache_key = f'wechat_cert:{serial}'
        cert_pem = cache.get(cache_key)

        if not cert_pem:
            # 从微信 API 下载平台证书列表
            certs = cls._download_platform_certs()
            for s, pem in certs.items():
                cache.set(f'wechat_cert:{s}', pem, 86400 * 12)  # 12 小时
            cert_pem = certs.get(serial)

        if not cert_pem:
            raise ValueError(f'平台证书 {serial} 不存在')

        cert = load_pem_x509_certificate(cert_pem.encode())
        return cert.public_key()

    @classmethod
    def _download_platform_certs(cls):
        """从微信 API 下载平台证书（需用商户私钥签名请求）"""
        # 构造签名请求 → GET /certificates
        # 解析返回的证书列表，提取 serial 和公钥
        # 实际实现省略
        ...

    @classmethod
    def decrypt_resource(cls, ciphertext, nonce, associated_data):
        """
        V3 回调中 resource.ciphertext 是 AES-256-GCM 加密的
        需要用 APIv3 密钥解密后才能获取订单信息
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        api_key = settings.WECHAT_PAY['api_key'].encode('utf-8')
        nonce_bytes = nonce.encode('utf-8')
        ciphertext_bytes = base64.b64decode(ciphertext)
        associated_data_bytes = associated_data.encode('utf-8')

        aesgcm = AESGCM(api_key)
        plaintext = aesgcm.decrypt(
            nonce_bytes, ciphertext_bytes, associated_data_bytes
        )
        return json.loads(plaintext.decode('utf-8'))
```

```python
# apps/payment/views.py — 回调处理视图

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def wechat_notify(request):
    """
    微信支付回调
    幂等处理：同一订单的多次回调只处理一次
    """
    body = request.body.decode('utf-8')
    headers = {k: v for k, v in request.headers.items()}

    # 1. 验签
    if not WechatPay.verify_notify(headers, body):
        logger.warning('wechat_notify_verify_failed', extra={
            'ip': request.META.get('REMOTE_ADDR'),
        })
        return HttpResponse(
            json.dumps({'code': 'FAIL', 'message': '验签失败'}),
            content_type='application/json',
            status=401
        )

    # 2. 解密回调内容
    notify_data = json.loads(body)
    resource = WechatPay.decrypt_resource(
        notify_data['resource']['ciphertext'],
        notify_data['resource']['nonce'],
        notify_data['resource']['associated_data'],
    )

    order_no = resource['out_trade_no']
    trade_status = resource['trade_state']
    trade_no = resource.get('transaction_id', '')

    # 3. 幂等处理
    with transaction.atomic():
        order = Order.objects.select_for_update().get(order_no=order_no)

        if order.status == 'paid':
            # 已处理过的回调，直接返回成功
            return HttpResponse(
                json.dumps({'code': 'SUCCESS', 'message': '成功'}),
                content_type='application/json'
            )

        if trade_status == 'SUCCESS':
            order.status = 'paid'
            order.payment_id = trade_no
            order.paid_at = timezone.now()
            order.save()

            logger.info('payment_success', extra={
                'order_no': order_no,
                'amount': str(order.amount),
                'trade_no': trade_no,
            })

            return HttpResponse(
                json.dumps({'code': 'SUCCESS', 'message': '成功'}),
                content_type='application/json'
            )
        else:
            order.status = 'failed'
            order.save()

            logger.warning('payment_failed', extra={
                'order_no': order_no,
                'trade_status': trade_status,
            })

            return HttpResponse(
                json.dumps({'code': 'SUCCESS', 'message': '已记录失败状态'}),
                content_type='application/json'
            )
```

#### 3. 防重复支付

通过数据库唯一约束和订单状态机，防止同一用户对同一测评重复支付。

```python
# 订单状态机
# pending → paid      （支付成功）
# pending → failed    （支付失败）
# pending → expired   （15 分钟超时）
# paid → refunded     （退款）

# 数据库层防重
class Order(models.Model):
    # ...
    class Meta:
        constraints = [
            # 同一 assessment 只允许一个 paid 订单
            models.UniqueConstraint(
                fields=['assessment_id'],
                condition=models.Q(status='paid'),
                name='unique_paid_order_per_assessment'
            )
        ]

# 应用层防重：创建订单前检查
def check_existing_order(uuid, assessment_id):
    """同一 UUID + assessment 不允许同时存在两个 pending 订单"""
    pending = Order.objects.filter(
        uuid=uuid, assessment_id=assessment_id, status='pending'
    ).first()
    if pending and pending.expires_at > timezone.now():
        # 返回已有订单而非创建新订单
        return pending
    return None
```

#### 4. 订单超时与资金对账

订单 15 分钟自动过期，防止用户长时间挂起支付。每日凌晨自动对账，核对支付平台流水与服务端订单状态。

```python
# apps/stats/tasks.py — Celery 定时任务

from celery import shared_task
from apps.payment.models import Order
from apps.payment.wechat_pay import WechatPay

@shared_task
def expire_pending_orders():
    """每 5 分钟将超时 pending 订单标记为 expired"""
    expired_count = Order.objects.filter(
        status='pending',
        expires_at__lt=timezone.now()
    ).update(status='expired')

    if expired_count > 0:
        logger.info('orders_expired', extra={'count': expired_count})


@shared_task
def daily_reconciliation():
    """
    每日凌晨 2 点执行对账
    1. 拉取微信/支付宝前一天的交易流水
    2. 与本地 paid 订单逐一核对
    3. 标记不一致的订单（漏单/多单）
    """
    # 拉取微信支付日账单
    wechat_bills = WechatPay.query_daily_bills(yesterday)

    for bill in wechat_bills:
        order_no = bill['out_trade_no']
        trade_status = bill['trade_state']

        try:
            order = Order.objects.get(order_no=order_no)
            if order.status == 'paid' and trade_status != 'SUCCESS':
                # 本地已支付但支付平台显示未成功 → 异常
                logger.error('reconciliation_mismatch', extra={
                    'order_no': order_no,
                    'local_status': order.status,
                    'remote_status': trade_status,
                })
                # 发送告警
            elif order.status != 'paid' and trade_status == 'SUCCESS':
                # 本地未支付但支付平台显示已成功 → 漏单
                order.status = 'paid'
                order.payment_id = bill['transaction_id']
                order.paid_at = bill['success_time']
                order.save()
                logger.warning('reconciliation_missed_order', extra={
                    'order_no': order_no,
                })
        except Order.DoesNotExist:
            logger.error('reconciliation_unknown_order', extra={
                'order_no': order_no,
            })
```

```python
# Celery Beat 定时任务配置
# caretest/settings/base.py

CELERY_BEAT_SCHEDULE = {
    'expire-pending-orders': {
        'task': 'apps.stats.tasks.expire_pending_orders',
        'schedule': 300.0,  # 每 5 分钟
    },
    'daily-reconciliation': {
        'task': 'apps.stats.tasks.daily_reconciliation',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨 2 点
    },
}
```

#### 5. 金额一致性保障

从前端到支付平台，金额经过三次传递：服务端生成 → 支付 SDK 提交 → 支付平台扣款。每一环节都需校验金额一致。

```python
# 金额校验三道防线

# 防线 1: 创建订单时，金额由服务端硬编码
amount = Decimal('2.99')  # 不接受前端传入的金额

# 防线 2: 调用支付 SDK 时，金额取自数据库记录
# 而非创建时传入的变量
order = Order.objects.get(order_no=order_no)
# 微信支付传参时取 order.amount
params['total_fee'] = int(order.amount * 100)  # 分

# 防线 3: 回调验签通过后，校验回调金额与订单金额一致
if Decimal(resource['amount']['total']) / 100 != order.amount:
    logger.error('amount_mismatch', extra={
        'order_no': order_no,
        'expected': str(order.amount),
        'actual': str(Decimal(resource['amount']['total']) / 100),
    })
    # 拒绝确认支付，人工介入
    return
```

#### 6. 前端支付状态轮询

支付完成后支付平台通过异步回调通知服务端，但回调存在延迟（通常 1–5 秒）。前端需轮询订单状态，在回调到达后自动跳转报告页。

```python
# apps/payment/views.py — 订单状态查询接口

class OrderStatusView(View):
    def get(self, request):
        order_no = request.GET.get('order_no')
        order = Order.objects.filter(order_no=order_no).first()

        if not order:
            return JsonResponse({'error': '订单不存在'}, status=404)

        return JsonResponse({
            'status': order.status,
            'paid': order.status == 'paid',
            'report_url': f'/report/{order.order_no}/' if order.status == 'paid' else None,
        })
```

```javascript
// static/js/payment.js — 前端轮询逻辑

const PaymentPoller = {
    pollInterval: null,
    maxAttempts: 60,       // 最多轮询 60 次
    intervalMs: 2000,      // 每 2 秒轮询一次
    attempts: 0,

    start(orderNo, onSuccess, onTimeout) {
        this.attempts = 0;
        this.pollInterval = setInterval(() => {
            this._poll(orderNo, onSuccess, onTimeout);
        }, this.intervalMs);
    },

    _poll(orderNo, onSuccess, onTimeout) {
        this.attempts++;
        if (this.attempts > this.maxAttempts) {
            clearInterval(this.pollInterval);
            onTimeout();
            return;
        }

        fetch(`/api/order/status/?order_no=${orderNo}`)
            .then(r => r.json())
            .then(data => {
                if (data.paid) {
                    clearInterval(this.pollInterval);
                    onSuccess(data.report_url);
                }
            })
            .catch(err => {
                console.error('Poll error:', err);
            });
    },

    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
};

// 使用方式
PaymentPoller.start(
    orderNo,
    (reportUrl) => {
        // 支付成功，跳转报告页
        window.location.href = reportUrl;
    },
    () => {
        // 轮询超时（2 分钟内未收到回调）
        // 展示"支付确认中，如已扣款请联系客服"
        showPaymentPendingNotice();
    }
);
```

### 前端降级方案

当后端评分接口不可用时，前端使用预置的简化评分规则本地计算维度级结果（不含面向分析和认知功能推导），确保用户至少能看到 MBTI 类型和维度倾向。

```javascript
// static/js/fallback_scoring.js — 前端降级评分

const FallbackScoring = {
    /**
     * 简化评分：将 6 点刻度简化为 2 级迫选
     * position 1-3 → A 极 +1
     * position 4-6 → B 极 +1
     * 分母为 12（非 36），精度降低但类型判定一致
     */
    calculate(answers, questions) {
        const dimScores = { EI: {a: 0, b: 0}, SN: {a: 0, b: 0},
                           TF: {a: 0, b: 0}, JP: {a: 0, b: 0} };
        const dimLetters = { EI: ['E', 'I'], SN: ['S', 'N'],
                           TF: ['T', 'F'], JP: ['J', 'P'] };

        answers.forEach(ans => {
            const q = questions.find(q => q.id === ans.question_id);
            const dim = q.dimension;
            const pole = ans.position <= 3 ? 'a' : 'b';
            dimScores[dim][pole] += 1;
        });

        let mbtiType = '';
        const dimensions = {};

        Object.keys(dimScores).forEach(dim => {
            const a = dimScores[dim].a;
            const b = dimScores[dim].b;
            const letters = dimLetters[dim];
            const pole = a > b ? letters[0] : (b > a ? letters[1] : 'X');
            const pct = Math.abs(a - b) / 12 * 100;
            mbtiType += pole;
            dimensions[dim] = {
                pole: pole,
                percentage: Math.round(pct * 10) / 10,
                level: pct >= 50 ? '明显倾向' : pct >= 25 ? '中等倾向' : '轻微倾向'
            };
        });

        return {
            mbti_type: mbtiType,
            dimensions: dimensions,
            facets: null,              // 降级模式无面向分析
            cognitive_stack: null,     // 降级模式无认知功能推导
            consistency_flag: 'normal',
            degraded: true             // 标记为降级结果
        };
    }
};
```

### 深度报告模板渲染

深度报告 12 章内容以模板形式存储在 `mbti_type` 表中，使用 Jinja2 风格的占位符。渲染时根据用户实际得分替换占位符，实现"同一类型模板 + 不同得分数据 = 个性化报告"。

```python
# apps/assessment/report_renderer.py

import re
import json
from apps.mbti_types.models import MBTIType

class ReportRenderer:
    """
    深度报告渲染器
    将类型模板中的占位符替换为用户实际得分
    """

    def render(self, type_config: MBTIType, assessment) -> dict:
        scores = json.loads(assessment.dimension_scores)
        facets = json.loads(assessment.facet_scores)
        cognitive = json.loads(assessment.cognitive_stack) \
            if isinstance(assessment.cognitive_stack, str) \
            else assessment.cognitive_stack

        # 构建占位符上下文
        ctx = self._build_context(scores, facets, cognitive)

        report = {}
        # 逐章渲染
        report['personality_analysis'] = self._replace(
            type_config.report_personality_analysis, ctx
        )
        report['strengths'] = self._render_list(
            json.loads(type_config.report_strengths), ctx
        )
        report['weaknesses'] = self._render_list(
            json.loads(type_config.report_weaknesses), ctx
        )
        report['growth'] = self._render_list(
            json.loads(type_config.report_growth), ctx
        )
        report['cognitive'] = self._render_list(
            json.loads(type_config.report_cognitive), ctx
        )
        report['romance'] = self._replace(
            type_config.report_romance, ctx
        )
        report['romantic_matches'] = self._render_list(
            json.loads(type_config.report_romantic_matches), ctx
        )
        report['career'] = self._render_list(
            json.loads(type_config.report_career), ctx
        )
        # 职业推荐列表无需渲染（直接从 career 表读取）
        report['career_list'] = json.loads(type_config.report_career_list)

        return report

    def _build_context(self, scores, facets, cognitive):
        """构建占位符 → 实际值的映射"""
        ctx = {}
        for dim, data in scores.items():
            ctx[f'dim_{dim}_percentage'] = data['percentage']
            ctx[f'dim_{dim}_pole'] = data['pole']
            ctx[f'dim_{dim}_level'] = data['level']
            ctx[f'dim_{dim}_score_a'] = data['score_a']
            ctx[f'dim_{dim}_score_b'] = data['score_b']

        # 面向级占位符
        for f in facets:
            key = f'facet_{f["dimension"]}_{f["facet"]}'
            ctx[f'{key}_pole'] = f['pole']
            ctx[f'{key}_percentage'] = f['percentage']

        # 认知功能占位符
        for role, func in cognitive.items():
            ctx[f'cog_{role}'] = func  # e.g. cog_dominant = 'Ne'

        return ctx

    def _replace(self, text: str, ctx: dict) -> str:
        """替换 {{placeholder}} 格式的占位符"""
        def replacer(match):
            key = match.group(1).strip()
            return str(ctx.get(key, match.group(0)))
        return re.sub(r'\{\{(\w+)\}\}', replacer, text)

    def _render_list(self, items: list, ctx: dict) -> list:
        """渲染列表中的每个元素的文本"""
        return [
            {k: self._replace(v, ctx) if isinstance(v, str) else v
             for k, v in item.items()}
            for item in items
        ]
```

```python
# 模板存储示例（mbti_type 表中的 report_strengths 字段）
[
    {
        "title": "策略能力",
        "content": "你的 Ni（内向直觉）得分对应 {{dim_EI_percentage}}% 的倾向强度，使你不仅能提前计划好行动方案，而且时刻做好准备，根据可能出现的各种情况准备多套计划。你的 {{cog_dominant}} 主导功能让你以广阔的、以未来为中心的视野来识别可能性和潜力。"
    },
    {
        "title": "创新",
        "content": "虽然你可能表面上看起来很难对付，但你实际上非常乐于接受并支持变革和创新。你的 {{cog_auxiliary}} 辅助功能使你能够跳出概念简单理论化的困境，将想法落实为能对世界产生真正影响的行动。"
    }
]
```

---

## 支撑系统设计

本章节覆盖核心测评流程之外但工程实现所需的支撑模块：统一错误处理、Celery 定时任务、前端埋点方案、LocalStorage 管理规范、新增接口设计。

### 统一 API 错误响应格式

所有 `/api/` 开头的 JSON 接口遵循统一错误响应结构，前端通过 `code` 字段做差异化处理：

```python
# apps/common/responses.py

from django.http import JsonResponse

class APIError(Exception):
    """统一 API 错误基类"""
    def __init__(self, code, message, http_status=400, extra=None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}

def api_error_response(api_error: APIError):
    return JsonResponse({
        'success': False,
        'code': api_error.code,
        'message': api_error.message,
        'extra': api_error.extra,
    }, status=api_error.http_status)

def api_success_response(data, extra=None):
    return JsonResponse({
        'success': True,
        'code': 0,
        'data': data,
        'extra': extra or {},
    })
```

| code | 含义 | 触发场景 | 前端处理 |
|------|------|---------|---------|
| 0 | 成功 | 正常响应 | 正常处理 data |
| 1001 | 参数缺失/格式错误 | 请求体缺少必填字段 | 提示"请求异常，请刷新重试" |
| 1002 | 答案数据不合法 | answers 数组长度 ≠ 48 或 position 不在 1–6 | 提示"答题数据异常，请重新测评" |
| 1003 | UUID 格式不合法 | uuid 不符合 UUID4 格式 | 前端重新生成 UUID |
| 2001 | 订单不存在 | order_no 在数据库中未找到 | 提示"订单不存在，请确认订单号" |
| 2002 | 订单已过期 | 订单状态为 expired 或创建超 15 分钟 | 提示"订单已过期，请重新发起支付" |
| 2003 | 订单已支付 | 重复创建支付请求 | 直接跳转报告页 |
| 3001 | 反馈提交频率超限 | 同一用户同一结果页已提交过反馈 | 提示"已收到你的反馈，感谢" |
| 4001 | 评分服务降级中 | Redis 不可用或评分引擎异常 | 前端切换降级评分模式 |
| 5001 | 服务器内部错误 | 未捕获异常 | 提示"服务暂时不可用，请稍后重试" |

```python
# apps/common/middleware.py

import logging
from django.http import JsonResponse
from .responses import APIError, api_error_response

logger = logging.getLogger('careertest.api')

class ExceptionMiddleware:
    """全局异常捕获中间件，将未处理异常转为统一 JSON 响应"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except APIError as e:
            return api_error_response(e)
        except Exception as e:
            logger.exception(f'Unhandled exception: {e}')
            return api_error_response(
                APIError(5001, '服务暂时不可用，请稍后重试', 500)
            )
```

### Celery 定时任务

```python
# careertest/celery.py

from celery import Celery
from django.conf import settings

app = Celery('careertest')
app.config_from_object(settings, namespace='CELERY')
app.autodiscover_tasks()

@app.on_after_configure.connect
def setup_scheduled_tasks(sender, **kwargs):
    from celery.schedules import crontab

    # 每分钟检查过期订单
    sender.add_periodic_task(
        60.0,
        'expire_pending_orders',
        name='expire-pending-orders',
    )

    # 每天凌晨 2:00 清理过期测评记录
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        'cleanup_old_assessments',
        name='cleanup-old-assessments',
    )

    # 每天凌晨 3:00 生成日报数据
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        'generate_daily_stats',
        name='generate-daily-stats',
    )

    # 每小时刷新已完成测评人数缓存
    sender.add_periodic_task(
        3600.0,
        'refresh_completed_count',
        name='refresh-completed-count',
    )
```

```python
# apps/stats/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from apps.payment.models import Order
from apps.assessment.models import Assessment

@shared_task
def expire_pending_orders():
    """将超时未支付订单标记为 expired"""
    expired = Order.objects.filter(
        status='pending',
        expires_at__lt=timezone.now(),
    )
    count = expired.update(status='expired')
    if count:
        logger.info(f'Expired {count} pending orders')

@shared_task
def cleanup_old_assessments():
    """清理超过 30 天的测评记录（仅保留类型代码用于统计）"""
    cutoff = timezone.now() - timedelta(days=30)
    Assessment.objects.filter(
        created_at__lt=cutoff
    ).exclude(
        orders__status='paid'  # 保留有付费订单的测评
    ).delete()

@shared_task
def refresh_completed_count():
    """刷新已完成测评人数缓存"""
    count = Assessment.objects.count()
    cache.set('stats:completed_count', count, 3600)

@shared_task
def generate_daily_stats():
    """生成日报数据，写入 stats_daily 表"""
    today = timezone.now().date()
    # 聚合当天数据：UV、完成数、付费数、收入等
    ...
```

| 任务 | 频率 | 说明 |
|------|------|------|
| `expire_pending_orders` | 每分钟 | 将超时（15 分钟）的 pending 订单标记为 expired |
| `cleanup_old_assessments` | 每天 02:00 | 清理 30 天前的未付费测评记录（付费记录依法保留） |
| `refresh_completed_count` | 每小时 | 刷新 Redis 中已完成测评人数缓存 |
| `generate_daily_stats` | 每天 03:00 | 聚合前一天的 UV/完成率/付费数/收入，写入日报表 |

### 前端埋点方案

```python
# apps/common/tracking.py

"""
前端埋点方案：通过统一事件上报接口收集用户行为数据，
用于计算 PRD 中定义的过程指标（完成率、中断率、分享率等）。
"""

TRACKING_EVENTS = {
    # 页面访问
    'page_view':        {'path': 'str', 'ref': 'str(optional)'},
    # 测评行为
    'assessment_start': {},
    'assessment_answer': {'question_idx': 'int', 'position': 'int', 'time_spent': 'int(ms)'},
    'assessment_pause':  {'question_idx': 'int'},
    'assessment_resume':  {'question_idx': 'int', 'via': 'continue|restart'},
    'assessment_submit':  {'total_time': 'int(s)', 'answer_count': 'int'},
    # 结果行为
    'result_view':       {'mbti_type': 'str'},
    'career_click':      {'career_id': 'str', 'match_score': 'int'},
    'career_feedback':   {'career_id': 'str', 'feedback_type': 'str'},
    'share_click':       {'mbti_type': 'str'},
    'share_success':     {'mbti_type': 'str'},
    # 支付行为
    'payment_click':     {'mbti_type': 'str'},
    'payment_success':   {'order_no': 'str', 'amount': 'str', 'method': 'str'},
    'payment_fail':      {'order_no': 'str', 'reason': 'str'},
    # 报告行为
    'report_view':       {'order_no': 'str'},
    'report_scroll':     {'chapter': 'int'},
    'report_feedback':   {'rating': 'up|down'},
    # 回流行为
    'referral_landing': {'ref_type': 'str', 'ref_mbti': 'str(optional)'},
}
```

```python
# apps/stats/views.py

class TrackingView(View):
    """前端埋点上报接口 POST /api/track/"""

    def post(self, request):
        data = json.loads(request.body)
        events = data.get('events', [])

        for event in events:
            event_name = event.get('name')
            event_data = event.get('data', {})
            uuid = data.get('uuid')

            # 写入 tracking 表或 Redis（高频事件先入 Redis，低频事件直接入库）
            if event_name in ('assessment_answer',):  # 高频事件
                cache.lpush(
                    f'track:{uuid}',
                    json.dumps({
                        'name': event_name,
                        'data': event_data,
                        'ts': int(time.time()),
                    })
                )
            else:  # 低频事件直接入库
                TrackingEvent.objects.create(
                    uuid=uuid,
                    event_name=event_name,
                    event_data=event_data,
                )

        return JsonResponse({'success': True})
```

```javascript
// 前端埋点 SDK（tracking.js）

const Tracker = {
    queue: [],

    track(eventName, data = {}) {
        const uuid = localStorage.getItem('user_uuid') || 'anonymous';
        this.queue.push({
            name: eventName,
            data: data,
            ts: Date.now(),
        });
        // 批量上报：每 5 条或页面隐藏时发送
        if (this.queue.length >= 5) {
            this.flush();
        }
    },

    flush() {
        if (this.queue.length === 0) return;
        const uuid = localStorage.getItem('user_uuid') || 'anonymous';
        const events = this.queue.splice(0);

        // 使用 sendBeacon 确保页面关闭时也能上报
        if (navigator.sendBeacon) {
            const blob = new Blob(
                [JSON.stringify({uuid, events})],
                {type: 'application/json'}
            );
            navigator.sendBeacon('/api/track/', blob);
        } else {
            fetch('/api/track/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uuid, events}),
                keepalive: true,
            });
        }
    },

    init() {
        // 页面隐藏时批量上报
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) this.flush();
        });
        // 页面卸载前上报
        window.addEventListener('beforeunload', () => this.flush());
    }
};
```

| 指标 | 所需埋点事件 | 计算公式 |
|------|-------------|---------|
| 测评完成率 | `assessment_start` / `assessment_submit` | submit_count / start_count |
| 答题中断率 | `assessment_pause` + `assessment_answer` 时间分布 | pause_count / start_count |
| 付费转化率 | `result_view` / `payment_click` / `payment_success` | payment_success / result_view |
| 分享率 | `result_view` / `share_click` | share_click / result_view |
| 分享回流率 | `referral_landing` / `page_view` | referral_landing / page_view |
| 平均答题时长 | `assessment_start.ts` / `assessment_submit.ts` | (submit_ts - start_ts) / submit_count |
| 职业推荐点击率 | `result_view` / `career_click` | career_click / result_view |

### LocalStorage 管理规范

```python
# 前端 LocalStorage 存储键名规范
# 所有键名以 'ct_' 前缀避免与其他网站冲突

LOCALSTORAGE_KEYS = {
    'ct_uuid': {
        'value': '用户 UUID（随机生成）',
        'ttl': '永久（除非用户手动清除）',
        'size': '36 bytes',
    },
    'ct_assessment_progress': {
        'value': '答题进度（answers + currentIdx + timestamp）',
        'ttl': '7 天（超时自动清除）',
        'size': '~2 KB',
    },
    'ct_last_result': {
        'value': '最近一次测评结果缓存（mbti_type + dimensions）',
        'ttl': '会话级（关闭浏览器后清除）',
        'size': '~4 KB',
    },
    'ct_paid_reports': {
        'value': '已购报告订单号列表 [{order_no, mbti_type, paid_at}]',
        'ttl': '永久（90 天后由前端标记过期）',
        'size': '~1 KB',
    },
    'ct_referrer_type': {
        'value': '分享来源参数（ref + type + name）',
        'ttl': '会话级',
        'size': '~200 bytes',
    },
    'ct_settings': {
        'value': '用户设置（如隐私声明已读标记）',
        'ttl': '永久',
        'size': '~100 bytes',
    },
}
```

| 键名 | 写入时机 | 读取时机 | 清除时机 |
|------|---------|---------|---------|
| `ct_uuid` | 首次访问时生成 | 所有 API 请求时携带 | 用户手动清除或数据清除功能 |
| `ct_assessment_progress` | 每 5 题自动保存 | 进入答题页时检查恢复 | 完成测评或选择重新开始或超 7 天 |
| `ct_last_result` | 评分成功后写入 | 返回结果页时读取 | 关闭浏览器或数据清除功能 |
| `ct_paid_reports` | 支付成功后写入 | 访问报告页前检查 | 超过 90 天的记录标记过期 |
| `ct_referrer_type` | 从分享链接进入时写入 | 首页加载时读取引导卡片 | 会话结束 |

### 新增接口详细设计

#### GET `/api/order/status/<order_no>/` — 订单状态查询

```python
# apps/payment/views.py

class OrderStatusView(View):
    def get(self, request, order_no):
        order = get_object_or_404(Order, order_no=order_no)
        return JsonResponse({
            'order_no': order.order_no,
            'status': order.status,  # pending / paid / expired / failed
            'amount': str(order.amount),
            'payment_method': order.payment_method,
            'created_at': order.created_at.isoformat(),
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
        })
```

前端轮询逻辑（每 2 秒查询一次，持续 2 分钟后超时）：

```javascript
const PaymentPoller = {
    start(orderNo, onSuccess, onTimeout) {
        this.orderNo = orderNo;
        this.attempts = 0;
        this.maxAttempts = 60;  // 2 分钟 / 2 秒 = 60 次
        this.timer = setInterval(() => this.poll(onSuccess, onTimeout), 2000);
    },

    async poll(onSuccess, onTimeout) {
        this.attempts++;
        try {
            const res = await fetch(`/api/order/status/${this.orderNo}/`);
            const data = await res.json();
            if (data.status === 'paid') {
                this.stop();
                onSuccess(data);
            } else if (data.status === 'expired' || data.status === 'failed') {
                this.stop();
                onTimeout(data);
            }
        } catch (e) {
            console.error('Poll error:', e);
        }
        if (this.attempts >= this.maxAttempts) {
            this.stop();
            onTimeout({status: 'timeout'});
        }
    },

    stop() {
        clearInterval(this.timer);
    }
};
```

#### GET `/api/history/<uuid>/` — 测评历史

```python
# apps/assessment/views.py

class HistoryView(View):
    def get(self, request, uuid):
        assessments = Assessment.objects.filter(
            uuid=uuid
        ).order_by('-created_at')[:3]  # 最多保留 3 条

        history = []
        for a in assessments:
            history.append({
                'assessment_id': a.id,
                'mbti_type': a.mbti_type_code,
                'created_at': a.created_at.isoformat(),
                'dimensions': json.loads(a.dimension_scores),
            })

        return JsonResponse({
            'history': history,
            'count': len(history),
        })
```

#### POST `/api/feedback/` — 用户反馈

```python
# apps/stats/views.py

class FeedbackView(View):
    def post(self, request):
        data = json.loads(request.body)
        uuid = data['uuid']

        # 防重复：同一用户同一 assessment 只能提交 1 次反馈
        existing = Feedback.objects.filter(
            uuid=uuid,
            assessment_id=data.get('assessment_id'),
        ).exists()
        if existing:
            return api_error_response(
                APIError(3001, '已收到你的反馈，感谢')
            )

        Feedback.objects.create(
            uuid=uuid,
            assessment_id=data.get('assessment_id'),
            order_no=data.get('order_no'),
            mbti_type=data.get('mbti_type'),
            feedback_type=data.get('type'),  # career_mismatch / career_partial / report_rating / report_text
            career_id=data.get('career_id'),
            rating=data.get('rating'),  # up / down
            content=data.get('content', '')[:200],  # 限制 200 字
        )

        return api_success_response({'submitted': True})
```

#### POST `/api/report/recover/` — 凭订单号找回报告

```python
# apps/payment/views.py

class ReportRecoverView(View):
    def post(self, request):
        data = json.loads(request.body)
        order_no = data.get('order_no')

        try:
            order = Order.objects.get(order_no=order_no, status='paid')
        except Order.DoesNotExist:
            return api_error_response(
                APIError(2001, '订单不存在或未支付')
            )

        # 检查是否在有效期内
        if order.paid_at:
            days_since = (timezone.now() - order.paid_at).days
            if days_since > 90:
                return api_error_response(
                    APIError(2002, '报告已过期，需重新测评并购买')
                )

        # 返回新 UUID 关联的 assessment_id，前端重新写入 localStorage
        return api_success_response({
            'order_no': order.order_no,
            'assessment_id': order.assessment_id,
            'mbti_type': order.assessment.mbti_type_code,
            'report_url': f'/report/{order.order_no}/',
        })
```

### 数据库表补充

新增支撑功能所需的数据表：

```sql
-- 用户反馈表
CREATE TABLE feedback (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL,
    assessment_id BIGINT,
    order_no VARCHAR(64),
    mbti_type VARCHAR(4) NOT NULL,
    feedback_type ENUM('career_mismatch', 'career_partial', 'report_rating', 'report_text') NOT NULL,
    career_id VARCHAR(20),
    rating ENUM('up', 'down'),
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_uuid (uuid),
    INDEX idx_assessment (assessment_id),
    INDEX idx_career (career_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 客服留言表
CREATE TABLE customer_service_message (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36),
    contact VARCHAR(100),          -- 微信号或手机号（选填）
    message TEXT NOT NULL,         -- 问题描述（必填，限 500 字）
    order_no VARCHAR(64),          -- 相关订单号（选填）
    status ENUM('pending', 'replied', 'closed') DEFAULT 'pending',
    reply TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    replied_at DATETIME,
    INDEX idx_uuid (uuid),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 前端埋点事件表（低频事件直接入库）
CREATE TABLE tracking_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL,
    event_name VARCHAR(50) NOT NULL,
    event_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_uuid (uuid),
    INDEX idx_event (event_name),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 日报统计表
CREATE TABLE stats_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    uv INT DEFAULT 0,
    pv INT DEFAULT 0,
    assessment_starts INT DEFAULT 0,
    assessment_completes INT DEFAULT 0,
    payment_clicks INT DEFAULT 0,
    payment_successes INT DEFAULT 0,
    revenue DECIMAL(10,2) DEFAULT 0,
    share_clicks INT DEFAULT 0,
    referral_visits INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
