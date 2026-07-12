/**
 * account.js — 账户设置页交互脚本
 * 功能：头像上传、昵称编辑、手机更换、隐私开关、数据导出、
 *       账户删除（二次确认 + 7 日清除）、退出登录
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'career_test_account',
        privacyKey: 'career_test_privacy',
        codeCountdown: 60,     // 验证码倒计时秒数
        exportSteps: ['正在收集测评记录...', '正在生成报告数据...', '正在打包文件...', '导出完成']
    };

    // ============== 模拟用户数据 ==============
    var DEFAULT_USER = {
        nickname: 'Career Test 用户',
        avatar: null,           // base64 或 null
        phone: '138****6789',
        typeCode: 'INTJ-A-C',
        registerDate: '2026-07-12'
    };

    // ============== DOM 元素引用 ==============
    var els = {
        // 导航
        backBtn:           document.getElementById('backBtn'),
        // 头像 & 昵称
        avatarWrapper:     document.getElementById('avatarWrapper'),
        avatar:            document.getElementById('avatar'),
        avatarInput:       document.getElementById('avatarInput'),
        nicknameRow:       document.getElementById('nicknameRow'),
        nicknameDisplay:   document.getElementById('nicknameDisplay'),
        typeBadge:         document.getElementById('typeBadge'),
        registerDate:      document.getElementById('registerDate'),
        // 手机
        phoneRow:          document.getElementById('phoneRow'),
        phoneDisplay:      document.getElementById('phoneDisplay'),
        // 隐私开关
        anonymousToggle:   document.getElementById('anonymousToggle'),
        analyticsToggle:   document.getElementById('analyticsToggle'),
        publicToggle:      document.getElementById('publicToggle'),
        // 数据管理
        exportRow:         document.getElementById('exportRow'),
        deleteAccountRow:  document.getElementById('deleteAccountRow'),
        // 退出
        logoutBtn:         document.getElementById('logoutBtn'),
        // 昵称弹窗
        nicknameModal:     document.getElementById('nicknameModal'),
        nicknameOverlay:   document.getElementById('nicknameOverlay'),
        nicknameInput:     document.getElementById('nicknameInput'),
        charCount:         document.getElementById('charCount'),
        nicknameCancel:    document.getElementById('nicknameCancel'),
        nicknameConfirm:   document.getElementById('nicknameConfirm'),
        // 手机弹窗
        phoneModal:        document.getElementById('phoneModal'),
        phoneOverlay:      document.getElementById('phoneOverlay'),
        phoneInput:        document.getElementById('phoneInput'),
        codeInput:         document.getElementById('codeInput'),
        sendCodeBtn:       document.getElementById('sendCodeBtn'),
        phoneCancel:       document.getElementById('phoneCancel'),
        phoneConfirm:      document.getElementById('phoneConfirm'),
        // 删除弹窗
        deleteModal:       document.getElementById('deleteModal'),
        deleteOverlay:     document.getElementById('deleteOverlay'),
        deleteConfirm:     document.getElementById('deleteConfirm'),
        deleteCancel:      document.getElementById('deleteCancel'),
        deleteOk:          document.getElementById('deleteOk'),
        // 导出弹窗
        exportModal:       document.getElementById('exportModal'),
        exportProgressFill:document.getElementById('exportProgressFill'),
        exportProgressText:document.getElementById('exportProgressText'),
        // Toast
        toast:             document.getElementById('accountToast')
    };

    // ============== 内部状态 ==============
    var state = {
        user: {},
        codeTimer: null,
        codeCountdown: 0
    };

    // ========================================================
    //  1. 数据加载
    // ========================================================
    function loadUser() {
        var saved = localStorage.getItem(CONFIG.storageKey);
        if (saved) {
            try {
                state.user = JSON.parse(saved);
            } catch (e) {
                state.user = {};
            }
        }
        // 合并默认值
        var keys = Object.keys(DEFAULT_USER);
        for (var i = 0; i < keys.length; i++) {
            if (state.user[keys[i]] === undefined) {
                state.user[keys[i]] = DEFAULT_USER[keys[i]];
            }
        }
        renderUser();
    }

    function saveUser() {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.user));
    }

    function loadPrivacy() {
        var saved = localStorage.getItem(CONFIG.privacyKey);
        var privacy = { anonymous: true, analytics: true, public: false };
        if (saved) {
            try {
                var parsed = JSON.parse(saved);
                privacy.anonymous = parsed.anonymous !== undefined ? parsed.anonymous : true;
                privacy.analytics = parsed.analytics !== undefined ? parsed.analytics : true;
                privacy.public = parsed.public !== undefined ? parsed.public : false;
            } catch (e) {
                // ignore
            }
        }
        els.anonymousToggle.checked = privacy.anonymous;
        els.analyticsToggle.checked = privacy.analytics;
        els.publicToggle.checked = privacy.public;
    }

    function savePrivacy() {
        var privacy = {
            anonymous: els.anonymousToggle.checked,
            analytics: els.analyticsToggle.checked,
            public: els.publicToggle.checked
        };
        localStorage.setItem(CONFIG.privacyKey, JSON.stringify(privacy));
    }

    function renderUser() {
        els.nicknameDisplay.textContent = state.user.nickname;
        els.phoneDisplay.textContent = state.user.phone;
        els.typeBadge.textContent = state.user.typeCode;
        els.registerDate.textContent = state.user.registerDate;

        // 渲染头像
        if (state.user.avatar) {
            els.avatar.innerHTML = '<img src="' + state.user.avatar + '" alt="头像">';
        }
    }

    // ========================================================
    //  2. 返回按钮
    // ========================================================
    function initBackBtn() {
        els.backBtn.addEventListener('click', function () {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = 'index.html';
            }
        });
    }

    // ========================================================
    //  3. 头像上传
    // ========================================================
    function initAvatar() {
        els.avatarWrapper.addEventListener('click', function () {
            els.avatarInput.click();
        });

        els.avatarInput.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (!file) return;

            // 验证文件类型
            if (!file.type.startsWith('image/')) {
                showToast('请选择图片文件');
                return;
            }

            // 验证文件大小（2MB 以内）
            if (file.size > 2 * 1024 * 1024) {
                showToast('图片大小不能超过 2MB');
                return;
            }

            // 读取并预览
            var reader = new FileReader();
            reader.onload = function (ev) {
                state.user.avatar = ev.target.result;
                saveUser();
                renderUser();

                // 响应 <1 秒
                showToast('头像更新成功');
                trackEvent('avatar_update', { size: file.size });
            };
            reader.readAsDataURL(file);

            // 清空 input 以便重复选择同一文件
            els.avatarInput.value = '';
        });
    }

    // ========================================================
    //  4. 昵称编辑
    // ========================================================
    function initNickname() {
        els.nicknameRow.addEventListener('click', function () {
            els.nicknameInput.value = state.user.nickname;
            updateCharCount();
            openModal(els.nicknameModal);
            setTimeout(function () {
                els.nicknameInput.focus();
                els.nicknameInput.select();
            }, 300);
        });

        // 字符计数
        els.nicknameInput.addEventListener('input', updateCharCount);

        // 保存
        els.nicknameConfirm.addEventListener('click', function () {
            var value = els.nicknameInput.value.trim();
            if (!value) {
                showToast('昵称不能为空');
                return;
            }
            if (value.length > 20) {
                showToast('昵称最多 20 字');
                return;
            }

            state.user.nickname = value;
            saveUser();
            renderUser();
            closeModal(els.nicknameModal);

            showToast('昵称修改成功');
            trackEvent('nickname_update', { length: value.length });
        });

        els.nicknameCancel.addEventListener('click', function () {
            closeModal(els.nicknameModal);
        });

        els.nicknameOverlay.addEventListener('click', function () {
            closeModal(els.nicknameModal);
        });
    }

    function updateCharCount() {
        els.charCount.textContent = els.nicknameInput.value.length;
    }

    // ========================================================
    //  5. 手机更换
    // ========================================================
    function initPhone() {
        els.phoneRow.addEventListener('click', function () {
            els.phoneInput.value = '';
            els.codeInput.value = '';
            els.sendCodeBtn.disabled = false;
            els.sendCodeBtn.textContent = '获取验证码';
            state.codeCountdown = 0;
            if (state.codeTimer) {
                clearInterval(state.codeTimer);
                state.codeTimer = null;
            }
            openModal(els.phoneModal);
        });

        // 发送验证码
        els.sendCodeBtn.addEventListener('click', function () {
            var phone = els.phoneInput.value.trim();
            if (!/^1[3-9]\d{9}$/.test(phone)) {
                showToast('请输入正确的手机号');
                return;
            }

            // 开始倒计时
            state.codeCountdown = CONFIG.codeCountdown;
            els.sendCodeBtn.disabled = true;
            els.sendCodeBtn.textContent = state.codeCountdown + 's';

            state.codeTimer = setInterval(function () {
                state.codeCountdown--;
                if (state.codeCountdown <= 0) {
                    clearInterval(state.codeTimer);
                    state.codeTimer = null;
                    els.sendCodeBtn.disabled = false;
                    els.sendCodeBtn.textContent = '获取验证码';
                } else {
                    els.sendCodeBtn.textContent = state.codeCountdown + 's';
                }
            }, 1000);

            showToast('验证码已发送');
            trackEvent('send_code', { phone: phone.substring(0, 7) + '****' });
        });

        // 确认更换
        els.phoneConfirm.addEventListener('click', function () {
            var phone = els.phoneInput.value.trim();
            var code = els.codeInput.value.trim();

            if (!/^1[3-9]\d{9}$/.test(phone)) {
                showToast('请输入正确的手机号');
                return;
            }
            if (code.length !== 6) {
                showToast('请输入 6 位验证码');
                return;
            }

            // 模拟更换（响应 <1 秒）
            var masked = phone.substring(0, 3) + '****' + phone.substring(7);
            state.user.phone = masked;
            saveUser();
            renderUser();

            closeModal(els.phoneModal);
            if (state.codeTimer) {
                clearInterval(state.codeTimer);
                state.codeTimer = null;
            }

            showToast('手机号更换成功');
            trackEvent('phone_update', { phone: masked });
        });

        els.phoneCancel.addEventListener('click', function () {
            closeModal(els.phoneModal);
            if (state.codeTimer) {
                clearInterval(state.codeTimer);
                state.codeTimer = null;
            }
        });

        els.phoneOverlay.addEventListener('click', function () {
            closeModal(els.phoneModal);
            if (state.codeTimer) {
                clearInterval(state.codeTimer);
                state.codeTimer = null;
            }
        });
    }

    // ========================================================
    //  6. 隐私设置
    // ========================================================
    function initPrivacy() {
        els.anonymousToggle.addEventListener('change', function () {
            savePrivacy();
            showToast(els.anonymousToggle.checked ? '已开启匿名化分享' : '已关闭匿名化分享');
            trackEvent('privacy_toggle', { setting: 'anonymous', value: els.anonymousToggle.checked });
        });

        els.analyticsToggle.addEventListener('change', function () {
            savePrivacy();
            showToast(els.analyticsToggle.checked ? '已允许数据分析' : '已关闭数据分析');
            trackEvent('privacy_toggle', { setting: 'analytics', value: els.analyticsToggle.checked });
        });

        els.publicToggle.addEventListener('change', function () {
            savePrivacy();
            showToast(els.publicToggle.checked ? '已开启结果公开' : '已关闭结果公开');
            trackEvent('privacy_toggle', { setting: 'public', value: els.publicToggle.checked });
        });
    }

    // ========================================================
    //  7. 数据导出
    // ========================================================
    function initExport() {
        els.exportRow.addEventListener('click', function () {
            openModal(els.exportModal);
            startExport();
        });
    }

    function startExport() {
        var step = 0;
        els.exportProgressFill.style.width = '0%';
        els.exportProgressText.textContent = CONFIG.exportSteps[0];

        var progress = 0;
        var interval = setInterval(function () {
            progress += Math.random() * 20 + 10;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }

            els.exportProgressFill.style.width = progress + '%';

            // 更新步骤文字
            var newStep = Math.min(Math.floor(progress / 25), CONFIG.exportSteps.length - 1);
            if (newStep !== step) {
                step = newStep;
                els.exportProgressText.textContent = CONFIG.exportSteps[step];
            }

            if (progress >= 100) {
                setTimeout(function () {
                    closeModal(els.exportModal);
                    // 模拟下载
                    showToast('数据已导出，正在下载...');

                    // 生成 JSON 文件并触发下载
                    var data = {
                        user: {
                            nickname: state.user.nickname,
                            typeCode: state.user.typeCode,
                            registerDate: state.user.registerDate
                        },
                        exportDate: new Date().toISOString(),
                        records: '（示例数据）'
                    };
                    var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'career_test_data_' + Date.now() + '.json';
                    a.click();
                    URL.revokeObjectURL(url);

                    trackEvent('data_export');
                }, 500);
            }
        }, 200);
    }

    // ========================================================
    //  8. 彻底删除账户（二次确认 + 7 日清除）
    // ========================================================
    function initDeleteAccount() {
        els.deleteAccountRow.addEventListener('click', function () {
            els.deleteConfirm.checked = false;
            els.deleteOk.disabled = true;
            openModal(els.deleteModal);
        });

        // 勾选确认后启用按钮
        els.deleteConfirm.addEventListener('change', function () {
            els.deleteOk.disabled = !els.deleteConfirm.checked;
        });

        // 确认删除
        els.deleteOk.addEventListener('click', function () {
            if (!els.deleteConfirm.checked) return;

            // 记录删除请求时间（7 日后清除）
            var deleteRequest = {
                requestedAt: new Date().toISOString(),
                scheduledPurge: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
            };
            localStorage.setItem('career_test_delete_request', JSON.stringify(deleteRequest));

            // 清除用户数据
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.removeItem(CONFIG.privacyKey);
            localStorage.removeItem('career_test_history');

            closeModal(els.deleteModal);

            trackEvent('account_delete_confirmed', {
                scheduledPurge: deleteRequest.scheduledPurge
            });

            showToast('账户删除请求已提交，7 日内清除所有数据');

            // 3 秒后跳转首页
            setTimeout(function () {
                window.location.href = 'index.html';
            }, 3000);
        });

        els.deleteCancel.addEventListener('click', function () {
            closeModal(els.deleteModal);
        });

        els.deleteOverlay.addEventListener('click', function () {
            closeModal(els.deleteModal);
        });
    }

    // ========================================================
    //  9. 退出登录
    // ========================================================
    function initLogout() {
        els.logoutBtn.addEventListener('click', function () {
            if (confirm('确认退出登录？')) {
                trackEvent('logout');
                showToast('已退出登录');
                setTimeout(function () {
                    window.location.href = 'index.html';
                }, 1000);
            }
        });
    }

    // ========================================================
    // 10. ESC 关闭弹窗
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;

            var modals = [els.nicknameModal, els.phoneModal, els.deleteModal, els.exportModal];
            for (var i = 0; i < modals.length; i++) {
                if (modals[i].classList.contains('modal--open')) {
                    closeModal(modals[i]);
                    return;
                }
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function openModal(modalEl) {
        modalEl.classList.add('modal--open');
        document.body.style.overflow = 'hidden';
    }

    function closeModal(modalEl) {
        modalEl.classList.remove('modal--open');
        document.body.style.overflow = '';
    }

    function trackEvent(eventName, data) {
        console.log('[Track]', eventName, data || {});
        // 后端接入后替换为真实埋点 API
        // fetch('/api/stats/track/', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ event: eventName, ...data })
        // });
    }

    var toastTimer = null;
    function showToast(message) {
        if (toastTimer) {
            clearTimeout(toastTimer);
        }

        els.toast.textContent = message;
        els.toast.classList.add('account-toast--visible');

        toastTimer = setTimeout(function () {
            els.toast.classList.remove('account-toast--visible');
        }, 2500);
    }

    // ========================================================
    // 初始化
    // ========================================================
    function init() {
        loadUser();
        loadPrivacy();
        initBackBtn();
        initAvatar();
        initNickname();
        initPhone();
        initPrivacy();
        initExport();
        initDeleteAccount();
        initLogout();
        initKeyboard();

        // 页面加载埋点
        trackEvent('account_page_view');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
