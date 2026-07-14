# 画己职测 — personality DRF 序列化器
#
# 本模块定义人格原型相关的 DRF 序列化器：
#   - PersonalityArchetypeSerializer: 人格原型序列化器

from rest_framework import serializers

from personality.models import PersonalityArchetype


class PersonalityArchetypeSerializer(serializers.ModelSerializer):
    """人格原型序列化器 — 返回原型配置给前端。"""

    class Meta:
        model = PersonalityArchetype
        fields: str = "__all__"
