# 画己职测 — assessment DRF 序列化器
#
# 本模块定义测评相关的所有 DRF 序列化器：
#   - QuestionSerializer: 题库序列化器（返回题目列表给前端）
#   - AnswerItemSerializer: 单题答案
#   - AssessmentSubmitSerializer: 测评提交序列化器
#   - OCEANScoreSerializer: 大五维度分数
#   - RIASECScoreSerializer: RIASEC 维度分数
#   - AssessmentResultSerializer: 测评结果序列化器（返回给前端）

import logging

from rest_framework import serializers

from assessment.models import Question
from common.constants import QUESTION_COUNT

logger = logging.getLogger(__name__)


class QuestionSerializer(serializers.ModelSerializer):
    """题库序列化器 — 返回题目列表给前端。"""

    class Meta:
        model = Question
        fields: list[str] = [
            "id",
            "question_text",
            "dimension_prefix",
            "is_reverse",
            "question_type",
            "order",
        ]


class AnswerItemSerializer(serializers.Serializer):
    """单题答案。"""

    question_id = serializers.IntegerField(min_value=1)
    scale_value = serializers.IntegerField(min_value=1, max_value=5)
    response_duration_ms = serializers.IntegerField(default=0, min_value=0)


class AssessmentSubmitSerializer(serializers.Serializer):
    """测评提交序列化器。"""

    answers = AnswerItemSerializer(many=True)
    started_at = serializers.CharField()
    submitted_at = serializers.CharField()

    def validate_answers(self, value: list[dict[str, int]]) -> list[dict[str, int]]:
        """验证答案数量必须为 80 题。"""
        if len(value) != QUESTION_COUNT:
            raise serializers.ValidationError(f"Expected {QUESTION_COUNT} answers, got {len(value)}")
        return value

    def validate_started_at(self, value: str) -> str:
        """验证开始时间非空。"""
        if not value:
            raise serializers.ValidationError("started_at 不能为空")
        return value

    def validate_submitted_at(self, value: str) -> str:
        """验证提交时间非空。"""
        if not value:
            raise serializers.ValidationError("submitted_at 不能为空")
        return value


class OCEANScoreSerializer(serializers.Serializer):
    """大五维度分数序列化器。"""

    dimension = serializers.CharField()
    raw_score = serializers.IntegerField()
    percentile = serializers.FloatField()
    is_high = serializers.BooleanField()
    level = serializers.IntegerField()


class RIASECScoreSerializer(serializers.Serializer):
    """RIASEC 维度分数序列化器。"""

    type = serializers.CharField()
    raw_score = serializers.IntegerField()
    rank = serializers.IntegerField()
    is_top_three = serializers.BooleanField()


class AssessmentResultSerializer(serializers.Serializer):
    """测评结果序列化器 — 返回给前端。"""

    session_token = serializers.CharField()
    assessment_id = serializers.IntegerField()
    archetype_id = serializers.IntegerField()
    archetype_name = serializers.CharField()
    archetype_slogan = serializers.CharField()
    riasec_code = serializers.CharField()
    color_spectrum = serializers.DictField()
    ocean_scores = OCEANScoreSerializer(many=True)
    riasec_scores = RIASECScoreSerializer(many=True)
    confidence = serializers.FloatField()
    is_valid = serializers.BooleanField()
    free_card_data = serializers.DictField()
