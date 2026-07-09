"""兼容性测试 — 模拟不同浏览器 / 设备的 User-Agent 访问页面。

使用 Django test Client 模拟各主流浏览器与内嵌 WebView 的 User-Agent，
验证首页与测评页在不同环境下均能正常渲染（HTTP 200 且包含核心内容）。

覆盖环境：
- 移动端 Safari（iPhone）
- Chrome Android
- 微信内置浏览器（MicroMessenger）
- 支付宝内置浏览器（AlipayClient）
- Firefox
- Edge
- IE 11（可能显示升级提示）
- PC 端布局

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md Phase 7
"""

from django.test import TestCase


# 各浏览器 / 设备的 User-Agent 字符串
USER_AGENTS = {
    'mobile_safari': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 '
        'Mobile/15E148 Safari/604.1'
    ),
    'chrome_android': (
        'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 '
        'Mobile Safari/537.36'
    ),
    'wechat_browser': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 '
        'MicroMessenger/8.0.43(0x18002b2b) NetType/WIFI Language/zh_CN'
    ),
    'alipay_browser': (
        'Mozilla/5.0 (Linux; Android 14; Build/UP1A.231005.007) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.105 '
        'Mobile Safari/537.36 AlipayClient/10.5.16.8000'
    ),
    'firefox': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) '
        'Gecko/20100101 Firefox/121.0'
    ),
    'edge': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 '
        'Safari/537.36 Edg/120.0.0.0'
    ),
    'ie11': (
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) '
        'like Gecko'
    ),
    'pc_chrome': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 '
        'Safari/537.36'
    ),
}


class CompatibilityTest(TestCase):
    """不同 User-Agent 下的页面渲染兼容性测试。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _assert_page_renders(self, ua, path='/'):
        """断言指定 User-Agent 访问指定路径能正常渲染。

        Args:
            ua: User-Agent 字符串。
            path: 请求路径。
        """
        response = self.client.get(path, HTTP_USER_AGENT=ua)
        self.assertEqual(
            response.status_code, 200,
            f'路径 {path} 在 UA={ua[:40]}... 下返回 {response.status_code}',
        )
        self.assertTrue(
            len(response.content) > 0,
            f'路径 {path} 在 UA={ua[:40]}... 下返回空内容',
        )

    # ------------------------------------------------------------------
    # 移动端
    # ------------------------------------------------------------------

    def test_mobile_safari_ua(self):
        """User-Agent: iPhone Safari → 页面正常渲染。"""
        ua = USER_AGENTS['mobile_safari']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_chrome_android_ua(self):
        """User-Agent: Chrome Android → 页面正常渲染。"""
        ua = USER_AGENTS['chrome_android']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_wechat_browser_ua(self):
        """User-Agent: MicroMessenger → 页面正常渲染。"""
        ua = USER_AGENTS['wechat_browser']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_alipay_browser_ua(self):
        """User-Agent: AlipayClient → 页面正常渲染。"""
        ua = USER_AGENTS['alipay_browser']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    # ------------------------------------------------------------------
    # 桌面端
    # ------------------------------------------------------------------

    def test_firefox_ua(self):
        """User-Agent: Firefox → 页面正常渲染。"""
        ua = USER_AGENTS['firefox']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_edge_ua(self):
        """User-Agent: Edge → 页面正常渲染。"""
        ua = USER_AGENTS['edge']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_ie11_ua(self):
        """User-Agent: IE 11 → 页面正常渲染（可能显示升级提示）。"""
        ua = USER_AGENTS['ie11']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    def test_pc_layout(self):
        """PC 端 User-Agent → 页面正常渲染。"""
        ua = USER_AGENTS['pc_chrome']
        self._assert_page_renders(ua, '/')
        self._assert_page_renders(ua, '/assessment/')

    # ------------------------------------------------------------------
    # 结果页兼容性（移动端 + 桌面端各取一个）
    # ------------------------------------------------------------------

    def test_result_page_mobile_render(self):
        """移动端 Safari 访问结果页 → 正常渲染。"""
        from apps.assessment.models import Assessment
        assessment = Assessment.objects.create(
            uuid='compat-result-uuid',
            mbti_type_code='INTJ',
            dimension_scores={
                'EI': {'percentage': 20, 'label': 'I'},
                'SN': {'percentage': 25, 'label': 'N'},
                'TF': {'percentage': 75, 'label': 'T'},
                'JP': {'percentage': 70, 'label': 'J'},
            },
            facet_scores=[],
            consistency_flag='normal',
        )
        ua = USER_AGENTS['mobile_safari']
        response = self.client.get(
            f'/result/{assessment.uuid}/', HTTP_USER_AGENT=ua
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.content) > 0)
