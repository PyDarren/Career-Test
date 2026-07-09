# AGENTS.md

**职探 — AI 代理开发指令文档**

本文档为 AI 代理（包括 TRAE、Cursor、Copilot 等）参与"职探"项目开发时的行为规范。代理在执行任何任务前应完整阅读本文档，并在后续操作中严格遵守其中约定。

---

## 目录

- [项目概述](#overview)
- [开发规范](#dev-conventions)
- [测试要求](#testing)
- [代码风格](#code-style)
- [注意事项](#precautions)
- [常见任务指引](#task-guide)
- [依赖清单](#dependencies)

---

<a id="overview"></a>
## 项目概述

### 产品定位

职探是一款面向大学生和职场新人的轻量化 MBTI 职业性格测评网页。核心体验是"八分钟，看见你的职业性格"——用户无需注册，打开即测，6–8 分钟完成 48 道 6 点刻度迫选题，免费查看人格认证卡，付费 2.99 元解锁 12 章深度报告。

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Django 5.0 LTS + Python 3.12 |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7.0 |
| 前端 | Django 模板 + Vanilla JS（不引入 Vue/React） |
| 图表 | ECharts 5.5 |
| 服务器 | Gunicorn 22.0 + Nginx 1.24 |
| 支付 | 微信支付 V3 + 支付宝 V3 |
| 视觉风格 | 参照 [16personalities.com](https://www.16personalities.com) |

### 关键文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 产品需求文档 | `PRD.md` (v3.5) | 产品功能（15 项）、商业模式、用户画像、支撑功能设计等 |
| 技术设计文档 | `TECH_DESIGN.md` (v1.2) | 架构、数据库（9 张表）、API（19 个端点）、安全设计、支撑系统设计等 |
| AI 代理指令 | `AGENTS.md` | 本文档 |

### Django 项目结构

```
careertest/
├── manage.py
├── apps/
│   ├── assessment/        # 测评模块（题目、评分引擎、结果、测评历史）
│   ├── mbti_types/        # MBTI 类型配置（16 型、认知功能栈、报告模板）
│   ├── careers/           # 职业数据库与匹配算法
│   ├── payment/           # 支付模块（微信/支付宝、订单、报告凭证）
│   ├── stats/             # 统计模块（埋点、反馈、日报、Celery 定时任务）
│   └── common/            # 公共模块（指纹、限流、统一错误处理、工具函数）
├── templates/
│   ├── base.html
│   ├── pages/             # 页面模板（首页/答题/结果/报告/帮助/设置）
│   └── partials/          # 可复用组件模板
├── static/
│   ├── css/main.css       # 主样式（含设计系统 CSS 变量）
│   ├── js/                # 前端 JS（assessment/tracking/share/payment）
│   ├── images/mascots/    # 16 型 3D 人偶图片
│   └── libs/              # ECharts 等第三方库
└── config/                # 部署配置
```

---

<a id="dev-conventions"></a>
## 开发规范

### 环境准备

```bash
# Python 3.12 + venv
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 加载初始数据（16 型配置 + 48 道题目 + 职业数据库）
python manage.py loaddata mbti_types.json questions.json careers.json

# 启动开发服务器
python manage.py runserver 0.0.0.0:8000
```

### 环境变量

所有敏感配置通过环境变量注入，不硬编码在代码中。开发环境使用 `.env` 文件（不提交到 Git）：

```bash
# .env（不提交到 Git）
DJANGO_SETTINGS_MODULE=caretest.settings.development
DB_USER=root
DB_PASSWORD=your_password
REDIS_URL=redis://127.0.0.1:6379/1
WECHAT_APP_ID=wx_your_app_id
WECHAT_MCH_ID=your_mch_id
WECHAT_API_KEY=your_api_key
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY=your_private_key
SENTRY_DSN=your_sentry_dsn
```

### Django app 划分规则

新增功能时按业务领域划分 app，不按技术层划分。每个 app 内包含完整的 models / views / urls / migrations / fixtures。

| app | 职责 | 禁止操作 |
|-----|------|---------|
| `assessment` | 题目管理、评分引擎、测评记录 | 不处理支付逻辑 |
| `mbti_types` | 16 型配置、认知功能栈 | 不直接操作 career 表 |
| `careers` | 职业数据库、匹配算法 | 不处理订单或支付 |
| `payment` | 订单、支付、回调 | 不实现评分逻辑 |
| `stats` | 数据统计、定时任务 | 不写入业务数据 |
| `common` | 指纹、限流、工具函数 | 不包含业务逻辑 |

跨 app 调用通过 model 方法或 service 层函数，不直接在 view 中跨 app 查询数据库。

### Model 编写规范

```python
# 正确示例：model 方法封装业务逻辑
class Order(models.Model):
    order_no = models.CharField(max_length=32, unique=True)
    uuid = models.CharField(max_length=36)
    amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('2.99'))
    status = models.CharField(max_length=10, default='pending')
    # ...

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['assessment_id'],
                condition=models.Q(status='paid'),
                name='unique_paid_order_per_assessment'
            )
        ]

    def __str__(self):
        return f'{self.order_no} ({self.status})'

    @property
    def is_expired(self):
        return self.status == 'pending' and self.expires_at < timezone.now()

    def mark_as_paid(self, payment_id):
        """标记订单为已支付，含状态校验"""
        if self.status != 'pending':
            raise ValueError(f'订单状态为 {self.status}，不能标记为已支付')
        self.status = 'paid'
        self.payment_id = payment_id
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'payment_id', 'paid_at'])
```

```python
# 错误示例：在 view 中散落业务逻辑
def pay(request):
    order = Order.objects.get(...)
    # 不要在 view 中直接操作订单状态
    order.status = 'paid'
    order.paid_at = timezone.now()
    order.save()  # 缺少状态校验，有并发风险
```

### View 编写规范

- 所有 API view 继承 `View` 类，不使用 Django REST Framework（本项目不需要序列化器）
- 返回 JSON 的 view 使用 `JsonResponse`
- 渲染页面的 view 使用 `render`
- 所有 POST 接口必须校验 CSRF token（支付回调除外，使用 `@csrf_exempt` + 验签）

```python
from django.views import View
from django.http import JsonResponse

class ScoreView(View):
    """评分接口"""

    def post(self, request):
        # 1. 参数校验
        data = json.loads(request.body)
        answers = data.get('answers', [])
        if len(answers) != 48:
            return JsonResponse(
                {'error': f'答案数量不正确，应为 48 题，实际 {len(answers)} 题'},
                status=400
            )

        # 2. 调用业务逻辑
        engine = ScoringEngine()
        result = engine.calculate(answers, questions)

        # 3. 持久化
        assessment = Assessment.objects.create(...)

        # 4. 返回结果
        return JsonResponse(result)
```

### URL 路由规范

```python
# apps/assessment/urls.py
from django.urls import path
from .views import AssessmentView, ScoreView, ResultView

app_name = 'assessment'

urlpatterns = [
    path('', AssessmentView.as_view(), name='assessment'),        # 答题页
    path('api/score/', ScoreView.as_view(), name='score'),         # 评分接口
    path('result/<str:uuid>/', ResultView.as_view(), name='result'),  # 结果页
]
```

URL 命名使用 kebab-case，API 接口统一前缀 `/api/`，页面路由无前缀。

### 模板编写规范

```html
<!-- templates/base.html -->
{% load static %}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}职探{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body data-role="{{ role_group }}">
    {% block content %}{% endblock %}
    <script src="{% static 'js/main.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

- 所有页面继承 `base.html`，通过 `{% block %}` 覆写
- 静态文件引用使用 `{% static %}` 标签
- `data-role` 属性用于切换四角色组配色（analyst/diplomat/sentinel/explorer）
- 模板中使用 `{% include 'partials/xxx.html' %}` 复用组件

### 前端 JS 编写规范

```javascript
// 每个功能模块使用 IIFE 封装，不污染全局作用域
(function() {
    'use strict';

    const Assessment = {
        // 状态
        questions: [],
        currentIdx: 0,
        answers: {},

        // 初始化
        init(questions) {
            this.questions = questions;
            this.answers = this.loadProgress();
            this.render();
        },

        // 方法...
    };

    // 导出
    window.Assessment = Assessment;
})();
```

- 不引入 Vue / React / jQuery 等框架
- 每个功能模块封装为独立对象，通过 `window.ModuleName` 导出
- 使用 `'use strict'` 模式
- DOM 操作集中在模块方法中，不散落在 HTML 内联事件中

### CSS 编写规范

```css
/* 所有颜色使用 CSS 变量，不硬编码 hex 值 */
.btn-primary {
    background: var(--color-primary);      /* 不写 #4D3E8C */
    color: #fff;
}

/* 响应式断点统一使用 600px */
@media (max-width: 600px) {
    .container { padding: 0 16px; }
}

/* 四角色组配色通过 data-role 属性切换 */
[data-role="analyst"] .dimension-bar-fill { background: var(--color-analyst); }
[data-role="diplomat"] .dimension-bar-fill { background: var(--color-diplomat); }
```

- CSS 变量定义在 `:root` 中，参照 TECH_DESIGN.md 的视觉设计系统章节
- 不使用 `!important`（特殊情况除外并注释原因）
- 类名使用 BEM 命名法：`.block__element--modifier`
- 媒体查询统一放在对应选择器之后

---

<a id="testing"></a>
## 测试要求

### 测试框架

使用 Django 内置的 `django.test.TestCase`，不引入 pytest（减少依赖）。

### 测试覆盖范围

| 模块 | 必测场景 | 最低覆盖率 |
|------|---------|-----------|
| `assessment/scoring.py` | 48 题全作答、临界维度（6:6）、面向不一致、极端作答检测 | 90% |
| `careers/matching.py` | 类型直接匹配、相邻类型匹配、维度强度余弦相似度、低于 50 分过滤 | 85% |
| `payment/views.py` | 订单创建、防重复支付、回调验签、金额一致性校验、订单超时 | 90% |
| `payment/wechat_pay.py` | 签名生成、验签（正确/错误签名）、回调解密 | 95% |
| `assessment/views.py` | 评分接口正常请求、答案数量不足、异常处理 | 80% |

### 评分引擎测试示例

```python
# apps/assessment/tests/test_scoring.py

from django.test import TestCase
from apps.assessment.scoring import ScoringEngine, Answer

class ScoringEngineTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """加载 48 道题目"""
        cls.questions = [
            {'id': 1, 'dimension': 'EI', 'facet': '社交能量', 'pole_a': 'E', 'pole_b': 'I', 'is_reverse': False},
            # ... 其余 47 题
        ]

    def test_all_position_1_returns_extreme_a(self):
        """所有题选位置 1 → 全部 A 极，类型为 XXXX（取决于 A 极字母）"""
        answers = [Answer(qid, 1) for qid in range(1, 49)]
        result = ScoringEngine().calculate(answers, self.questions)
        # 每个维度 A 极总分为 36（满分），B 极为 0
        for dim in result['dimensions'].values():
            self.assertEqual(dim['score_a'], 36)
            self.assertEqual(dim['score_b'], 0)
            self.assertEqual(dim['level'], '明显倾向')

    def test_critical_dimension_returns_x(self):
        """维度得分相等时返回 X"""
        # 构造 EI 维度 6:6 的答案
        answers = self._build_answers(ei_a=18, ei_b=18)
        result = ScoringEngine().calculate(answers, self.questions)
        self.assertEqual(result['dimensions']['EI']['pole'], 'X')

    def test_extreme_response_detection(self):
        """连续 8 题以上选位置 1 或 6 → 标记 extreme_response"""
        answers = [Answer(qid, 1 if i < 20 else 4) for i, qid in enumerate(range(1, 49), 1)]
        result = ScoringEngine().calculate(answers, self.questions)
        self.assertEqual(result['consistency_flag'], 'extreme_response')

    def test_cognitive_stack_intj(self):
        """INTJ 类型 → 认知功能栈 Ni > Te > Fi > Se"""
        answers = self._build_answers_to_get_type('INTJ')
        result = ScoringEngine().calculate(answers, self.questions)
        self.assertEqual(result['mbti_type'], 'INTJ')
        self.assertEqual(result['cognitive_stack']['dominant'], 'Ni')
        self.assertEqual(result['cognitive_stack']['inferior'], 'Se')
```

### 支付安全测试示例

```python
# apps/payment/tests/test_security.py

from django.test import TestCase, Client
from apps.payment.models import Order
from apps.assessment.models import Assessment
import json

class PaymentSecurityTest(TestCase):

    def setUp(self):
        self.assessment = Assessment.objects.create(
            uuid='test-uuid', mbti_type_code='ENFP',
            dimension_scores='{}', facet_scores='{}'
        )

    def test_amount_cannot_be_tampered(self):
        """前端传入的 amount 字段被忽略，实际使用服务端硬编码金额"""
        client = Client()
        response = client.post('/api/payment/create/', data=json.dumps({
            'assessment_id': self.assessment.id,
            'uuid': 'test-uuid',
            'method': 'wechat',
            'amount': '0.01',  # 尝试篡改金额
        }), content_type='application/json')

        order = Order.objects.first()
        self.assertEqual(order.amount, Decimal('2.99'))  # 服务端金额未被篡改

    def test_duplicate_payment_prevented(self):
        """同一 assessment 已有 paid 订单时，再次创建返回 400"""
        Order.objects.create(
            order_no='CT001', uuid='test-uuid',
            assessment_id=self.assessment.id, amount=Decimal('2.99'),
            status='paid'
        )
        client = Client()
        response = client.post('/api/payment/create/', data=json.dumps({
            'assessment_id': self.assessment.id,
            'uuid': 'test-uuid',
            'method': 'wechat',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_referer_rejected(self):
        """评分接口拒绝非本站 Referer"""
        client = Client()
        response = client.post('/api/score/', data=json.dumps({...}),
            content_type='application/json',
            HTTP_REFERER='https://evil.example.com/'
        )
        self.assertEqual(response.status_code, 403)
```

### 运行测试

```bash
# 运行全部测试
python manage.py test

# 运行单个 app 测试
python manage.py test apps.assessment

# 运行单个测试类
python manage.py test apps.assessment.tests.test_scoring.ScoringEngineTest

# 带覆盖率报告（需安装 coverage）
coverage run --source='.' manage.py test
coverage report --fail-under=80
```

---

<a id="code-style"></a>
## 代码风格

### Python 代码风格

| 规则 | 要求 |
|------|------|
| 格式化工具 | `black`（行宽 88） |
| import 排序 | `isort`（Django profile） |
| Linter | `flake8`（max-line-length=120） |
| 类型标注 | 公共函数和方法必须添加类型标注（`from typing import ...`） |
| 文档字符串 | 公共类和函数必须有 docstring |
| 变量命名 | `snake_case`，常量 `UPPER_SNAKE_CASE` |
| 私有方法 | 前缀下划线 `_private_method` |

```python
# 正确示例
def calculate_match_score(
    user_type: str,
    dimensions: dict,
    career: 'Career'
) -> float:
    """计算用户与职业的匹配度评分"""
    ...

# 错误示例
def calc(t, d, c):  # 无类型标注、缩写命名、无 docstring
    ...
```

### JavaScript 代码风格

| 规则 | 要求 |
|------|------|
| 格式化 | 2 空格缩进 |
| 变量命名 | `camelCase` |
| 常量 | `UPPER_SNAKE_CASE` |
| 字符串 | 统一使用单引号 `'` |
| 分号 | 行尾加分号 |
| 严格模式 | 每个文件顶部 `'use strict'` |

### CSS 代码风格

| 规则 | 要求 |
|------|------|
| 缩进 | 4 空格 |
| 属性排序 | 先布局（display/position）后视觉（color/font）后动效（transition） |
| 颜色 | 全部使用 CSS 变量，不硬编码 hex |
| 颜色格式 | 使用 hex（`#4D3E8C`），不使用 rgb() |
| 媒体查询 | 移动优先，默认样式适配移动端，`@media (min-width: 600px)` 适配 PC |

### HTML 模板风格

| 规则 | 要求 |
|------|------|
| 缩进 | 4 空格 |
| 语义化标签 | 使用 `<section>` `<article>` `<nav>` 等，不滥用 `<div>` |
| Django 模板标签 | 标签内前后留空格 `{% if x %}` |
| 注释 | 使用 `{# comment #}` 或 `{% comment %}` |

---

<a id="precautions"></a>
## 注意事项

### 安全红线

以下行为在任何情况下都不允许：

1. **前端金额传入**：支付金额必须由服务端硬编码（`Decimal('2.99')`），不从前端请求体读取金额参数
2. **跳过验签**：支付回调必须验签，即使开发环境也不能用 `@csrf_exempt` + 跳过验签的"临时方案"
3. **硬编码密钥**：API 密钥、数据库密码等不得出现在代码中，必须通过环境变量读取
4. **日志记录敏感数据**：日志中不得记录用户的完整答题数据、支付流水号、手机号等信息
5. **跨站请求**：评分和支付接口必须校验 Referer，拒绝非本站来源的请求
6. **禁用安全中间件**：不得注释或禁用 `SecurityMiddleware`、`CsrfViewMiddleware`、`XFrameOptionsMiddleware`

### 支付相关约束

- 订单状态只能按 `pending → paid → refunded` 或 `pending → failed/expired` 流转，不允许跳转
- 支付回调必须实现幂等处理（`select_for_update` + 状态检查）
- 订单 15 分钟自动过期，不得修改超时时间（除非通过 PRD 变更流程）
- 金额使用 `Decimal` 类型，不使用 `float`（浮点精度问题）

### 数据隐私约束

- 答题原始数据（48 个刻度位置）不存入数据库，仅存浏览器 localStorage，提交评分后丢弃
- 测评记录表仅存储结果（类型代码 + 得分），不存储原始答案
- 浏览器指纹哈希值 90 天后自动从 Redis 清除
- 不得在任何日志中记录用户的完整答题数据

### 性能约束

- 首屏加载 ≤ 500KB（HTML + CSS + JS，不含图片）
- 16 型 3D 人偶图片单张 ≤ 80KB（WebP 格式）
- 评分接口响应 ≤ 1 秒
- 非首屏资源必须懒加载
- 数据库查询注意 N+1 问题，使用 `select_related` / `prefetch_related`

### Git 提交规范

```bash
# 提交信息格式：type: 简短描述
git commit -m "feat: 添加评分引擎面向级计分逻辑"
```

| type | 含义 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| refactor | 重构（不改变功能） |
| style | 代码风格调整（不改逻辑） |
| docs | 文档变更 |
| test | 新增或修改测试 |
| chore | 构建、依赖、配置等杂项 |

### 禁止操作

- 不修改 `PRD.md` 和 `TECH_DESIGN.md` 的版本号和文档状态（由人工评审后更新）
- 不引入新的 Python / JS / CSS 依赖（需通过 PR 评审）
- 不在 `static/` 目录中放置超过 200KB 的文件（大文件使用 CDN）
- 不在模板中使用内联样式 `style="..."`
- 不在 JS 中使用 `var`（使用 `const` 或 `let`）
- 不使用 `console.log` 调试代码提交到仓库
- 不删除数据库迁移文件（`migrations/`），只新增

---

<a id="task-guide"></a>
## 常见任务指引

### 添加新的 API 接口

1. 在对应 app 的 `views.py` 中添加 View 类
2. 在对应 app 的 `urls.py` 中注册路由
3. 在 `apps/<app>/tests/` 中添加测试用例
4. 运行 `python manage.py test apps.<app>` 确认测试通过

### 修改评分算法

1. 修改 `apps/assessment/scoring.py`
2. 更新 `apps/assessment/tests/test_scoring.py` 中的测试用例
3. 确保新增的逻辑不影响已有测试
4. 更新 `TECH_DESIGN.md` 中"6 点刻度评分引擎"章节的代码示例

### 修改数据库结构

1. 修改 `apps/<app>/models.py`
2. 运行 `python manage.py makemigrations <app_name>` 生成迁移文件
3. 运行 `python manage.py migrate` 执行迁移
4. 更新 `TECH_DESIGN.md` 中对应的表结构 DDL
5. 如果涉及初始数据，更新 `fixtures/` 中的 JSON 文件

### 新增 MBTI 类型数据

16 型配置数据存储在 `apps/mbti_types/fixtures/mbti_types.json` 中。修改后执行：

```bash
python manage.py loaddata mbti_types.json
```

### 添加前端页面

1. 在 `templates/pages/` 中创建 HTML 模板，继承 `base.html`
2. 在对应 app 的 `views.py` 中添加渲染 View
3. 在 `urls.py` 中注册路由
4. 如需交互 JS，在 `static/js/` 中创建独立 JS 文件
5. 在 `base.html` 的 `{% block extra_js %}` 中引入

### 修改视觉设计

1. CSS 变量定义在 `static/css/main.css` 的 `:root` 中
2. 修改变量值后需检查所有使用该变量的组件
3. 四角色组配色修改需同步更新 `TECH_DESIGN.md` 的视觉设计系统章节
4. 新增颜色必须定义为 CSS 变量，不硬编码

---

<a id="dependencies"></a>
## 依赖清单

```txt
# requirements.txt
Django==5.0.6
mysqlclient==2.2.4
redis==5.0.7
django-redis==5.4.0
celery==5.4.0
cryptography==42.0.8        # 微信支付 V3 验签
Pillow==10.4.0             # 图片处理（人偶缩放）

# 开发依赖
# requirements-dev.txt
black==24.4.2
isort==5.13.2
flake8==7.1.0
coverage==7.5.4
```

不引入以下类型的依赖：

- Web 框架扩展（如 Django REST Framework，本项目不需要序列化器）
- 前端框架（Vue / React / jQuery）
- ORM 扩展（如 django-mysql-extensions）
- 重量级依赖（如 numpy / pandas，本项目不需要数据分析）
