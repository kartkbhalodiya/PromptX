"""Admin configuration for PromptX."""

from django.contrib import admin
from .models import PromptCategory, EnhancementRule, PromptHistory, PromptTemplate


@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(EnhancementRule)
class EnhancementRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'priority', 'is_active', 'usage_count', 'success_rate']
    list_filter = ['rule_type', 'is_active']
    search_fields = ['name']
    ordering = ['-priority']


@admin.register(PromptHistory)
class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'detected_intent', 'detected_domain', 'enhancement_level',
        'original_quality_score', 'enhanced_quality_score',
        'improvement_delta', 'validation_passed', 'processing_time_ms',
        'created_at',
    ]
    list_filter = [
        'enhancement_level', 'detected_intent', 'detected_domain',
        'validation_passed', 'complexity_level',
    ]
    search_fields = ['original_prompt', 'enhanced_prompt']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'processing_time_ms',
        'pipeline_stages_completed',
    ]
    date_hierarchy = 'created_at'


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'intent', 'domain', 'usage_count', 'avg_quality_improvement', 'is_active']
    list_filter = ['intent', 'domain', 'is_active']
    search_fields = ['name']
