# serializers.py
from rest_framework import serializers
from .models import Password
import re
from transformers import pipeline  # Using Hugging Face's transformers
from urllib.parse import urlparse

class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Password
        fields = (
            'id', 'name', 'username', 'password_value', 'website_url', 
            'notes', 'category', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'category')
    
    def create(self, validated_data):
        user = self.context['request'].user
        password = Password(user=user, **validated_data)
        
        # AI-powered categorization
        password.category = self.predict_category(password)
        password.save()
        
        return password
    
    def predict_category(self, password):
        # Combine features from different sources
        features = {
            'name': password.name,
            'domain': self.extract_domain_features(password.website_url),
            'notes': password.notes,
            'keywords': self.extract_keywords(password)
        }
        
        # Multi-stage classification
        return self.classify_password(features)
    
    def extract_domain_features(self, url):
        if not url:
            return {}
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return {
                'domain': domain,
                'tld': domain.split('.')[-1],
                'subdomains': domain.split('.')[:-1]
            }
        except:
            return {}

    def extract_keywords(self, password):
        text = f"{password.name} {password.notes}".lower()
        return set(re.findall(r'\b\w{4,}\b', text))

    def classify_password(self, features):
        # 1. Domain-based classification
        domain_cat = self.domain_based_classification(features['domain'])
        if domain_cat != 'OTHER':
            return domain_cat

        # 2. Zero-shot classification using transformers
        text = f"{features['name']} {features['notes']}"
        return self.zero_shot_classification(text)
    
    def domain_based_classification(self, domain_info):
        if not domain_info.get('domain'):
            return 'OTHER'


        domain = domain_info['domain'].lower()
        tld = domain_info.get('tld', '')
        subdomains = domain_info.get('subdomains', [])
        
        # Expanded domain rules with common services and patterns
        domain_patterns = {
            'SOCIAL': {
                'exact': {'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
                        'pinterest.com', 'tumblr.com', 'reddit.com', 'snapchat.com',
                        'tiktok.com', 'whatsapp.com', 'wechat.com', 'telegram.org'},
                'contains': ['social', 'connect', 'profile', 'network', 'share'],
                'tlds': set()
            },
            'EMAIL': {
                'exact': {'gmail.com', 'outlook.com', 'yahoo.com', 'protonmail.com',
                        'zoho.com', 'mail.com', 'fastmail.com', 'icloud.com'},
                'contains': ['mail', 'inbox', 'email', 'mx.', 'smtp.'],
                'tlds': {'email', 'mail'}
            },
            'FINANCE': {
                'exact': {'paypal.com', 'bankofamerica.com', 'chase.com', 'fidelity.com',
                        'capitalone.com', 'wellsfargo.com', 'schwab.com', 'coinbase.com',
                        'binance.com', 'venmo.com', 'cash.app', 'mint.com'},
                'contains': ['bank', 'pay', 'credit', 'loan', 'mortgage', 'crypto', 'trade',
                            'invest', 'wealth', 'finance', 'capital', 'exchange'],
                'tlds': {'bank', 'capital', 'trade'}
            },
            'WORK': {
                'exact': {'okta.com', 'office.com', 'azure.com', 'slack.com',
                        'atlassian.net', 'googleworkspace.com', 'vpn.', 'remote.',
                        'jira.', 'confluence.', 'zoom.us', 'teams.microsoft.com'},
                'contains': ['vpn', 'corp', 'office', 'work', 'business', 'enterprise',
                            'company', 'internal', 'hr', 'okta', 'sso', 'auth'],
                'tlds': {'enterprise', 'business'}
            },
            'ENTERTAINMENT': {
                'exact': {'netflix.com', 'spotify.com', 'hulu.com', 'youtube.com',
                        'twitch.tv', 'disneyplus.com', 'primevideo.com', 'steampowered.com',
                        'xbox.com', 'playstation.com', 'crunchyroll.com'},
                'contains': ['stream', 'game', 'music', 'video', 'tv', 'movie', 'play',
                            'fun', 'entertain', 'media', 'flix', 'tube'],
                'tlds': {'tv', 'games', 'movie'}
            },
            'SHOPPING': {
                'exact': {'amazon.com', 'ebay.com', 'etsy.com', 'aliexpress.com',
                        'walmart.com', 'target.com', 'bestbuy.com', 'newegg.com',
                        'zappos.com', 'shopify.com', 'woocommerce.com'},
                'contains': ['shop', 'store', 'cart', 'buy', 'deal', 'sale', 'market',
                            'mall', 'checkout', 'purchase', 'retail', 'merchant'],
                'tlds': {'shop', 'store', 'buy'}
            },
            'EDUCATION': {
                'exact': {'coursera.org', 'edx.org', 'udemy.com', 'khanacademy.org',
                        'skillshare.com', 'pluralsight.com', 'lynda.com'},
                'contains': ['learn', 'course', 'academy', 'study', 'school', 'edu',
                            'training', 'class', 'education'],
                'tlds': {'edu', 'academy', 'courses'}
            }
        }

        # Check exact domain matches
        for category, patterns in domain_patterns.items():
            if domain in patterns['exact']:
                return category

        # Check subdomain patterns
        for subdomain in subdomains:
            for category, patterns in domain_patterns.items():
                if any(keyword in subdomain for keyword in patterns['contains']):
                    return category

        # Check domain contains keywords
        for category, patterns in domain_patterns.items():
            if any(keyword in domain for keyword in patterns['contains']):
                return category

        # Check TLD patterns
        for category, patterns in domain_patterns.items():
            if tld in patterns['tlds']:
                return category

        # Special case handling
        if 'login.' in domain or 'auth.' in domain:
            return 'WORK'
        if 'cloud.' in domain or 'aws.' in domain:
            return 'WORK'
        if any(x in domain for x in ['bit.ly', 'goo.gl']):
            return 'OTHER'  # URL shorteners
            
        # Check domain structure patterns
        if re.search(r'\d{3,}', domain):  # Numbers in domain often indicate shopping
            return 'SHOPPING'
            
        if re.search(r'(api|dev|stage|prod)', domain):
            return 'WORK'

        # Check for country-specific financial institutions
        if re.search(r'(bank|creditunion|fin|capital)', domain):
            return 'FINANCE'

        return 'OTHER'

    def zero_shot_classification(self, text):
        if not text.strip():
            return 'OTHER'
        
        # Load a pre-trained zero-shot classifier
        classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        candidate_labels = [
            'social media', 'email', 'financial services', 
            'work related', 'entertainment', 'online shopping'
        ]
        
        result = classifier(text, candidate_labels)
        top_label = result['labels'][0].upper().replace(' ', '_')
        
        # Map to existing categories
        label_mapping = {
            'SOCIAL_MEDIA': 'SOCIAL',
            'EMAIL': 'EMAIL',
            'FINANCIAL_SERVICES': 'FINANCE',
            'WORK_RELATED': 'WORK',
            'ENTERTAINMENT': 'ENTERTAINMENT',
            'ONLINE_SHOPPING': 'SHOPPING'
        }
        
        return label_mapping.get(top_label, 'OTHER')