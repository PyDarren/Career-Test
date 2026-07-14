/**
 * share.js — 画己职测 分享功能模块
 * 功能：保存认证卡为 PNG、微信分享、复制链接
 * 依赖：原生 Canvas API、可选微信 JS-SDK
 */
var Share = (function () {
    'use strict';

    // ============== 内部配置 ==============
    var config = {
        code: '',            // 人格编码 (如 "沉稳架构师·IRC")
        title: '',           // 画像名 (如 "沉稳架构师")
        slogan: '',          // 口号
        sessionToken: '',    // 会话 token
        certCard: null,      // 认证卡 DOM 元素
        nicknameInput: null, // 昵称输入框 DOM 元素
        shareUrl: '',        // 分享链接
    };

    // ============== 卡片模板配色 ==============
    var templateColors = {
        lavender: {
            bg: ['#E8E0F0', '#FAF8FC', '#F5F0FA'],
            ribbon: '#9B7ED8',
            partner: '#9B7ED8',
        },
        ocean: {
            bg: ['#D0E8F0', '#F0F8FA', '#E8F4F8'],
            ribbon: '#4A6FA5',
            partner: '#4A6FA5',
        },
        sunset: {
            bg: ['#FDE8D0', '#FFF8F0', '#FFF4E8'],
            ribbon: '#E0A93A',
            partner: '#E0A93A',
        },
    };

    // ============== 工具函数 ==============
    function showToast(message) {
        var existing = document.getElementById('share-toast');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.id = 'share-toast';
        toast.style.cssText =
            'position:fixed;bottom:30%;left:50%;transform:translateX(-50%);' +
            'background:rgba(0,0,0,0.78);color:#fff;padding:12px 28px;border-radius:28px;' +
            'font-size:14px;z-index:99999;pointer-events:none;transition:opacity 0.3s ease;' +
            'font-family:Inter,"PingFang SC",sans-serif;max-width:80vw;text-align:center;';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            setTimeout(function () {
                if (toast.parentNode) toast.remove();
            }, 300);
        }, 2500);
    }

    function trackEvent(eventName, data) {
        // 埋点追踪：后端接入后替换为真实埋点 API
    }

    function getTemplate() {
        if (config.certCard) {
            return config.certCard.getAttribute('data-template') || 'lavender';
        }
        return 'lavender';
    }

    function getNickname() {
        if (config.nicknameInput) {
            var val = config.nicknameInput.value.trim();
            return val || '匿名用户001';
        }
        return '匿名用户001';
    }

    // ============== 圆角矩形辅助（兼容旧浏览器） ==============
    function roundRect(ctx, x, y, w, h, r) {
        if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(x, y, w, h, r);
            return;
        }
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    // ============== 1. 保存认证卡为 PNG ==============
    function saveCardAsImage(cardData) {
        // cardData 为可选参数，如果不传则使用 config 中的数据
        var data = cardData || {};
        var code = data.code || config.code || '人格画像';
        var slogan = data.slogan || config.slogan || '';
        var rarity = data.rarity || '3.13%';
        var rarityLabel = data.rarityLabel || '稀有';
        var famousPeople = data.famousPeople || '—';
        var bestPartners = data.bestPartners || [];
        var colorSpectrum = data.colorSpectrum || null;
        var template = getTemplate();
        var colors = templateColors[template] || templateColors.lavender;
        var nickname = getNickname();

        var canvas = document.createElement('canvas');
        var W = 1080;
        var H = 1620;
        canvas.width = W;
        canvas.height = H;
        var ctx = canvas.getContext('2d');

        // --- 背景 ---
        var bgGrad = ctx.createLinearGradient(0, 0, W, H);
        bgGrad.addColorStop(0, colors.bg[0]);
        bgGrad.addColorStop(0.5, colors.bg[1]);
        bgGrad.addColorStop(1, colors.bg[2]);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, W, H);

        // --- 缎带 ---
        ctx.fillStyle = colors.ribbon;
        ctx.fillRect(W / 2 - 70, 0, 55, 90);
        ctx.fillStyle = '#7DD3C0';
        ctx.fillRect(W / 2 + 15, 0, 55, 90);

        // --- 标题 ---
        ctx.fillStyle = '#2D2D3A';
        ctx.font = '700 44px "Nunito", "PingFang SC", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('我的人格认证卡', W / 2, 170);

        // --- 已认证徽章 ---
        ctx.fillStyle = '#F5D547';
        ctx.font = '700 26px "Nunito", sans-serif';
        ctx.fillText('\u2713 已认证', W / 2, 220);

        // --- 人格编码 ---
        ctx.font = '600 108px "Montserrat", sans-serif';
        ctx.fillStyle = colors.ribbon;
        ctx.fillText(code, W / 2, 370);

        // --- 口号 ---
        ctx.font = '400 34px "Nunito", "PingFang SC", sans-serif';
        ctx.fillStyle = '#636e72';
        ctx.fillText(slogan, W / 2, 440);

        // --- 色彩光谱 ---
        if (colorSpectrum && colorSpectrum.dots) {
            var dotY = 510;
            var dotSpacing = 80;
            var dotStartX = W / 2 - (colorSpectrum.dots.length - 1) * dotSpacing / 2;
            colorSpectrum.dots.forEach(function (dot, idx) {
                var dotR = 16 + (dot.level || 3) * 4;
                ctx.beginPath();
                ctx.arc(dotStartX + idx * dotSpacing, dotY, dotR, 0, Math.PI * 2);
                ctx.fillStyle = dot.color || '#9B7ED8';
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 3;
                ctx.stroke();
            });
        }

        // --- 分割线 ---
        ctx.strokeStyle = 'rgba(155, 126, 216, 0.2)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(100, 570);
        ctx.lineTo(W - 100, 570);
        ctx.stroke();

        // --- 信息区 ---
        ctx.textAlign = 'left';
        ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = '#9B9BAB';
        ctx.fillText('人格稀有度', 120, 640);
        ctx.font = '700 50px "Montserrat", sans-serif';
        ctx.fillStyle = '#2D2D3A';
        ctx.fillText(rarity, 120, 700);
        ctx.font = '700 24px "Nunito", sans-serif';
        ctx.fillStyle = colors.ribbon;
        ctx.fillText(rarityLabel, 320, 695);

        ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = '#9B9BAB';
        ctx.fillText('相同人格名人', 120, 790);
        ctx.font = '600 32px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = '#2D2D3A';
        ctx.fillText(famousPeople, 120, 840);

        ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = '#9B9BAB';
        ctx.fillText('最佳搭子', 120, 930);
        bestPartners.forEach(function (partner, idx) {
            var pillX = 120 + idx * 200;
            var pillY = 950;
            ctx.fillStyle = colors.partner;
            roundRect(ctx, pillX, pillY, 170, 56, 28);
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = '600 26px "Montserrat", sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(partner, pillX + 85, pillY + 36);
            ctx.textAlign = 'left';
        });

        // --- 昵称 ---
        ctx.font = '400 30px "Nunito", "PingFang SC", sans-serif';
        ctx.fillStyle = '#636e72';
        ctx.textAlign = 'left';
        ctx.fillText(nickname, 120, 1100);

        // --- 品牌水印 ---
        ctx.font = '600 24px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = 'rgba(155, 126, 216, 0.5)';
        ctx.textAlign = 'center';
        ctx.fillText('画己职测 · 发现你的职业人格画像', W / 2, 1480);

        // --- 底部提示 ---
        ctx.font = '400 22px "Inter", "PingFang SC", sans-serif';
        ctx.fillStyle = '#9B9BAB';
        ctx.fillText('扫描二维码查看完整报告', W / 2, 1540);

        // --- 触发下载 ---
        var link = document.createElement('a');
        link.download = '画己职测-' + code + '-' + nickname + '.png';
        link.href = canvas.toDataURL('image/png');
        link.click();

        trackEvent('card_save', { template: template, code: code });
        showToast('认证卡已保存到相册');
    }

    // ============== 2. 微信好友分享 ==============
    function shareToWechatFriend() {
        var shareUrl = config.shareUrl || window.location.href;
        var shareTitle = '我的职业人格画像是 ' + config.title;
        var shareDesc = '来画己职测，发现你的职业人格画像与兴趣方向';

        // 微信 JS-SDK 环境
        if (typeof wx !== 'undefined' && typeof wx.updateAppMessageShareData === 'function') {
            wx.updateAppMessageShareData({
                title: shareTitle,
                desc: shareDesc,
                link: shareUrl,
                imgUrl: window.location.origin + '/static/assets/images/职业测评 LOGO 透明.png',
                success: function () {
                    showToast('分享内容已准备，请点击右上角分享');
                },
            });
        } else if (typeof wx !== 'undefined' && typeof wx.miniProgram !== 'undefined') {
            // 微信小程序环境
            wx.miniProgram.postMessage({
                data: {
                    type: 'share_friend',
                    title: shareTitle,
                    path: shareUrl,
                },
            });
            showToast('请点击右上角 ··· 分享给好友');
        } else {
            // 非微信环境：复制链接
            copyShareLink();
            showToast('链接已复制，请在微信中粘贴分享给好友');
        }

        trackEvent('share_click', { channel: 'wechat_friend', code: config.code });
    }

    // ============== 3. 微信朋友圈分享 ==============
    function shareToWechatMoment() {
        var shareUrl = config.shareUrl || window.location.href;
        var shareTitle = '我的职业人格画像是 ' + config.title + '！来测测你的吧~';

        if (typeof wx !== 'undefined' && typeof wx.updateTimelineShareData === 'function') {
            wx.updateTimelineShareData({
                title: shareTitle,
                link: shareUrl,
                imgUrl: window.location.origin + '/static/assets/images/职业测评 LOGO 透明.png',
                success: function () {
                    showToast('分享内容已准备，请点击右上角分享到朋友圈');
                },
            });
        } else if (typeof wx !== 'undefined' && typeof wx.miniProgram !== 'undefined') {
            wx.miniProgram.postMessage({
                data: {
                    type: 'share_moment',
                    title: shareTitle,
                    path: shareUrl,
                },
            });
            showToast('请点击右上角 ··· 分享到朋友圈');
        } else {
            copyShareLink();
            showToast('链接已复制，请在微信中粘贴分享到朋友圈');
        }

        trackEvent('share_click', { channel: 'wechat_moments', code: config.code });
    }

    // ============== 4. 微博分享 ==============
    function shareToWeibo() {
        var shareUrl = encodeURIComponent(config.shareUrl || window.location.href);
        var shareText = encodeURIComponent(
            '我的职业人格画像是 ' + config.code + ' ' + config.title + '！来画己职测，发现你的职业人格画像~'
        );
        window.open(
            'https://service.weibo.com/share/share.php?url=' + shareUrl + '&title=' + shareText,
            '_blank'
        );
        trackEvent('share_click', { channel: 'weibo', code: config.code });
    }

    // ============== 5. 复制分享链接 ==============
    function copyShareLink() {
        var link = config.shareUrl || window.location.href;

        // 优先使用 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(link).then(function () {
                showToast('分享链接已复制');
            }).catch(function () {
                fallbackCopy(link);
            });
        } else {
            fallbackCopy(link);
        }

        trackEvent('share_click', { channel: 'copy_link', code: config.code });
    }

    function fallbackCopy(text) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.cssText =
            'position:fixed;left:-9999px;top:-9999px;opacity:0;';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('分享链接已复制');
        } catch (e) {
            showToast('复制失败，请手动复制链接');
        }
        document.body.removeChild(textarea);
    }

    // ============== 初始化 ==============
    function init(options) {
        config.code = options.code || '';
        config.title = options.title || '';
        config.slogan = options.slogan || '';
        config.sessionToken = options.sessionToken || '';
        config.certCard = options.certCard || null;
        config.nicknameInput = options.nicknameInput || null;

        // 构建分享链接
        var origin = window.location.origin || '';
        var path = window.location.pathname.replace(/[^/]*$/, '');
        if (config.sessionToken) {
            config.shareUrl = origin + '/?ref=' + config.sessionToken;
        } else {
            config.shareUrl = window.location.href;
        }
    }

    return {
        init: init,
        saveCard: saveCardAsImage,
        shareFriend: shareToWechatFriend,
        shareMoment: shareToWechatMoment,
        shareWeibo: shareToWeibo,
        copyLink: copyShareLink,
        showToast: showToast,
    };
})();
