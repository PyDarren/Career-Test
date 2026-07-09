/* ==========================================================================
   职探 - Browser Fingerprint
   浏览器指纹生成：Canvas 绘制 → 像素数据 → 64 位哈希
   用于匿名用户识别（非唯一标识，作为辅助手段）
   ========================================================================== */

(function () {
    'use strict';

    var Fingerprint = {
        // 指纹哈希值
        hash: null,
        // 生成时间戳
        generatedAt: null,

        /**
         * 生成浏览器指纹
         * 基于 Canvas 绘制 + 系统信息组合
         * @returns {string} 64 位哈希值
         */
        generate: function () {
            if (this.hash) return this.hash;

            var canvasFp = this._generateCanvasFingerprint();
            var systemInfo = this._collectSystemInfo();
            var combined = canvasFp + '|' + systemInfo;

            this.hash = this._hashString(combined);
            this.generatedAt = Date.now();

            // 发送至后端存储（SHA-256 存 Redis，TTL 90 天）
            this._sendToBackend();

            console.info('[职探] 浏览器指纹已生成');
            return this.hash;
        },

        /**
         * Canvas 指纹生成
         * 绘制特定文本和图形，提取像素数据作为指纹
         * @returns {string} Canvas 像素数据哈希
         */
        _generateCanvasFingerprint: function () {
            try {
                var canvas = document.createElement('canvas');
                canvas.width = 200;
                canvas.height = 50;
                var ctx = canvas.getContext('2d');
                if (!ctx) return 'no-canvas';

                // 绘制文本（不同系统/浏览器渲染结果不同）
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f60';
                ctx.fillRect(0, 0, 200, 50);
                ctx.fillStyle = '#069';
                ctx.fillText('CareerTest_fp_2026', 2, 15);
                ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
                ctx.fillText('CareerTest_fp_2026', 4, 17);

                // 提取像素数据
                var imageData = ctx.getImageData(0, 0, 200, 50).data;
                return this._hashArray(imageData);
            } catch (e) {
                return 'canvas-error';
            }
        },

        /**
         * 收集系统信息
         * @returns {string}
         */
        _collectSystemInfo: function () {
            var parts = [];

            // 屏幕信息
            parts.push(screen.width + 'x' + screen.height);
            parts.push(screen.colorDepth);

            // 时区
            try {
                parts.push(Intl.DateTimeFormat().resolvedOptions().timeZone);
            } catch (e) {
                parts.push('tz-unknown');
            }

            // 语言
            parts.push(navigator.language || 'lang-unknown');

            // 平台
            parts.push(navigator.platform || 'platform-unknown');

            // WebGL 渲染器（如果可用）
            try {
                var canvas = document.createElement('canvas');
                var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    if (debugInfo) {
                        parts.push(gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL));
                    }
                }
            } catch (e) {
                // 忽略
            }

            // 硬件并发数
            parts.push(navigator.hardwareConcurrency || 'cores-unknown');

            return parts.join('|');
        },

        /**
         * 字符串哈希（64 位 FNV-1a 变体）
         * @param {string} str - 输入字符串
         * @returns {string} 16 位十六进制哈希
         */
        _hashString: function (str) {
            var hash1 = 0x811c9dc5;
            var hash2 = 0x1000193;

            for (var i = 0; i < str.length; i++) {
                var ch = str.charCodeAt(i);
                hash1 = ((hash1 ^ ch) * 0x01000193) >>> 0;
                hash2 = ((hash2 + ch) * 0x100000001b3) >>> 0;
            }

            // 组合两个哈希为 64 位
            var hex1 = hash1.toString(16).padStart(8, '0');
            var hex2 = hash2.toString(16).padStart(8, '0');
            return hex1 + hex2 + hex1 + hex2;
        },

        /**
         * 数组哈希
         * @param {Uint8ClampedArray} arr - 像素数据
         * @returns {string}
         */
        _hashArray: function (arr) {
            var hash = 0;
            // 采样：每隔 4 个像素取一次（减少计算量）
            for (var i = 0; i < arr.length; i += 16) {
                hash = ((hash << 5) - hash + arr[i]) >>> 0;
            }
            return hash.toString(16).padStart(8, '0');
        },

        /**
         * 发送指纹到后端
         * 后端存储 SHA-256 到 Redis `fp:{hash}` TTL 90 天
         */
        _sendToBackend: function () {
            try {
                var data = {
                    fingerprint: this.hash,
                    timestamp: this.generatedAt
                };

                // 使用 sendBeacon 避免阻塞页面
                if (navigator.sendBeacon) {
                    var blob = new Blob(
                        [JSON.stringify(data)],
                        { type: 'application/json' }
                    );
                    navigator.sendBeacon('/api/fingerprint/', blob);
                    return;
                }

                // Fallback: fetch
                fetch('/api/fingerprint/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                    keepalive: true
                }).catch(function () {});
            } catch (e) {
                console.warn('[职探] 指纹上报失败:', e);
            }
        }
    };

    // Export
    window.Fingerprint = Fingerprint;

})();
