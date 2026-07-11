"""
Preview views with mock data.
"""
from django.shortcuts import render


def landing(request):
    return render(request, 'assessment/landing.html')


def guide(request):
    return render(request, 'assessment/guide.html', {
        'estimated_duration': '12 分钟',
        'question_count': 86,
    })


def question(request):
    return render(request, 'assessment/question.html', {
        'current_index': 34,
        'total_questions': 86,
        'question': {
            'text': '在团队讨论中，你更倾向于：',
            'option_a': '直接提出想法并推动决策',
            'option_b': '先倾听他人意见再谨慎表态',
            'option_a_text': '主动表达',
            'option_b_text': '倾听思考',
        },
    })


def free_result(request):
    return render(request, 'result/free_result.html', {
        'result': {
            'full_code': 'INTJ-A-C',
            'type_code': 'INTJ',
            'type_name': '建筑师',
            'type_slogan': '智慧的先锋，未来的建筑师',
            'nickname': '匿名用户SK3',
            'rarity': '2.70%',
            'rarity_label': '超稀有人格',
            'famous_people': '比尔·盖茨、伊隆·马斯克',
            'best_partners_list': ['INTP', 'ENTP', 'ENFP'],
            'dimensions': [
                {'label': 'E/I', 'percent': '72% I', 'left': '外向', 'right': '内向'},
                {'label': 'S/N', 'percent': '68% N', 'left': '实感', 'right': '直觉'},
                {'label': 'T/F', 'percent': '81% T', 'left': '思考', 'right': '情感'},
                {'label': 'J/P', 'percent': '64% J', 'left': '判断', 'right': '感知'},
            ],
            'core_traits': [
                '战略思维 — 善于长远规划，看到别人看不到的模式',
                '独立自主 — 不依赖外部认可，内在驱动为主',
                '理性决策 — 以逻辑和数据为基础做判断',
                '高标准 — 对自己和他人都有很高期望',
            ],
            'social_tips': [
                '在社交中尝试更多地倾听，而非总是给出解决方案',
                '学会表达情感，让身边的人感受到你的关心',
            ],
        },
    })


def card(request):
    return render(request, 'result/card.html', {
        'result': {
            'full_code': 'INTJ-A-C',
            'type_code': 'INTJ',
            'type_name': '建筑师',
            'type_slogan': '智慧的先锋，未来的建筑师',
            'nickname': '匿名用户SK3',
            'rarity': '2.70%',
            'rarity_label': '超稀有人格',
            'famous_people': '比尔·盖茨、伊隆·马斯克',
            'best_partners_list': ['INTP', 'ENTP', 'ENFP'],
        },
    })


def preview_report(request):
    return render(request, 'payment/preview.html', {
        'price': '2.99',
        'preview_content': '''
<h3>1. 你的人格类型</h3>
<p>你的完整人格编码是 <strong>INTJ-A-C</strong>，这意味着你属于 MBTI 体系中最稀有的人格类型之一。
作为"建筑师"类型，你拥有罕见的战略眼光和执行力组合——你不仅善于构画宏大蓝图，
更能够将其一步步变为现实。</p>
<p>"A"维度代表你倾向于<strong>自信型（Assertive）</strong>，这意味着你在面对压力和挑战时，
能够保持内心的稳定感。你不容易被外界评价动摇，对自己的能力有清醒的认知。</p>
<p>"C"维度代表你倾向于<strong>创造型（Creative）</strong>，在认知功能上，你更依赖直觉和想象
来理解世界，而非仅凭经验和既有规则……</p>
''',
    })


def pay(request):
    return render(request, 'payment/pay.html', {
        'price': '2.99',
        'order_id': 'PREVIEW-ORDER-001',
    })


def deep_report(request):
    chapters = []
    chapter_data = [
        (1, '你的人格类型', '你的完整人格编码是 INTJ-A-C。作为"建筑师"类型，你拥有罕见的战略眼光和执行力组合——你不仅善于构画宏大蓝图，更能够将其一步步变为现实。这是 MBTI 体系中最稀有的人格类型之一，仅占总人口的约 2.7%。'),
        (2, '人格特征分析', 'INTJ 的核心特征在于"内向直觉"（Ni）作为主导功能。这意味着你的思维天然倾向于在大量信息中识别深层模式和未来趋势。你的辅助功能"外向思考"（Te）则让你能够将直觉洞察转化为可执行的计划和系统。'),
        (3, '人口比例', 'INTJ 在全球人口中占比约 2.1%，其中男性约 3.3%，女性约 0.8%。这是最稀有的 MBTI 类型之一，尤其女性 INTJ 更为罕见。在中国语境下，INTJ 的比例可能略有不同，但整体稀有度不变。'),
        (4, '相同人格名人', '比尔·盖茨（微软创始人）、伊隆·马斯克（特斯拉/SpaceX CEO）、弗里德里希·尼采（哲学家）、尼古拉·特斯拉（发明家）、克里斯托弗·诺兰（导演）等。这些人物共同展现了 INTJ 类型"以远见改变世界"的特质。'),
        (5, '人格优势', '战略思维：善于长远规划，看到别人看不到的模式和趋势。独立自主：不依赖外部认可，内在驱动为主。理性决策：以逻辑和数据为基础做判断。高标准：对自己和他人都有很高期望。学习能力：对新知识有强烈的渴求和快速吸收能力。'),
        (6, '人格劣势', '社交困难：可能忽视情感交流，被认为冷漠或不近人情。完美主义：过高的标准可能导致拖延或不满。固执：一旦形成判断，较难接受不同观点。情感表达：不善于表达关心和爱意。过度分析：可能在简单决策上投入过多思考。'),
        (7, '成长建议', '学会倾听：在给出解决方案前，先确认对方是否只是需要倾诉。练习情感表达：尝试每天对身边人表达一次感谢或关心。接受不完美：将"足够好"作为某些场景的标准，而非追求极致。培养社交能量：有意识地安排轻松的社交活动，而非完全回避。'),
        (8, '荣格八维专项解读', '主导功能 Ni（内向直觉）：你的精神核心，负责在潜意识层面整合信息，产生"顿悟"式的洞察。辅助功能 Te（外向思考）：将直觉转化为系统化的计划和行动。第三功能 Fi（内向情感）：在成熟后发展出的价值判断系统，为决策提供内在道德锚点。劣势功能 Se（外向感觉）：你最不擅长的领域，表现为对当下感官环境的忽视或过度敏感。'),
        (9, '人格恋爱专题', '在恋爱中，INTJ 寻求的是"智性吸引"——你需要一个能与你进行深度对话、理解你思维方式的伴侣。你不擅长传统的浪漫表达，但会通过解决实际问题、优化对方生活来展现爱意。你需要大量独处时间，这不是疏远，而是"充电"。'),
        (10, '最佳恋爱对象', 'INTP（逻辑学家）：智识匹配度最高，能理解你的思维跳跃。ENTP（辩论家）：激发你的思维，带来新鲜视角。ENFP（竞选者）：用温暖和直觉补充你的理性世界，帮助你打开情感通道。'),
        (11, '深度职业专题', 'INTJ 在职业选择上需要"自主权"和"复杂度"两个核心要素。你适合能够独立思考、解决复杂问题的环境，而非重复性高、规则严密的工作。你最擅长的是"从0到1"的战略构建和系统设计，而非"从1到100"的运营优化。'),
        (12, '合适的职业', '战略顾问、数据科学家、系统架构师、投资分析师、产品经理（技术方向）、大学教授/研究员、创业者、精算师、软件工程师（架构方向）、律师（知识产权/企业法务）。这些职业共同特点是：需要深度分析能力、允许独立工作、有明确的复杂问题需要解决。'),
    ]
    for num, title, content in chapter_data:
        chapters.append({
            'num': num,
            'title': title,
            'content': '<p>' + content + '</p>',
        })
    return render(request, 'result/deep_report.html', {
        'chapters': chapters,
        'result': {
            'full_code': 'INTJ-A-C',
            'type_name': '建筑师',
        },
    })


def profile(request):
    return render(request, 'account/profile.html', {
        'assessment_history': [
            {'personality_code': 'INTJ-A-C', 'created_at': '2026-07-10T14:30:00', 'status': 'paid'},
            {'personality_code': 'ENTP-T-L', 'created_at': '2026-06-15T09:20:00', 'status': 'free'},
        ],
        'orders': [
            {'order_id': 'ORD-2026-0710-001', 'created_at': '2026-07-10T14:35:00', 'amount': '2.99', 'status': '已完成'},
            {'order_id': 'ORD-2026-0620-002', 'created_at': '2026-06-20T10:00:00', 'amount': '2.99', 'status': '已退款'},
        ],
        'user': {
            'nickname': '匿名用户SK3',
            'anonymous': True,
        },
    })
