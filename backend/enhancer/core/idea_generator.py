"""Idea generation module for PromptX - generates business and project ideas."""

import random
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger('enhancer')


@dataclass
class IdeaResult:
    """Result from idea generation."""
    ideas: List[Dict]
    category: str
    total_ideas: int
    processing_time_ms: float


class IdeaGenerator:
    """
    Generates business, project, and money-making ideas.
    
    Categories:
    - business: High-grossing business ideas
    - project: Project/tech ideas
    - side_hustle: Quick income ideas
    - startup: Startup opportunities
    - coding: Development project ideas
    - hacking: Security/ethical hacking ideas
    """

    # High-grossing business ideas with details
    BUSINESS_IDEAS = [
        {
            'title': 'AI-Powered SaaS Platform',
            'description': 'Build vertical-specific AI tools for industries like healthcare, legal, or finance.',
            'market_size': '$50B+',
            'revenue_potential': '$1M-10M ARR',
            'startup_cost': '$50K-500K',
            'time_to_revenue': '6-18 months',
            'difficulty': 'Hard',
            'skills_needed': ['AI/ML', 'Cloud', 'Domain expertise'],
        },
        {
            'title': 'B2B Marketplace',
            'description': 'Connect businesses with suppliers, services, or professionals in a niche industry.',
            'market_size': '$20B+',
            'revenue_potential': '$500K-5M ARR',
            'startup_cost': '$20K-200K',
            'time_to_revenue': '6-12 months',
            'difficulty': 'Medium',
            'skills_needed': ['Full-stack', 'Sales', 'Marketing'],
        },
        {
            'title': 'SaaS Subscription Box',
            'description': 'Curated tech/gadgets delivered monthly to subscribers.',
            'market_size': '$5B',
            'revenue_potential': '$200K-2M ARR',
            'startup_cost': '$10K-100K',
            'time_to_revenue': '3-6 months',
            'difficulty': 'Easy',
            'skills_needed': ['E-commerce', 'Sourcing', 'Logistics'],
        },
        {
            'title': 'Online Education Platform',
            'description': 'Create courses, bootcamps, or tutoring for professional skills.',
            'market_size': '$400B',
            'revenue_potential': '$100K-1M ARR',
            'startup_cost': '$5K-50K',
            'time_to_revenue': '1-6 months',
            'difficulty': 'Easy',
            'skills_needed': ['Content creation', 'Marketing', 'Subject expertise'],
        },
        {
            'title': 'Health Tech App',
            'description': 'Fitness, mental health, or chronic disease management mobile app.',
            'market_size': '$180B',
            'revenue_potential': '$500K-5M ARR',
            'startup_cost': '$30K-300K',
            'time_to_revenue': '6-12 months',
            'difficulty': 'Medium',
            'skills_needed': ['Mobile dev', 'Healthcare knowledge', 'Compliance'],
        },
        {
            'title': 'Fintech Solution',
            'description': 'Payment processing, personal finance, or investment tools.',
            'market_size': '$700B',
            'revenue_potential': '$1M-20M ARR',
            'startup_cost': '$100K-1M',
            'time_to_revenue': '12-24 months',
            'difficulty': 'Hard',
            'skills_needed': ['Finance', 'Security', 'Regulatory compliance'],
        },
        {
            'title': 'E-commerce Brand',
            'description': 'Sell private-label products on Amazon, Shopify, or direct-to-consumer.',
            'market_size': '$6T',
            'revenue_potential': '$50K-500K profit',
            'startup_cost': '$5K-50K',
            'time_to_revenue': '1-4 months',
            'difficulty': 'Easy',
            'skills_needed': ['Product sourcing', 'Amazon/Shopify', 'Ads'],
        },
        {
            'title': 'Consulting Agency',
            'description': 'Expert consulting in tech, business, marketing, or specialized field.',
            'market_size': '$250B',
            'revenue_potential': '$100K-1M+',
            'startup_cost': '$1K-10K',
            'time_to_revenue': '1-3 months',
            'difficulty': 'Easy',
            'skills_needed': ['Expertise', 'Sales', 'Client management'],
        },
    ]

    # Side hustle ideas
    SIDE_HUSTLE_IDEAS = [
        {
            'title': 'Freelance Development',
            'description': 'Build websites, apps, or automate processes for clients.',
            'income_potential': '$1K-10K/month',
            'time_investment': '5-20 hours/week',
            'startup_cost': '$0',
            'skills_needed': ['Programming', 'Communication'],
        },
        {
            'title': 'Content Creation',
            'description': 'YouTube, TikTok, blog, or podcast with monetization.',
            'income_potential': '$100-10K/month',
            'time_investment': '10-30 hours/week',
            'startup_cost': '$0-2K',
            'skills_needed': ['Content creation', 'Editing', 'Consistency'],
        },
        {
            'title': 'Dropshipping',
            'description': 'Sell products without inventory, ship directly from supplier.',
            'income_potential': '$500-5K/month',
            'time_investment': '10-25 hours/week',
            'startup_cost': '$500-3K',
            'skills_needed': ['E-commerce', 'Ads', 'Customer service'],
        },
        {
            'title': 'Print on Demand',
            'description': 'Design custom t-shirts, mugs, and sell via Merch by Amazon or Redbubble.',
            'income_potential': '$200-2K/month',
            'time_investment': '5-15 hours/week',
            'startup_cost': '$0-500',
            'skills_needed': ['Design', 'Marketing'],
        },
        {
            'title': 'Virtual Assistant',
            'description': 'Help businesses with admin tasks, scheduling, email management.',
            'income_potential': '$1K-5K/month',
            'time_investment': '10-40 hours/week',
            'startup_cost': '$0',
            'skills_needed': ['Organization', 'Communication', 'Tech'],
        },
        {
            'title': 'Online Tutoring',
            'description': 'Teach subjects you excel at via Zoom or platforms like VIPKid.',
            'income_potential': '$1K-8K/month',
            'time_investment': '5-30 hours/week',
            'startup_cost': '$0-500',
            'skills_needed': ['Subject expertise', 'Teaching'],
        },
        {
            'title': 'Social Media Management',
            'description': 'Manage social accounts for small businesses.',
            'income_potential': '$500-5K/month',
            'time_investment': '10-25 hours/week',
            'startup_cost': '$0',
            'skills_needed': ['Social media', 'Content', 'Analytics'],
        },
        {
            'title': 'Stock Photography',
            'description': 'Sell photos to stock photo sites like Shutterstock, Adobe Stock.',
            'income_potential': '$50-1K/month',
            'time_investment': '5-15 hours/week',
            'startup_cost': '$0-2K (camera)',
            'skills_needed': ['Photography', 'Editing'],
        },
    ]

    # Coding project ideas
    CODING_PROJECT_IDEAS = [
        {
            'title': 'Task Management App',
            'description': 'Trello-like kanban board with real-time collaboration.',
            'difficulty': 'Medium',
            'tech_stack': ['React', 'Node.js', 'MongoDB', 'Socket.io'],
            'features': ['Drag-drop boards', 'Real-time sync', 'File attachments'],
        },
        {
            'title': 'AI Chatbot',
            'description': 'Custom chatbot with knowledge base and API integrations.',
            'difficulty': 'Medium-Hard',
            'tech_stack': ['Python', 'LangChain', 'OpenAI API', 'FastAPI'],
            'features': ['Custom knowledge', 'Multi-language', 'Voice input'],
        },
        {
            'title': 'E-learning Platform',
            'description': 'Course platform with video streaming, quizzes, progress tracking.',
            'difficulty': 'Hard',
            'tech_stack': ['React', 'Node.js', 'PostgreSQL', 'AWS S3'],
            'features': ['Video hosting', 'Quizzes', 'Certificates', 'Progress tracking'],
        },
        {
            'title': 'Personal Finance Tracker',
            'description': 'Track expenses, investments, and budget with visualizations.',
            'difficulty': 'Easy-Medium',
            'tech_stack': ['React Native', 'Firebase', 'Chart.js'],
            'features': ['Bank sync', 'Budget alerts', 'Investment tracking', 'Reports'],
        },
        {
            'title': 'Social Media Scheduler',
            'description': 'Schedule posts across multiple platforms with analytics.',
            'difficulty': 'Medium',
            'tech_stack': ['Vue.js', 'Django', 'PostgreSQL', 'AWS'],
            'features': ['Multi-platform', 'Analytics', 'Team collaboration'],
        },
        {
            'title': 'Real-time Collaboration Tool',
            'description': 'Google Docs-like collaborative document editing.',
            'difficulty': 'Hard',
            'tech_stack': ['React', 'Node.js', 'OT algorithm', 'WebSockets'],
            'features': ['Real-time editing', 'Comments', 'Version history'],
        },
    ]

    # Ethical hacking/security ideas
    SECURITY_IDEAS = [
        {
            'title': 'Security Audit Framework',
            'description': 'Automated security scanning and vulnerability assessment tool.',
            'difficulty': 'Hard',
            'use_cases': ['Web app security', 'API security', 'Compliance checking'],
            'tools_needed': ['Python', 'Burp Suite', 'OWASP ZAP', 'Nmap'],
        },
        {
            'title': 'Penetration Testing Guide',
            'description': 'Comprehensive methodology and checklist for pentesting.',
            'difficulty': 'Medium',
            'use_cases': ['Red team ops', 'Security certification', 'Training'],
            'tools_needed': ['Metasploit', 'Nmap', 'Wireshark', 'Burp Suite'],
        },
        {
            'title': 'Security Awareness Training',
            'description': 'Interactive training platform for employee security education.',
            'difficulty': 'Medium',
            'use_cases': ['Corporate training', 'Phishing simulation', 'Compliance'],
            'tools_needed': ['LMS platform', 'Phishing tools', 'Analytics'],
        },
        {
            'title': 'Incident Response Automation',
            'description': 'Automated playbook for security incident response.',
            'difficulty': 'Hard',
            'use_cases': ['SOC automation', 'Threat response', 'Forensics'],
            'tools_needed': ['SIEM', 'SOAR', 'Python', 'API integrations'],
        },
    ]

    def __init__(self):
        pass

    def generate(self, prompt: str, category: Optional[str] = None, 
                 quantity: int = 5) -> IdeaResult:
        """
        Generate ideas based on user prompt.
        
        Args:
            prompt: User's idea request
            category: Specific category (business, project, side_hustle, startup, coding, hacking)
            quantity: Number of ideas to generate
            
        Returns:
            IdeaResult with generated ideas
        """
        import time
        start_time = time.perf_counter()

        # Determine category from prompt if not specified
        if not category:
            category = self._detect_category(prompt)

        # Get ideas based on category
        ideas = self._get_ideas_by_category(category, quantity)

        elapsed = (time.perf_counter() - start_time) * 1000

        return IdeaResult(
            ideas=ideas,
            category=category,
            total_ideas=len(ideas),
            processing_time_ms=round(elapsed, 2),
        )

    def _detect_category(self, prompt: str) -> str:
        """Detect the category from the prompt."""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['business', 'startup', 'company', 'enterprise', 'grossing', 'revenue']):
            return 'business'
        elif any(word in prompt_lower for word in ['side hustle', 'quick money', 'extra income', 'part time', 'freelance']):
            return 'side_hustle'
        elif any(word in prompt_lower for word in ['coding', 'program', 'app', 'software', 'project', 'build', 'develop']):
            return 'coding'
        elif any(word in prompt_lower for word in ['hack', 'security', 'penetration', 'vulnerability', 'pentest']):
            return 'hacking'
        elif any(word in prompt_lower for word in ['startup', 'entrepreneur', 'new business', 'innovation']):
            return 'startup'
        else:
            return 'business'  # Default to business ideas

    def _get_ideas_by_category(self, category: str, quantity: int) -> List[Dict]:
        """Get ideas for a specific category."""
        idea_pool = {
            'business': self.BUSINESS_IDEAS,
            'side_hustle': self.SIDE_HUSTLE_IDEAS,
            'coding': self.CODING_PROJECT_IDEAS,
            'hacking': self.SECURITY_IDEAS,
            'startup': self.BUSINESS_IDEAS,  # Similar to business
        }

        pool = idea_pool.get(category, self.BUSINESS_IDEAS)
        
        # Shuffle and return requested quantity
        shuffled = random.sample(pool, min(len(pool), quantity))
        return shuffled

    def get_all_categories(self) -> List[Dict]:
        """Get all available categories with descriptions."""
        return [
            {
                'id': 'business',
                'name': 'Business Ideas',
                'description': 'High-grossing business opportunities with market analysis',
                'icon': '💼',
            },
            {
                'id': 'side_hustle',
                'name': 'Side Hustles',
                'description': 'Quick income ideas you can start today',
                'icon': '💰',
            },
            {
                'id': 'startup',
                'name': 'Startup Ideas',
                'description': 'Scalable startup opportunities',
                'icon': '🚀',
            },
            {
                'id': 'coding',
                'name': 'Coding Projects',
                'description': 'Development project ideas with tech stacks',
                'icon': '💻',
            },
            {
                'id': 'hacking',
                'name': 'Security Ideas',
                'description': 'Ethical hacking and security project ideas',
                'icon': '🔐',
            },
        ]