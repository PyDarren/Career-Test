# 画己职测 — careers DRF 序列化器
#
# 本模块定义职业相关的 DRF 序列化器：
#   - CareerSerializer: 职业序列化器

from rest_framework import serializers

from careers.models import Career


class CareerSerializer(serializers.ModelSerializer):
    """职业序列化器 — 返回职业推荐数据给前端。"""

    class Meta:
        model = Career
        fields: str = "__all__"
