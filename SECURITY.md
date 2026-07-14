# 安全策略

## 安全措施概览

### 支付安全（六道防线）

| 防线 | 措施 | 实现位置 |
|------|------|---------|
| 订单防篡改 | HMAC-SHA256 签名（order_id + amount + timestamp） | `payment/services/order_service.py` |
| 回调签名验证 | 微信/支付宝回调签名校验 | `payment/services/callback_handler.py` |
| 防重复支付 | 回调幂等去重（order.status == paid 检查） | `payment/services/callback_handler.py` |
| 订单超时与对账 | Celery 定时任务（60s 过期 + 02:30 对账） | `stats/tasks.py` |
| 金额一致性 | 回调金额 == 订单金额 == 2.99 校验 | `payment/services/callback_handler.py` |
| 前端轮询 | 2 秒间隔 / 最多 30 次 | `templates/assets/js/payment.js` |

### 数据安全

- **AES-256-CBC 加密**：答题数据加密存储（`common/utils.py: encrypt_data/decrypt_data`）
- **手机号脱敏**：138****1234 格式（`common/utils.py: mask_phone`）
- **答题数据脱敏**：日志中不暴露原始答题数据（`common/utils.py: mask_answers`）
- **SECRET_KEY**：从环境变量读取，不硬编码（`settings/base.py`）
- **.env 文件**：已在 `.gitignore` 中排除

### HTTP 安全

- **HTTPS 强制**：Nginx 80 → 443 重定向（`deploy/nginx/career_test.conf`）
- **安全头**：X-Frame-Options DENY, X-Content-Type-Options nosniff, HSTS
- **CSRF 保护**：Django CSRF 中间件启用
- **CORS**：生产环境仅允许指定域名
- **Cookie 安全**：httponly=True, samesite=Lax

### 错误处理

- **全局异常处理**：`ExceptionHandlerMiddleware` 捕获未处理异常
- **DEBUG 模式**：生产环境 DEBUG=False，不暴露异常详情
- **Sentry 集成**：生产环境自动上报异常到 Sentry

### 设备追踪

- **设备指纹**：64 位十六进制，通过 Cookie/Header 传递
- **Session Token**：UUID4，匿名用户追踪（无需登录）
- **免登录测评**：用户打开应用即可开始测试

## 漏洞报告

如发现安全漏洞，请联系：security@huajizhice.com

## 合规说明

- 测评体系使用 IPIP Big Five（公有领域）+ Holland RIASEC（自由引用框架）
- 不使用 MBTI（商标法律风险，已于 v1.2 弃用）
- 用户数据存储符合个人信息保护法要求
