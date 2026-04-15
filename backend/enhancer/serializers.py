"""Serializers for PromptX API."""

from rest_framework import serializers


class EnhanceRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        min_length=1, max_length=10000,
        help_text="The prompt to enhance"
    )
    enhancement_level = serializers.ChoiceField(
        choices=['basic', 'intermediate', 'advanced', 'expert'],
        default='intermediate',
        help_text="Level of enhancement depth"
    )
    preferences = serializers.DictField(
        required=False, default=dict,
        help_text="User preferences (e.g., {'tone': 'formal', 'audience': 'developers'})"
    )


class AnalyzeRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=1, max_length=10000)


class CompareRequestSerializer(serializers.Serializer):
    prompt_a = serializers.CharField(min_length=1, max_length=10000)
    prompt_b = serializers.CharField(min_length=1, max_length=10000)


class FeedbackSerializer(serializers.Serializer):
    prompt_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class BatchEnhanceRequestSerializer(serializers.Serializer):
    prompts = serializers.ListField(
        child=serializers.CharField(min_length=1, max_length=10000),
        min_length=1, max_length=10,
        help_text="List of prompts to enhance (max 10)"
    )
    enhancement_level = serializers.ChoiceField(
        choices=['basic', 'intermediate', 'advanced', 'expert'],
        default='intermediate'
    )
