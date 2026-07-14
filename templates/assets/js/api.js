/**
 * api.js — 画己职测 API 请求封装
 * 所有 fetch 请求统一通过此模块发出
 * 依赖：原生 fetch API
 */
var API = (function () {
    'use strict';

    var BASE_URL = '/api';
    var TIMEOUT_MS = 15000;

    /**
     * 统一请求函数
     * @param {string} method - HTTP 方法 (GET/POST)
     * @param {string} path - API 路径 (如 '/questions/')
     * @param {object} [data] - POST 请求体数据
     * @returns {Promise} 解析为 response.data
     */
    function request(method, path, data) {
        var url = BASE_URL + path;
        var options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-Device-Fingerprint': getDeviceFingerprint(),
            },
        };
        if (data) {
            options.body = JSON.stringify(data);
        }

        // 超时控制
        var controller = null;
        var timeoutId = null;
        if (typeof AbortController !== 'undefined') {
            controller = new AbortController();
            options.signal = controller.signal;
            timeoutId = setTimeout(function () {
                controller.abort();
            }, TIMEOUT_MS);
        }

        return fetch(url, options).then(function (response) {
            if (timeoutId) clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error('网络请求失败 (HTTP ' + response.status + ')');
            }
            return response.json();
        }).then(function (result) {
            if (result && result.code === 0) {
                return result.data;
            } else {
                throw new Error((result && result.message) || '请求失败');
            }
        }).catch(function (err) {
            if (timeoutId) clearTimeout(timeoutId);
            if (err.name === 'AbortError') {
                throw new Error('请求超时，请检查网络后重试');
            }
            throw err;
        });
    }

    /**
     * 构建查询字符串
     * @param {object} params - 参数对象
     * @returns {string} 形如 ?key=value&key2=value2，无参数时返回空串
     */
    function buildQuery(params) {
        if (!params) return '';
        var parts = [];
        Object.keys(params).forEach(function (key) {
            var value = params[key];
            if (value === undefined || value === null || value === '') return;
            parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
        });
        return parts.length ? '?' + parts.join('&') : '';
    }

    /**
     * 下载请求（用于 CSV 导出，返回 Blob）
     * @param {string} path - API 路径
     * @param {object} [params] - 查询参数
     * @returns {Promise<Blob>}
     */
    function requestDownload(path, params) {
        var url = BASE_URL + path + buildQuery(params);
        return fetch(url, {
            headers: {
                'X-Device-Fingerprint': getDeviceFingerprint(),
            },
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('下载失败 (HTTP ' + response.status + ')');
            }
            return response.blob();
        });
    }

    /**
     * 触发浏览器下载 Blob 文件
     * @param {Blob} blob - 文件内容
     * @param {string} filename - 文件名
     */
    function downloadBlob(blob, filename) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }

    /**
     * 获取或生成设备指纹（持久化到 localStorage）
     * @returns {string}
     */
    function getDeviceFingerprint() {
        var fp = '';
        try {
            fp = localStorage.getItem('device_fingerprint');
        } catch (e) {
            // localStorage 不可用时使用内存变量
        }
        if (!fp) {
            fp = 'fp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            try {
                localStorage.setItem('device_fingerprint', fp);
            } catch (e) {
                // 静默失败
            }
        }
        return fp;
    }

    /**
     * 获取当前会话 token
     * @returns {string}
     */
    function getSessionToken() {
        try {
            return localStorage.getItem('session_token') || '';
        } catch (e) {
            return '';
        }
    }

    /**
     * 保存会话 token
     * @param {string} token
     */
    function setSessionToken(token) {
        try {
            localStorage.setItem('session_token', token);
        } catch (e) {
            // 静默失败
        }
    }

    /**
     * 清除会话 token
     */
    function clearSessionToken() {
        try {
            localStorage.removeItem('session_token');
        } catch (e) {
            // 静默失败
        }
    }

    return {
        // GET /api/questions/ — 获取 80 题题库
        getQuestions: function () {
            return request('GET', '/questions/');
        },

        // POST /api/assessments/ — 提交测评答案
        submitAssessment: function (answers, startedAt, submittedAt) {
            return request('POST', '/assessments/', {
                answers: answers,
                started_at: startedAt,
                submitted_at: submittedAt,
            });
        },

        // GET /api/assessments/<session_token>/ — 查询测评结果
        getAssessmentResult: function (sessionToken) {
            return request('GET', '/assessments/' + sessionToken + '/');
        },

        // ============== 支付相关 ==============

        // POST /api/orders/ — 创建订单
        // data: { payment_channel, assessment_id, coupon_code? }
        // 返回: { order_id, amount, signature, pay_url, pay_params }
        createOrder: function (data) {
            return request('POST', '/orders/', data);
        },

        // GET /api/orders/<orderId>/status/ — 查询订单支付状态
        // 返回: { order_id, status, paid_at }
        getOrderStatus: function (orderId) {
            return request('GET', '/orders/' + orderId + '/status/');
        },

        // GET /api/orders/?status=<filter> — 获取订单列表
        // 返回: { list: [...], total: N }
        getOrderList: function (filter) {
            var path = '/orders/';
            if (filter && filter !== 'all') {
                path += '?status=' + encodeURIComponent(filter);
            }
            return request('GET', path);
        },

        // GET /api/orders/<orderId>/ — 获取订单详情
        getOrderDetail: function (orderId) {
            return request('GET', '/orders/' + orderId + '/');
        },

        // POST /api/orders/coupon/ — 验证优惠券
        // 返回: { valid, discount, final_price }
        validateCoupon: function (code) {
            return request('POST', '/orders/coupon/', { code: code });
        },

        // POST /api/orders/<orderId>/refund/ — 申请退款
        requestRefund: function (orderId, reason, description) {
            return request('POST', '/orders/' + orderId + '/refund/', {
                reason: reason,
                description: description || '',
            });
        },

        // POST /api/orders/<orderId>/invoice/ — 申领发票
        requestInvoice: function (orderId, data) {
            return request('POST', '/orders/' + orderId + '/invoice/', data);
        },

        // ============== 报告相关 ==============

        // GET /api/reports/<assessmentId>/ — 获取深度报告
        // 返回: { chapters: [...], is_paid, code, title, ... }
        getDeepReport: function (assessmentId) {
            return request('GET', '/reports/' + assessmentId + '/');
        },

        // GET /api/reports/preview/<archetypeId>/ — 获取报告预览
        // 返回: { locked_preview: {...} }
        getReportPreview: function (archetypeId) {
            return request('GET', '/reports/preview/' + archetypeId + '/');
        },

        // ============== 历史记录 ==============

        // GET /api/assessments/history/ — 获取测评历史
        // 返回: { list: [...], total: N }
        getAssessmentHistory: function () {
            return request('GET', '/assessments/history/');
        },

        // DELETE /api/assessments/<assessmentId>/ — 删除测评记录
        deleteAssessment: function (assessmentId) {
            return request('DELETE', '/assessments/' + assessmentId + '/');
        },

        // ============== 埋点 ==============

        // POST /api/tracking-events/ — 埋点事件上报
        trackEvent: function (eventType, eventData, pageName) {
            var payload = {
                event_type: eventType,
                event_data: eventData || {},
            };
            if (pageName) {
                payload.page_name = pageName;
            }
            // fire-and-forget：静默失败，不影响业务逻辑
            return request('POST', '/tracking-events/', payload).catch(function () {
                // 静默忽略埋点失败
            });
        },

        // ============== Admin 后台 ==============

        // --- Admin Dashboard ---
        // GET /api/admin/dashboard/?range= — 看板数据（KPI/趋势/漏斗/告警）
        getDashboardData: function (range) {
            return request('GET', '/admin/dashboard/' + buildQuery({ range: range }));
        },

        // GET /api/admin/dashboard/export/?range= — 导出看板 CSV
        exportDashboard: function (range) {
            return requestDownload('/admin/dashboard/export/', { range: range });
        },

        // --- Admin Orders ---
        // GET /api/admin/orders/?... — 订单列表（筛选/分页/统计）
        getAdminOrders: function (params) {
            return request('GET', '/admin/orders/' + buildQuery(params));
        },

        // GET /api/admin/orders/<id>/ — 订单详情 + 操作日志
        getAdminOrderDetail: function (orderId) {
            return request('GET', '/admin/orders/' + orderId + '/');
        },

        // GET /api/admin/orders/export/?... — 导出订单 CSV
        exportAdminOrders: function (params) {
            return requestDownload('/admin/orders/export/', params);
        },

        // --- Admin Questions ---
        // GET /api/admin/questions/?... — 题目列表（筛选/分页/统计）
        getAdminQuestions: function (params) {
            return request('GET', '/admin/questions/' + buildQuery(params));
        },

        // POST /api/admin/questions/ — 新增题目
        createAdminQuestion: function (data) {
            return request('POST', '/admin/questions/', data);
        },

        // PUT /api/admin/questions/<id>/ — 更新题目
        updateAdminQuestion: function (id, data) {
            return request('PUT', '/admin/questions/' + id + '/', data);
        },

        // DELETE /api/admin/questions/<id>/ — 删除题目
        deleteAdminQuestion: function (id) {
            return request('DELETE', '/admin/questions/' + id + '/');
        },

        // GET /api/admin/questions/export/?... — 导出题目 CSV
        exportAdminQuestions: function (params) {
            return requestDownload('/admin/questions/export/', params);
        },

        // --- Admin Content ---
        // GET /api/admin/content/archetypes/ — 画像列表
        getAdminArchetypes: function () {
            return request('GET', '/admin/content/archetypes/');
        },

        // PUT /api/admin/content/archetypes/<id>/ — 更新画像配置
        updateAdminArchetype: function (id, data) {
            return request('PUT', '/admin/content/archetypes/' + id + '/', data);
        },

        // GET /api/admin/content/careers/ — 职业列表
        getAdminCareers: function () {
            return request('GET', '/admin/content/careers/');
        },

        // PUT /api/admin/content/careers/<id>/ — 更新职业配置
        updateAdminCareer: function (id, data) {
            return request('PUT', '/admin/content/careers/' + id + '/', data);
        },

        // ============== 工具方法 ==============
        getDeviceFingerprint: getDeviceFingerprint,
        getSessionToken: getSessionToken,
        setSessionToken: setSessionToken,
        clearSessionToken: clearSessionToken,
        downloadBlob: downloadBlob,
    };
})();
