/* ==========================================================================
   职探 - FallbackScoring Module
   MBTI 职业性格测评 · 降级评分（前端兜底算法）

   当后端 /api/score/ 接口不可用时，使用本地简化算法完成评分，
   保证用户在网络异常情况下仍能获得基础结果。

   说明：
   - 简化算法不包含面向分析与认知功能栈推导
   - 每题按 1 分计（position 1-3 → A 极，4-6 → B 极）
   - 反向题交换 A/B 极
   - 分母固定为 12（每维度 12 题）
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     常量定义
     ---------------------------------------------------------------------- */

  // 维度配置：pole_a / pole_b 为各维度的两个极字母
  const DIMENSIONS = {
    EI: { pole_a: 'E', pole_b: 'I' },
    SN: { pole_a: 'S', pole_b: 'N' },
    TF: { pole_a: 'T', pole_b: 'F' },
    JP: { pole_a: 'J', pole_b: 'P' }
  };

  // 维度判定顺序（决定 MBTI 类型 4 位字母的排列）
  const DIMENSION_ORDER = ['EI', 'SN', 'TF', 'JP'];

  // 每维度题目数（分母）
  const QUESTIONS_PER_DIMENSION = 12;

  /* ----------------------------------------------------------------------
     FallbackScoring 模块
     ---------------------------------------------------------------------- */

  const FallbackScoring = {
    // 题目元数据索引 {question_id: question}，由 setQuestions 注入
    questionsMap: {},

    /* ------------------------------------------------------------------
       注入题目元数据
       供 calculate() 查表获取 dimension / is_reverse 等信息。
       @param {Array} questions - 题目列表
       ------------------------------------------------------------------ */
    setQuestions(questions) {
      const map = {};
      (questions || []).forEach((q) => {
        if (q && q.id !== undefined) {
          map[q.id] = q;
        }
      });
      this.questionsMap = map;
    },

    /* ------------------------------------------------------------------
       简化评分
       @param {Array} answers - 答案列表，每项 {question_id, position}
                                也可内联 dimension / is_reverse 等元数据
       @returns {Object} 降级评分结果
         {
           mbti_type: "INTJ",
           degraded: true,
           dimensions: {
             EI: {percentage, label, pole_a, pole_b, score_a, score_b},
             ...
           }
         }
       ------------------------------------------------------------------ */
    calculate(answers) {
      // 初始化各维度 A/B 极计数
      const counts = {};
      DIMENSION_ORDER.forEach((dim) => {
        counts[dim] = { a: 0, b: 0 };
      });

      // 遍历答案，逐题计分
      (answers || []).forEach((ans) => {
        if (!ans) return;

        // 优先使用答案内联元数据，否则从题目索引查表
        const q = this.questionsMap[ans.question_id] || {};
        const dimension = ans.dimension || q.dimension;
        const isReverse = ans.is_reverse !== undefined
          ? !!ans.is_reverse
          : !!q.is_reverse;
        const position = ans.position;

        // 参数校验：维度合法、位置在 1-6 范围内
        if (!dimension || !counts[dimension]) return;
        if (typeof position !== 'number' || position < 1 || position > 6) return;

        // position 1-3 → A 极；4-6 → B 极
        let pole = position <= 3 ? 'a' : 'b';

        // 反向题：交换 A/B 极
        if (isReverse) {
          pole = pole === 'a' ? 'b' : 'a';
        }

        counts[dimension][pole] += 1;
      });

      // 构建维度结果
      const dimensions = {};
      DIMENSION_ORDER.forEach((dim) => {
        const config = DIMENSIONS[dim];
        const aCount = counts[dim].a;
        const bCount = counts[dim].b;

        // percentage = pole_a_count / 12 × 100
        const percentage = Math.round((aCount / QUESTIONS_PER_DIMENSION) * 100);

        // 判定倾向极：> 50 → pole_a，< 50 → pole_b，== 50 → X（临界）
        let label;
        if (percentage > 50) {
          label = config.pole_a;
        } else if (percentage < 50) {
          label = config.pole_b;
        } else {
          label = 'X';
        }

        dimensions[dim] = {
          percentage: percentage,
          label: label,
          pole_a: config.pole_a,
          pole_b: config.pole_b,
          score_a: aCount,
          score_b: bCount
        };
      });

      // 4 维度判定 MBTI 类型
      let mbtiType = '';
      DIMENSION_ORDER.forEach((dim) => {
        mbtiType += dimensions[dim].label;
      });

      return {
        mbti_type: mbtiType,
        degraded: true,
        dimensions: dimensions
      };
    }
  };

  /* ----------------------------------------------------------------------
     导出
     ---------------------------------------------------------------------- */
  window.FallbackScoring = FallbackScoring;

})();
