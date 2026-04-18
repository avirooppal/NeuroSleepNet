import re

def redact_pii(text: str) -> str:
    \"\"\"
    Detects and masks basic PII such as Emails, SSNs, and Phone Numbers.
    \"\"\"
    if not text:
        return text
    
    # Redact Emails
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL REDACTED]', text)
    
    # Redact basic US Phone Numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]', text)
    
    # Redact SSNs
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]', text)
    
    return text
