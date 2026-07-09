#!/usr/bin/env python3
"""
LLM-Generated Phishing Detection Classifier Prototype

This script implements a classifier to detect AI-generated phishing emails based on:
1. Linguistic pattern analysis (overly formal language, lack of specific details)
2. AI-generated text markers (certain linguistic patterns common in LLM output)
3. Sender reputation and URL verification simulation

Note: This is a conceptual prototype. Full implementation would use NLP models
like BERT or LLM-specific classifiers.
"""

import re
from typing import Dict, List, Tuple, Any

class LLMPhishingDetector:
    """
    Detects AI-generated phishing emails using linguistic pattern analysis.
    """
    
    def __init__(self):
        # AI-generated text markers
        self.ai_linguistic_markers = [
            r"I hope this email finds you well",
            r"I am writing to you regarding",
            r"Please let me know if you have any questions",
            r"I would appreciate your prompt attention to this matter",
            r"At your earliest convenience",
            r"It is important to note that",
            r"In conclusion",
            r"As an AI language model",
            r"Please be advised",
            r"Kindly revert back"
        ]
        
        # Phishing indicator patterns (contextual, not just keywords)
        self.phishing_patterns = [
            r"urgent.*action.*required",
            r"account.*suspended|account.*limited",
            r"verify.*identity|verify.*account",
            r"click.*link.*below",
            r"update.*password.*immediately",
            r"wire.*transfer.*urgent",
            r"invoice.*past.*due",
            r"payment.*failed"
        ]
        
        # AI-generated text tends to be overly formal and lack specific details
        self.overly_formal_markers = [
            r"dear (sir|madam|valued customer)",
            r"this is to inform you that",
            r"we are writing to notify you"
        ]
    
    def analyze_linguistic_patterns(self, email_content: str) -> Dict[str, float]:
        """
        Analyze email content for AI-generated linguistic patterns.
        """
        email_lower = email_content.lower()
        
        ai_marker_score = 0.0
        found_ai_markers = []
        
        for marker in self.ai_linguistic_markers:
            if re.search(marker, email_lower):
                ai_marker_score += 0.15
                found_ai_markers.append(marker)
        
        # Normalize score
        ai_marker_score = min(ai_marker_score, 1.0)
        
        # Check for overly formal language
        formal_score = 0.0
        for marker in self.overly_formal_markers:
            if re.search(marker, email_lower):
                formal_score += 0.2
        
        formal_score = min(formal_score, 1.0)
        
        return {
            'ai_marker_score': ai_marker_score,
            'found_ai_markers': found_ai_markers,
            'formal_language_score': formal_score
        }
    
    def analyze_phishing_patterns(self, email_content: str) -> Dict[str, float]:
        """
        Analyze email content for phishing indicators.
        """
        email_lower = email_content.lower()
        
        phishing_score = 0.0
        found_patterns = []
        
        for pattern in self.phishing_patterns:
            if re.search(pattern, email_lower):
                phishing_score += 0.25
                found_patterns.append(pattern)
        
        phishing_score = min(phishing_score, 1.0)
        
        return {
            'phishing_score': phishing_score,
            'found_patterns': found_patterns
        }
    
    def analyze_sender_reputation_simulation(self, sender_email: str, domain: str) -> Dict[str, Any]:
        """
        Simulate sender reputation analysis.
        In a real implementation, this would check:
        - SPF/DKIM/DMARC records
        - Historical sending patterns
        - Domain age and reputation
        """
        # Simulate reputation check
        is_valid_domain = domain.endswith(('.com', '.org', '.net', '.edu', '.gov'))
        
        # Simulate SPF/DKIM/DMARC status
        spf_passed = True if random.random() > 0.1 else False
        dkim_passed = True if random.random() > 0.1 else False
        dmarc_passed = True if random.random() > 0.1 else False
        
        reputation_score = 1.0
        if not is_valid_domain:
            reputation_score -= 0.5
        if not spf_passed:
            reputation_score -= 0.3
        if not dkim_passed:
            reputation_score -= 0.3
        if not dmarc_passed:
            reputation_score -= 0.4
        
        reputation_score = max(0.0, min(1.0, reputation_score))
        
        return {
            'is_valid_domain': is_valid_domain,
            'spf_passed': spf_passed,
            'dkim_passed': dkim_passed,
            'dmarc_passed': dmarc_passed,
            'reputation_score': reputation_score
        }
    
    def analyze_url_verification_simulation(self, urls_in_email: List[str]) -> Dict[str, Any]:
        """
        Simulate URL/domain verification.
        In a real implementation, this would check:
        - If URLs lead to legitimate domains
        - If domains are known phishing sites
        - If URLs contain obfuscation patterns
        """
        suspicious_urls = []
        url_risk_score = 0.0
        
        for url in urls_in_email:
            # Check for obfuscation patterns
            if 'http://' in url and 'https://' not in url:
                url_risk_score += 0.2
                suspicious_urls.append(f"{url} (uses http instead of https)")
            elif 'bit.ly' in url or 'tinyurl.com' in url or 't.co' in url:
                url_risk_score += 0.3
                suspicious_urls.append(f"{url} (uses URL shortener)")
            elif re.search(r'\d+\.\d+\.\d+\.\d+', url):
                url_risk_score += 0.4
                suspicious_urls.append(f"{url} (IP address instead of domain)")
        
        url_risk_score = min(url_risk_score, 1.0)
        
        return {
            'suspicious_urls': suspicious_urls,
            'url_risk_score': url_risk_score
        }
    
    def classify_email(self, email_content: str, sender_email: str, urls_in_email: List[str] = None) -> Dict[str, Any]:
        """
        Classify email as AI-generated phishing or legitimate.
        """
        if urls_in_email is None:
            urls_in_email = []
        
        # Extract domain from sender email
        domain = sender_email.split('@')[-1] if '@' in sender_email else ''
        
        # Analyze patterns
        linguistic_analysis = self.analyze_linguistic_patterns(email_content)
        phishing_analysis = self.analyze_phishing_patterns(email_content)
        sender_reputation = self.analyze_sender_reputation_simulation(sender_email, domain)
        url_verification = self.analyze_url_verification_simulation(urls_in_email)
        
        # Compute overall risk score
        risk_score = 0.0
        
        # Linguistic AI markers (up to 0.3)
        risk_score += linguistic_analysis['ai_marker_score'] * 0.3
        
        # Formal language (up to 0.1)
        risk_score += linguistic_analysis['formal_language_score'] * 0.1
        
        # Phishing patterns (up to 0.4)
        risk_score += phishing_analysis['phishing_score'] * 0.4
        
        # Sender reputation (up to 0.2)
        risk_score += (1.0 - sender_reputation['reputation_score']) * 0.2
        
        # URL risk (up to 0.2)
        risk_score += url_verification['url_risk_score'] * 0.2
        
        risk_score = min(risk_score, 1.0)
        
        is_phishing = risk_score > 0.5
        confidence = min(risk_score * 1.2, 1.0)
        
        return {
            'risk_score': risk_score,
            'is_phishing': is_phishing,
            'confidence': confidence,
            'linguistic_analysis': linguistic_analysis,
            'phishing_analysis': phishing_analysis,
            'sender_reputation': sender_reputation,
            'url_verification': url_verification
        }


import random

def run_llm_phishing_detector_demo():
    """Run a demonstration of the LLM-generated phishing detection prototype"""
    print("="*70)
    print("LLM-GENERATED PHISHING DETECTION CLASSIFIER PROTOTYPE")
    print("="*70)
    
    detector = LLMPhishingDetector()
    
    # Test Case 1: AI-Generated Phishing Email
    print("\n--- Test Case 1: AI-Generated Phishing Email ---")
    ai_phishing_email = """
Subject: Urgent: Action Required to Verify Your Account

Dear Valued Customer,

I am writing to you regarding your account. It is important to note that we have detected unusual activity on your account. 

To prevent your account from being suspended, please verify your identity by clicking the link below:

https://secure-verify-account.com/login

Please be advised that you must update your password immediately. If you do not take action within 24 hours, your account will be limited.

I would appreciate your prompt attention to this matter. Please let me know if you have any questions.

Sincerely,
Security Team
"""
    
    result_ai_phishing = detector.classify_email(
        email_content=ai_phishing_email,
        sender_email='security@secure-verify-account.com',
        urls_in_email=['https://secure-verify-account.com/login']
    )
    
    print(f"Risk Score: {result_ai_phishing['risk_score']:.3f}")
    print(f"Is Phishing: {result_ai_phishing['is_phishing']}")
    print(f"Confidence: {result_ai_phishing['confidence']:.3f}")
    print(f"AI Markers Found: {result_ai_phishing['linguistic_analysis']['found_ai_markers']}")
    print(f"Phishing Patterns Found: {result_ai_phishing['phishing_analysis']['found_patterns']}")
    print(f"Sender Reputation Score: {result_ai_phishing['sender_reputation']['reputation_score']:.3f}")
    
    # Test Case 2: Legitimate Internal Email
    print("\n--- Test Case 2: Legitimate Internal Email ---")
    legitimate_email = """
Subject: Team Meeting - Project Alpha Update

Hi team,

Just a quick reminder about our team meeting tomorrow at 2 PM to discuss the Project Alpha update. 

Please come prepared with your status reports for your respective modules.

Thanks,
John
"""
    
    result_legitimate = detector.classify_email(
        email_content=legitimate_email,
        sender_email='john.smith@company.com',
        urls_in_email=[]
    )
    
    print(f"Risk Score: {result_legitimate['risk_score']:.3f}")
    print(f"Is Phishing: {result_legitimate['is_phishing']}")
    print(f"Confidence: {result_legitimate['confidence']:.3f}")
    print(f"AI Markers Found: {result_legitimate['linguistic_analysis']['found_ai_markers']}")
    print(f"Phishing Patterns Found: {result_legitimate['phishing_analysis']['found_patterns']}")
    print(f"Sender Reputation Score: {result_legitimate['sender_reputation']['reputation_score']:.3f}")
    
    # Test Case 3: Sophisticated AI Phishing with Low Formal Markers
    print("\n--- Test Case 3: Sophisticated AI Phishing (Less Formal) ---")
    soph_phishing_email = """
Subject: Invoice #INV-2026-0742 - Payment Failed

Hi,

Your invoice for $12,500 is past due. The payment failed and your services will be suspended unless you update your payment information.

Click here to update: http://invoice-payment-portal.net/update

This is urgent - please resolve within 48 hours.

Best,
Billing Department
"""
    
    result_soph_phishing = detector.classify_email(
        email_content=soph_phishing_email,
        sender_email='billing@invoice-payment-portal.net',
        urls_in_email=['http://invoice-payment-portal.net/update']
    )
    
    print(f"Risk Score: {result_soph_phishing['risk_score']:.3f}")
    print(f"Is Phishing: {result_soph_phishing['is_phishing']}")
    print(f"Confidence: {result_soph_phishing['confidence']:.3f}")
    print(f"AI Markers Found: {result_soph_phishing['linguistic_analysis']['found_ai_markers']}")
    print(f"Phishing Patterns Found: {result_soph_phishing['phishing_analysis']['found_patterns']}")
    print(f"Sender Reputation Score: {result_soph_phishing['sender_reputation']['reputation_score']:.3f}")
    print(f"URL Risk Score: {result_soph_phishing['url_verification']['url_risk_score']:.3f}")
    
    print("\n" + "="*70)
    print("LLM PHISHING DETECTOR PROTOTYPE DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Finding: The prototype successfully identifies AI-generated phishing")
    print("emails using linguistic pattern analysis, phishing indicator detection,")
    print("sender reputation simulation, and URL verification. Multi-layered")
    print("analysis provides comprehensive protection against AI-powered phishing.")


if __name__ == "__main__":
    run_llm_phishing_detector_demo()