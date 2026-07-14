# 画己职测 — 业务常量

# 定价
DEEP_REPORT_PRICE: float = 2.99

# 测评题目
QUESTION_COUNT: int = 80
IPIP_QUESTION_COUNT: int = 50  # 大五人格 50 题
RIASEC_QUESTION_COUNT: int = 30  # 职业兴趣 30 题

# 量表
SCALE_MIN: int = 1  # 非常不符合
SCALE_MAX: int = 5  # 非常符合
SCALE_MID: int = 3  # 不确定

# 人格画像
ARCHETYPE_COUNT: int = 32  # 2^5 = 32 种原型

# RIASEC
RIASEC_CODE_LENGTH: int = 3  # 取前三
RIASEC_TYPES: list[str] = ["R", "I", "A", "S", "E", "C"]
RIASEC_PRIORITY: list[str] = ["R", "I", "A", "S", "E", "C"]  # 并列时优先级

# 大五维度
OCEAN_DIMENSIONS: list[str] = ["O", "C", "E", "A", "N"]
OCEAN_LABELS: dict[str, str] = {"O": "开放性", "C": "尽责性", "E": "外向性", "A": "宜人性", "N": "神经质"}

# 维度前缀编码
DIMENSION_PREFIXES: dict[str, str] = {
    "BO": "大五-开放性",
    "BC": "大五-尽责性",
    "BE": "大五-外向性",
    "BA": "大五-宜人性",
    "BN": "大五-神经质",
    "RR": "RIASEC-现实型",
    "RI": "RIASEC-研究型",
    "RA": "RIASEC-艺术型",
    "RS": "RIASEC-社会型",
    "RE": "RIASEC-企业型",
    "RC": "RIASEC-常规型",
}

# 色彩光谱
COLOR_SPECTRUM: dict[str, str] = {
    "O": "#9B7ED8",
    "C": "#5a96b1",
    "E": "#5ea67e",
    "A": "#deb45c",
    "N": "#e17055",
}

# 深度报告
REPORT_CHAPTER_COUNT: int = 12

# 订单
ORDER_TIMEOUT_SECONDS: int = 60

# 支付
PAYMENT_CHANNELS: list[str] = ["wechat_pay", "alipay"]
PAYMENT_POLL_INTERVAL: int = 2  # 秒
PAYMENT_POLL_MAX_TIMES: int = 30

# 缓存
CACHE_TTL: int = 3600  # 1 小时

# 微信
WECHAT_JSAPI_TICKET_TTL: int = 7200  # 秒
WECHAT_SHARE_THUMB_SIZE: int = 300  # 像素
WECHAT_SHARE_THUMB_MAX_KB: int = 32

# 效度检测
VALIDITY_LIE_QUESTION_COUNT: int = 3
VALIDITY_CONTRADICTION_PAIR_COUNT: int = 3
CONFIDENCE_NORMAL: float = 0.8
CONFIDENCE_BORDERLINE: float = 0.5

# 置信度等级
CONFIDENCE_LEVELS: dict[str, tuple[float, float]] = {
    "normal": (0.8, 1.0),  # 正常
    "borderline": (0.5, 0.8),  # 仅供参考
    "low": (0.0, 0.5),  # 建议重测
}
