/**
 * result-free.js — 免费结果页交互脚本（对接后端 API）
 * 功能：从 API 加载测评结果、渲染三层标签、雷达图、色彩光谱、
 *       核心特质、社交建议、认证卡片、分享、深度报告预览
 * 依赖：api.js、share.js
 */
(function () {
    'use strict';

    // ============== 常量 ==============

    // OCEAN 五维色彩映射
    var OCEAN_COLORS = {
        'O': '#9B7ED8',
        'C': '#5a96b1',
        'E': '#5ea67e',
        'A': '#deb45c',
        'N': '#e17055'
    };

    var OCEAN_LABELS = {
        'O': '开放性 (O)',
        'C': '尽责性 (C)',
        'E': '外向性 (E)',
        'A': '宜人性 (A)',
        'N': '稳定性 (N\u2193)'
    };

    // RIASEC 特质映射
    var RIASEC_TRAITS = {
        'R': ['动手能力', '实践导向', '机械天赋'],
        'I': ['分析思维', '深度探索', '逻辑推理'],
        'A_': ['创意表达', '审美直觉', '自由发挥'], // 艺术型 A 与宜人性 A 区分
        'S': ['同理心', '团队协作', '助人成长'],
        'E_': ['领导力', '说服能力', '目标驱动'], // 企业型 E 与外向性 E 区分
        'C_': ['条理规划', '细节专注', '流程执行'] // 常规型 C 与尽责性 C 区分
    };

    // OCEAN 高分特质
    var OCEAN_HIGH_TRAITS = {
        'O': ['创新意识', '好奇心强'],
        'C': ['目标导向', '自律条理'],
        'E': ['社交活跃', '精力充沛'],
        'A': ['温暖包容', '合作共赢'],
        'N': ['敏感细腻']
    };

    // OCEAN 低分特质
    var OCEAN_LOW_TRAITS = {
        'O': ['务实稳健'],
        'C': ['灵活应变'],
        'E': ['独立深思'],
        'A': ['理性客观'],
        'N': ['冷静沉稳']
    };

    // ============== 状态 ==============
    var resultData = null;
    var sessionToken = '';

    // ============== DOM 元素引用 ==============
    var els = {
        radarCanvas: document.getElementById('radarCanvas'),
        nicknameInput: document.getElementById('nicknameInput'),
        cardNickname: document.getElementById('cardNickname'),
        templatePicker: document.getElementById('templatePicker'),
        certCard: document.getElementById('certCard'),
        saveCardBtn: document.getElementById('saveCardBtn'),
        shareBtns: document.querySelectorAll('.share-btn'),
        // Hero 区
        personalityCode: document.getElementById('personalityCode'),
        personalityTitle: document.getElementById('personalityTitle'),
        personalitySubtitle: document.getElementById('personalitySubtitle'),
        summaryText: document.getElementById('summaryText'),
        // 特质
        traitsCloud: document.getElementById('traitsCloud'),
        // 卡片
        cardCode: document.getElementById('cardCode'),
        cardSlogan: document.getElementById('cardSlogan'),
    };

    // ============== 工具函数 ==============
    function trackEvent(eventName, data) {
        // 埋点追踪：后端接入后替换为真实埋点 API
    }

    function showToast(message) {
        if (typeof Share !== 'undefined' && Share.showToast) {
            Share.showToast(message);
            return;
        }
        var toast = document.createElement('div');
        toast.style.cssText =
            'position:fixed;bottom:30%;left:50%;transform:translateX(-50%);' +
            'background:rgba(0,0,0,0.75);color:#fff;padding:12px 24px;border-radius:24px;' +
            'font-size:14px;z-index:9999;pointer-events:none;';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(function () { toast.remove(); }, 300);
        }, 2500);
    }

    /**
     * 从 API 响应映射到内部数据结构
     */
    function mapApiData(data) {
        var cardData = data.free_card_data || {};

        // 解析 OCEAN 分数
        var oceanScores = (data.ocean_scores || []).map(function (item) {
            var dim = item.dimension || item.key || item.dim || '';
            var pct = item.percentile != null ? item.percentile :
                      (item.score != null ? item.score : (item.value || 0));
            return {
                dimension: dim,
                percentile: Math.round(pct),
                color: OCEAN_COLORS[dim] || '#9B7ED8',
                label: OCEAN_LABELS[dim] || dim
            };
        });

        // 确保 5 个维度都有值
        var dims = ['O', 'C', 'E', 'A', 'N'];
        dims.forEach(function (d) {
            var found = oceanScores.find(function (s) { return s.dimension === d; });
            if (!found) {
                oceanScores.push({
                    dimension: d,
                    percentile: 50,
                    color: OCEAN_COLORS[d],
                    label: OCEAN_LABELS[d]
                });
            }
        });
        // 按 O C E A N 排序
        oceanScores.sort(function (a, b) {
            return dims.indexOf(a.dimension) - dims.indexOf(b.dimension);
        });

        // 构建 resultData
        return {
            code: (data.archetype_name || '') + '\u00b7' + (data.riasec_code || ''),
            title: data.archetype_name || '人格画像',
            slogan: (data.archetype_slogan || '') + ' \u00b7 职业兴趣码 ' + (data.riasec_code || ''),
            riasecCode: data.riasec_code || '',
            archetypeName: data.archetype_name || '',
            archetypeSlogan: data.archetype_slogan || '',
            summary: cardData.summary || generateSummary(data, oceanScores),
            dimensions: oceanScores.map(function (s) {
                return {
                    label: s.label,
                    value: s.percentile,
                    color: s.color,
                    dimension: s.dimension
                };
            }),
            oceanScores: oceanScores,
            colorSpectrum: data.color_spectrum || generateColorSpectrum(oceanScores),
            rarity: cardData.rarity || (data.confidence ? (data.confidence * 5).toFixed(2) + '%' : '3.13%'),
            rarityLabel: cardData.rarity_label || '稀有',
            famousPeople: cardData.famous_people || cardData.famousPeople || '\u2014',
            bestPartners: cardData.best_partners || cardData.bestPartners || [],
            confidence: data.confidence || 0,
            isValid: data.is_valid !== false,
            freeCardData: cardData
        };
    }

    /**
     * 生成色彩光谱（如果 API 未返回）
     */
    function generateColorSpectrum(oceanScores) {
        var dots = oceanScores.map(function (s) {
            var level = Math.ceil(s.percentile / 20);
            if (level < 1) level = 1;
            if (level > 5) level = 5;
            return {
                dimension: s.dimension,
                color: s.color,
                level: level
            };
        });
        return {
            dots: dots,
            visual: '\u25cf\u25cf\u25cf\u25cf\u25cf'
        };
    }

    /**
     * 生成默认总结文案
     */
    function generateSummary(data, oceanScores) {
        var name = data.archetype_name || '你';
        var slogan = data.archetype_slogan || '';
        return '你是一位' + (slogan || '独特的个体') + '，在' + name +
               '的人格特质下，你的大五人格与职业兴趣形成了独特的组合，' +
               '为你的人生与职业发展提供了清晰的方向参考。';
    }

    // ============== 1. 渲染三层标签（画像名、RIASEC码、色彩光谱） ==============
    function renderHero(data) {
        // 画像名 + RIASEC 码
        if (els.personalityCode) {
            els.personalityCode.textContent = data.code;
        }
        if (els.personalityTitle) {
            els.personalityTitle.textContent = data.title;
        }
        if (els.personalitySubtitle) {
            els.personalitySubtitle.textContent = data.slogan;
        }

        // 更新 segments
        var segments = document.querySelectorAll('.result-hero__segments .segment');
        if (segments.length >= 3) {
            segments[0].textContent = data.riasecCode;   // .segment--base
            segments[1].textContent = data.title;          // .segment--sub1
            // segments[2] 是色彩光谱，由 renderColorSpectrum 处理
        }

        // 总结文案
        if (els.summaryText) {
            els.summaryText.textContent = data.summary;
        }

        // 卡片编码和口号
        if (els.cardCode) {
            els.cardCode.textContent = data.code;
        }
        if (els.cardSlogan) {
            els.cardSlogan.textContent = data.slogan;
        }
    }

    // ============== 2. 色彩光谱渲染 ==============
    function renderColorSpectrum(spectrum) {
        // 更新 hero 区的色彩光谱 segment
        var spectrumSegment = document.querySelectorAll('.result-hero__segments .segment')[2];
        if (spectrumSegment && spectrum && spectrum.dots) {
            var dotsHtml = spectrum.dots.map(function (dot) {
                var size = 10 + (dot.level || 3) * 3;
                var opacity = 0.4 + (dot.level || 3) * 0.15;
                return '<span style="display:inline-block;width:' + size + 'px;height:' + size +
                       'px;border-radius:50%;background:' + (dot.color || '#9B7ED8') +
                       ';opacity:' + opacity + ';margin:0 2px;vertical-align:middle;"></span>';
            }).join('');
            spectrumSegment.innerHTML = dotsHtml;
            spectrumSegment.style.fontSize = '0';
        }

        // 在认证卡区域也添加色彩光谱
        var cardCodeArea = document.querySelector('.cert-card__code-area');
        if (cardCodeArea && spectrum && spectrum.dots) {
            // 移除已有的光谱
            var existing = cardCodeArea.querySelector('.cert-card__spectrum');
            if (existing) existing.remove();

            var spectrumDiv = document.createElement('div');
            spectrumDiv.className = 'cert-card__spectrum';
            spectrumDiv.style.cssText =
                'display:flex;justify-content:center;gap:8px;margin-top:12px;';

            spectrum.dots.forEach(function (dot) {
                var dotEl = document.createElement('span');
                var size = 12 + (dot.level || 3) * 3;
                dotEl.style.cssText =
                    'display:inline-block;width:' + size + 'px;height:' + size +
                    'px;border-radius:50%;background:' + (dot.color || '#9B7ED8') +
                    ';box-shadow:0 2px 6px ' + (dot.color || '#9B7ED8') + '40;';
                spectrumDiv.appendChild(dotEl);
            });

            cardCodeArea.appendChild(spectrumDiv);
        }
    }

    // ============== 3. 雷达图绘制 ==============
    function drawRadar(dimensions) {
        var canvas = els.radarCanvas;
        if (!canvas || !dimensions || dimensions.length === 0) return;

        var ctx = canvas.getContext('2d');
        var dpr = window.devicePixelRatio || 1;
        var size = 320;
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';
        ctx.scale(dpr, dpr);

        var cx = size / 2;
        var cy = size / 2;
        var maxRadius = 110;
        var sides = dimensions.length;
        var angleStep = (Math.PI * 2) / sides;
        var startAngle = -Math.PI / 2;

        // 背景网格（4 层同心多边形）
        ctx.strokeStyle = '#e7eae8';
        ctx.lineWidth = 1;
        for (var layer = 1; layer <= 4; layer++) {
            var r = (maxRadius / 4) * layer;
            ctx.beginPath();
            for (var i = 0; i <= sides; i++) {
                var angle = startAngle + angleStep * i;
                var x = cx + Math.cos(angle) * r;
                var y = cy + Math.sin(angle) * r;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }

        // 轴线
        ctx.strokeStyle = '#e7eae8';
        for (var j = 0; j < sides; j++) {
            var a = startAngle + angleStep * j;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(a) * maxRadius, cy + Math.sin(a) * maxRadius);
            ctx.stroke();
        }

        // 数据填充
        ctx.beginPath();
        for (var k = 0; k < sides; k++) {
            var dataAngle = startAngle + angleStep * k;
            var dataRadius = (dimensions[k].value / 100) * maxRadius;
            var px = cx + Math.cos(dataAngle) * dataRadius;
            var py = cy + Math.sin(dataAngle) * dataRadius;
            if (k === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();

        // 渐变填充
        var gradient = ctx.createLinearGradient(
            cx - maxRadius, cy - maxRadius, cx + maxRadius, cy + maxRadius
        );
        gradient.addColorStop(0, 'rgba(155, 126, 216, 0.25)');
        gradient.addColorStop(1, 'rgba(90, 150, 177, 0.25)');
        ctx.fillStyle = gradient;
        ctx.fill();

        // 数据边线
        ctx.strokeStyle = '#9B7ED8';
        ctx.lineWidth = 2;
        ctx.stroke();

        // 数据点（各维度专属色）
        for (var m = 0; m < sides; m++) {
            var ptAngle = startAngle + angleStep * m;
            var ptRadius = (dimensions[m].value / 100) * maxRadius;
            var ptX = cx + Math.cos(ptAngle) * ptRadius;
            var ptY = cy + Math.sin(ptAngle) * ptRadius;

            ctx.beginPath();
            ctx.arc(ptX, ptY, 5, 0, Math.PI * 2);
            ctx.fillStyle = dimensions[m].color;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // 标签
        ctx.font = '600 13px Inter, "PingFang SC", sans-serif';
        ctx.fillStyle = '#2d2d3a';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        for (var n = 0; n < sides; n++) {
            var lblAngle = startAngle + angleStep * n;
            var lblRadius = maxRadius + 25;
            var lblX = cx + Math.cos(lblAngle) * lblRadius;
            var lblY = cy + Math.sin(lblAngle) * lblRadius;
            ctx.fillText(dimensions[n].label, lblX, lblY);
        }
    }

    // ============== 4. 更新雷达图图例 ==============
    function updateRadarLegend(dimensions) {
        var legendItems = document.querySelectorAll('.legend-item');
        dimensions.forEach(function (dim, idx) {
            if (legendItems[idx]) {
                var dot = legendItems[idx].querySelector('.legend-dot');
                var label = legendItems[idx].querySelector('.legend-label');
                if (dot) {
                    dot.style.background = dim.color;
                }
                if (label) {
                    label.innerHTML = dim.label + ' <strong>' + dim.value + '%</strong>';
                }
            }
        });
    }

    // ============== 5. 核心特质标签生成 ==============
    function renderTraits(data) {
        if (!els.traitsCloud) return;

        var traits = [];
        var sizes = ['trait-tag--lg', 'trait-tag--md', 'trait-tag--sm', 'trait-tag--md', 'trait-tag--lg',
                      'trait-tag--sm', 'trait-tag--md', 'trait-tag--sm', 'trait-tag--md', 'trait-tag--sm'];
        var colorKeys = ['#5a96b1', '#87699a', '#deb45c', '#5ea67e', '#9B7ED8',
                         '#e17055', '#5a96b1', '#deb45c', '#87699a', '#5ea67e'];

        // 如果 API 返回了特质数据，直接使用
        if (data.freeCardData && data.freeCardData.traits && data.freeCardData.traits.length > 0) {
            traits = data.freeCardData.traits;
        } else {
            // 基于 RIASEC 码生成特质
            var riasecCode = data.riasecCode || '';
            var usedTraits = {};

            // RIASEC 前三个字母对应的特质
            for (var i = 0; i < riasecCode.length && i < 3; i++) {
                var letter = riasecCode[i];
                var key = (letter === 'A') ? 'A_' : (letter === 'E') ? 'E_' : (letter === 'C') ? 'C_' : letter;
                var traitList = RIASEC_TRAITS[key] || RIASEC_TRAITS[letter] || [];
                traitList.forEach(function (t) {
                    if (!usedTraits[t] && traits.length < 6) {
                        traits.push(t);
                        usedTraits[t] = true;
                    }
                });
            }

            // 基于 OCEAN 高分维度补充特质
            data.oceanScores.forEach(function (s) {
                if (s.percentile >= 65 && traits.length < 10) {
                    var highTraits = OCEAN_HIGH_TRAITS[s.dimension] || [];
                    highTraits.forEach(function (t) {
                        if (!usedTraits[t] && traits.length < 10) {
                            traits.push(t);
                            usedTraits[t] = true;
                        }
                    });
                } else if (s.percentile <= 35 && traits.length < 10) {
                    var lowTraits = OCEAN_LOW_TRAITS[s.dimension] || [];
                    lowTraits.forEach(function (t) {
                        if (!usedTraits[t] && traits.length < 10) {
                            traits.push(t);
                            usedTraits[t] = true;
                        }
                    });
                }
            });

            // 如果特质不够，补充默认
            var defaults = ['深度思考', '冷静沉着', '高标准'];
            defaults.forEach(function (t) {
                if (!usedTraits[t] && traits.length < 8) {
                    traits.push(t);
                    usedTraits[t] = true;
                }
            });
        }

        // 渲染
        els.traitsCloud.innerHTML = '';
        traits.forEach(function (trait, idx) {
            var span = document.createElement('span');
            var sizeClass = sizes[idx % sizes.length];
            var color = colorKeys[idx % colorKeys.length];
            span.className = 'trait-tag ' + sizeClass;
            span.style.setProperty('--tag-color', color);
            span.textContent = trait;
            els.traitsCloud.appendChild(span);
        });
    }

    // ============== 6. 社交建议生成 ==============
    function renderSocialTips(data) {
        var tipsContainer = document.querySelector('.result-social-tips__list');
        if (!tipsContainer) return;

        // 如果 API 返回了社交建议
        if (data.freeCardData && data.freeCardData.social_tips &&
            data.freeCardData.social_tips.length > 0) {
            tipsContainer.innerHTML = '';
            data.freeCardData.social_tips.forEach(function (tip) {
                tipsContainer.appendChild(createSocialTipElement(tip));
            });
            return;
        }

        // 基于 OCEAN 分数生成社交建议
        var oceanMap = {};
        data.oceanScores.forEach(function (s) {
            oceanMap[s.dimension] = s.percentile;
        });

        var tips = [];

        // 团队协作（基于 E 和 A）
        if ((oceanMap['E'] || 50) < 50) {
            tips.push({
                title: '团队协作',
                desc: '你更擅长独立深度工作，但在团队中应主动分享你的战略视角，帮助团队看清方向。',
                color: '#5a96b1'
            });
        } else {
            tips.push({
                title: '团队协作',
                desc: '你善于在团队中发挥主动性，适当倾听他人意见能让你的领导力更加全面。',
                color: '#5a96b1'
            });
        }

        // 沟通方式（基于 A）
        if ((oceanMap['A'] || 50) < 50) {
            tips.push({
                title: '沟通方式',
                desc: '偏好直接、有逻辑的交流。在表达观点时适当增加情感共鸣，能让你的建议更易被接受。',
                color: '#87699a'
            });
        } else {
            tips.push({
                title: '沟通方式',
                desc: '你善于照顾他人感受，在需要时可以更直接地表达自己的需求与边界。',
                color: '#87699a'
            });
        }

        // 社交节奏（基于 E）
        if ((oceanMap['E'] || 50) < 50) {
            tips.push({
                title: '社交节奏',
                desc: '你需要充足的独处时间恢复能量。建议将社交活动安排在精力充沛时段，不要过度勉强自己。',
                color: '#deb45c'
            });
        } else {
            tips.push({
                title: '社交节奏',
                desc: '你在社交中获得能量，但也要注意留出独处时间进行深度思考和自我充电。',
                color: '#deb45c'
            });
        }

        tipsContainer.innerHTML = '';
        tips.forEach(function (tip) {
            tipsContainer.appendChild(createSocialTipElement(tip));
        });
    }

    function createSocialTipElement(tip) {
        var div = document.createElement('div');
        div.className = 'social-tip';

        var icon = document.createElement('div');
        icon.className = 'social-tip__icon';
        icon.style.background = tip.color || '#9B7ED8';
        icon.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" stroke-width="2">' +
                         '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';

        var content = document.createElement('div');
        content.className = 'social-tip__content';
        content.innerHTML = '<strong>' + (tip.title || '') + '</strong>' +
                           '<p>' + (tip.desc || tip.description || '') + '</p>';

        div.appendChild(icon);
        div.appendChild(content);
        return div;
    }

    // ============== 7. 更新认证卡信息 ==============
    function updateCertCard(data) {
        // 稀有度
        var infoItems = document.querySelectorAll('.cert-card__info-item');
        if (infoItems.length >= 3) {
            // 稀有度
            var rarityValue = infoItems[0].querySelector('.cert-card__info-value');
            var rarityBadge = infoItems[0].querySelector('.cert-card__info-badge');
            if (rarityValue) rarityValue.textContent = data.rarity;
            if (rarityBadge) rarityBadge.textContent = data.rarityLabel;

            // 相同人格名人
            var famousValue = infoItems[1].querySelector('.cert-card__info-value');
            if (famousValue) famousValue.textContent = data.famousPeople;

            // 最佳搭子
            var partnersContainer = infoItems[2].querySelector('.cert-card__partners');
            if (partnersContainer && data.bestPartners.length > 0) {
                partnersContainer.innerHTML = '';
                data.bestPartners.forEach(function (partner) {
                    var pill = document.createElement('span');
                    pill.className = 'partner-pill';
                    pill.textContent = partner;
                    partnersContainer.appendChild(pill);
                });
            }
        }
    }

    // ============== 8. 昵称同步 ==============
    function initNicknameSync() {
        if (!els.nicknameInput || !els.cardNickname) return;

        els.nicknameInput.addEventListener('input', function () {
            var val = els.nicknameInput.value.trim() || '匿名用户001';
            els.cardNickname.textContent = val;
        });
    }

    // ============== 9. 模板切换 ==============
    function initTemplateSwitch() {
        if (!els.templatePicker || !els.certCard) return;

        els.templatePicker.addEventListener('click', function (e) {
            var btn = e.target.closest('.template-btn');
            if (!btn) return;

            els.templatePicker.querySelectorAll('.template-btn').forEach(function (b) {
                b.classList.remove('template-btn--active');
            });
            btn.classList.add('template-btn--active');

            var template = btn.getAttribute('data-template');
            els.certCard.setAttribute('data-template', template);
        });
    }

    // ============== 10. 保存卡片（集成 Share 模块） ==============
    function initSaveCard() {
        if (!els.saveCardBtn) return;

        els.saveCardBtn.addEventListener('click', function () {
            if (typeof Share !== 'undefined' && Share.saveCard) {
                Share.saveCard({
                    code: resultData.code,
                    title: resultData.title,
                    slogan: resultData.slogan,
                    rarity: resultData.rarity,
                    rarityLabel: resultData.rarityLabel,
                    famousPeople: resultData.famousPeople,
                    bestPartners: resultData.bestPartners,
                    colorSpectrum: resultData.colorSpectrum
                });
            }
            trackEvent('card_save', { code: resultData.code });
        });
    }

    // ============== 11. 分享按钮（集成 Share 模块） ==============
    function initShare() {
        if (!els.shareBtns.length) return;

        // 初始化 Share 模块
        if (typeof Share !== 'undefined' && Share.init) {
            Share.init({
                code: resultData ? resultData.code : '',
                title: resultData ? resultData.title : '',
                slogan: resultData ? resultData.slogan : '',
                sessionToken: sessionToken,
                certCard: els.certCard,
                nicknameInput: els.nicknameInput
            });
        }

        els.shareBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var channel = btn.getAttribute('data-channel');

                trackEvent('share_click', {
                    channel: channel,
                    code: resultData ? resultData.code : ''
                });

                if (typeof Share !== 'undefined') {
                    if (channel === 'wechat_friend') {
                        Share.shareFriend();
                    } else if (channel === 'wechat_moments') {
                        Share.shareMoment();
                    } else if (channel === 'weibo') {
                        Share.shareWeibo();
                    }
                } else {
                    // Share 模块未加载时的降级处理
                    if (channel === 'weibo') {
                        var shareUrl = encodeURIComponent(window.location.href);
                        var shareText = encodeURIComponent(
                            '我的职业人格画像是 ' + (resultData ? resultData.code : '') +
                            '！来画己职测，发现你的职业人格画像~'
                        );
                        window.open(
                            'https://service.weibo.com/share/share.php?url=' + shareUrl + '&title=' + shareText,
                            '_blank'
                        );
                    } else {
                        showToast('请在微信中打开以分享给好友');
                    }
                }
            });
        });
    }

    // ============== 12. 更新免责声明 ==============
    function updateDisclaimer() {
        var disclaimerP = document.querySelector('.disclaimer-box p');
        if (disclaimerP) {
            disclaimerP.textContent =
                '基于 IPIP 大五人格量表与霍兰德 RIASEC 理论综合推导，' +
                '仅供自我探索与职业参考，不作为临床诊断依据。';
        }
    }

    // ============== 13. 更新深度报告预览中的画像名 ==============
    function updateDeepPreview(data) {
        var previewChapters = document.querySelectorAll('.deep-preview__chapter');
        if (previewChapters.length > 0) {
            var firstChapterP = previewChapters[0].querySelector('p');
            if (firstChapterP) {
                firstChapterP.textContent = data.code + ' — 深入解析你的大五人格五维度组合，' +
                    '揭示 O-C-E-A-N 的运作机制与深层驱动力\u2026';
            }
        }
    }

    // ============== 加载状态 ==============
    function showLoading() {
        var main = document.querySelector('.result-main');
        if (!main) return;

        var loader = document.createElement('div');
        loader.id = 'resultLoader';
        loader.style.cssText =
            'position:fixed;inset:0;background:#f9f9f9;display:flex;' +
            'flex-direction:column;align-items:center;justify-content:center;z-index:999;';
        loader.innerHTML =
            '<div style="width:48px;height:48px;border:4px solid #e7eae8;' +
            'border-top-color:#9B7ED8;border-radius:50%;' +
            'animation:spin 0.8s linear infinite;"></div>' +
            '<p style="margin-top:20px;font-size:15px;color:#636e72;font-family:Inter,sans-serif;">' +
            '正在加载你的测评结果\u2026</p>' +
            '<style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
        document.body.appendChild(loader);
    }

    function hideLoading() {
        var loader = document.getElementById('resultLoader');
        if (loader) loader.remove();
    }

    // ============== 错误处理 ==============
    function showError(message) {
        hideLoading();

        var main = document.querySelector('.result-main');
        if (!main) return;

        var errorEl = document.createElement('div');
        errorEl.style.cssText =
            'max-width:600px;margin:60px auto;padding:48px 24px;text-align:center;' +
            'background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.04);';
        errorEl.innerHTML =
            '<div style="font-size:48px;margin-bottom:16px;color:#e17055;">!</div>' +
            '<h2 style="font-size:22px;font-weight:700;color:#2d2d3a;margin-bottom:12px;">结果加载失败</h2>' +
            '<p style="font-size:14px;color:#636e72;margin-bottom:28px;line-height:1.6;">' +
            (message || '无法加载测评结果，请稍后重试') + '</p>' +
            '<div style="display:flex;gap:12px;justify-content:center;">' +
            '<a href="/question/" style="padding:12px 32px;border:none;border-radius:24px;' +
            'background:linear-gradient(135deg,#9B7ED8,#B8A4E0);color:#fff;font-size:15px;' +
            'font-weight:700;text-decoration:none;display:inline-block;">重新测试</a>' +
            '<button onclick="location.reload()" style="padding:12px 32px;border:2px solid #e7eae8;' +
            'border-radius:24px;background:#fff;color:#636e72;font-size:15px;font-weight:600;cursor:pointer;">' +
            '重试加载</button>' +
            '</div>';
        main.innerHTML = '';
        main.appendChild(errorEl);
    }

    // ============== 渲染所有结果 ==============
    function renderResult(data) {
        // 1. 三层标签 + Hero
        renderHero(data);

        // 2. 色彩光谱
        renderColorSpectrum(data.colorSpectrum);

        // 3. 雷达图
        drawRadar(data.dimensions);
        updateRadarLegend(data.dimensions);

        // 4. 核心特质
        renderTraits(data);

        // 5. 社交建议
        renderSocialTips(data);

        // 6. 认证卡信息
        updateCertCard(data);

        // 7. 更新免责声明
        updateDisclaimer();

        // 8. 更新深度报告预览
        updateDeepPreview(data);

        // 9. 初始化交互
        initNicknameSync();
        initTemplateSwitch();
        initSaveCard();
        initShare();

        // 页面加载埋点
        trackEvent('result_page_view', { code: data.code });
    }

    // ============== 从 URL 获取 session_token ==============
    function getSessionTokenFromUrl() {
        var params = new URLSearchParams(window.location.search);
        return params.get('session_token') || '';
    }

    // ============== 主流程 ==============
    function loadResult() {
        sessionToken = getSessionTokenFromUrl();

        if (!sessionToken) {
            // 尝试从 localStorage 获取
            if (typeof API !== 'undefined') {
                sessionToken = API.getSessionToken();
            }
        }

        if (!sessionToken) {
            showError('未找到测评结果，请先完成测试。');
            return;
        }

        showLoading();

        API.getAssessmentResult(sessionToken)
            .then(function (data) {
                hideLoading();

                if (!data || data.is_valid === false) {
                    showError('测评结果无效或已过期，请重新测试。');
                    return;
                }

                resultData = mapApiData(data);
                renderResult(resultData);
            })
            .catch(function (err) {
                showError(err.message || '无法连接到服务器');
            });
    }

    // ============== 初始化 ==============
    function init() {
        if (typeof API === 'undefined') {
            showError('API 模块加载失败，请刷新页面重试。');
            return;
        }

        loadResult();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
