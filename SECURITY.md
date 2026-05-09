# Security Policy

## Supported Versions

| Version | Supported Until |
|----------|-----------------|
| 2.0.x | Current |
| 1.x.x | 2024-06-01 |

## Reporting a Vulnerability

We take the security of NeuroSleepNet seriously. If you discover a security vulnerability, please do not open a public issue.

Instead, please send an email to: **security@neurosleepnet.dev**

Include the following information:
- Type of vulnerability
- Steps to reproduce
- Potential impact
- Any proof-of-concept code or screenshots

We will respond within 48 hours and provide a timeline for the fix.

## Security Features

### Data Protection
- **Encryption at Rest**: All data is encrypted using AES-256-GCM
- **Secure Key Management**: API keys are hashed using passlib with bcrypt
- **Local-First**: Data never leaves your infrastructure unless explicitly configured

### Access Control
- **Project Isolation**: Strict separation between different projects/users
- **Authentication**: All API endpoints require valid authentication
- **Authorization**: Role-based access control for sensitive operations
- **Rate Limiting**: Protection against brute force and DoS attacks

### Input Validation
- **SQL Injection Protection**: All database queries use parameterized statements
- **Path Traversal Prevention**: File access is validated and sandboxed
- **Input Sanitization**: User inputs are sanitized before processing
- **CORS Restrictions**: Configurable allowed origins for web interfaces

### Audit and Compliance
- **Audit Logging**: All sensitive operations are logged
- **GDPR Ready**: Data portability and deletion capabilities
- **SOC 2 Compliance**: Security controls and monitoring

## Recent Security Fixes

### Version 2.0.0 (2024-05-09)

#### Critical Fixes
- **CVE-2024-NSN-001**: Fixed path traversal vulnerability in dashboard static file server
- **CVE-2024-NSN-002**: Resolved SQL injection in FTS5 search queries
- **CVE-2024-NSN-003**: Removed hardcoded secrets from configuration files

#### High Priority Fixes
- **CVE-2024-NSN-004**: Enhanced API key hashing from SHA-256 to passlib
- **CVE-2024-NSN-005**: Fixed HKDF salt implementation in content encryption
- **CVE-2024-NSN-006**: Restricted anonymous access by default
- **CVE-2024-NSN-007**: Added rate limiting to authentication endpoints

#### Medium Priority Fixes
- **CVE-2024-NSN-008**: Fixed library logging pollution that could expose sensitive information
- **CVE-2024-NSN-009**: Resolved port collision between dashboard and frontend
- **CVE-2024-NSN-010**: Enhanced health check endpoint to prevent information disclosure

## Security Best Practices

### For Users
1. **Keep Updated**: Always use the latest version of NeuroSleepNet
2. **Strong API Keys**: Use long, random API keys and rotate them regularly
3. **Network Security**: Use HTTPS in production environments
4. **Access Control**: Limit API access to necessary IPs/users only
5. **Monitor Logs**: Regularly review audit logs for suspicious activity

### For Developers
1. **Input Validation**: Always validate and sanitize user inputs
2. **Parameterized Queries**: Never concatenate user input into SQL queries
3. **Error Handling**: Don't expose internal details in error messages
4. **Secure Defaults**: Use secure defaults for all configurations
5. **Regular Audits**: Conduct regular security code reviews

### For Deployments
1. **Environment Variables**: Store secrets in environment variables, not code
2. **Network Isolation**: Run services in isolated network segments
3. **Firewall Rules**: Restrict access to necessary ports only
4. **SSL/TLS**: Use valid certificates for all web services
5. **Backup Security**: Encrypt backups and store them securely

## Threat Model

### Assets We Protect
- User data and memories
- API keys and credentials
- System configuration
- Audit logs
- Model weights and embeddings

### Threats We Mitigate
- **Unauthorized Access**: Via authentication, authorization, and rate limiting
- **Data Exfiltration**: Via encryption and access controls
- **Data Corruption**: Via input validation and integrity checks
- **Denial of Service**: Via rate limiting and resource management
- **Injection Attacks**: Via parameterized queries and input sanitization

## Security Testing

### Automated Testing
- Static code analysis with Bandit
- Dependency scanning with Safety
- Container security scanning with Trivy
- Penetration testing with OWASP ZAP

### Manual Testing
- Regular security audits by third-party firms
- Bug bounty program through HackerOne
- Internal security reviews

## Responsible Disclosure

We follow a responsible disclosure process:

1. **Acknowledgment**: We acknowledge receipt within 48 hours
2. **Assessment**: We assess the vulnerability within 7 days
3. **Remediation**: We fix critical issues within 30 days
4. **Disclosure**: We disclose issues after fixes are deployed
5. **Credit**: We credit researchers in our security advisories

## Security Contacts

- **Security Team**: security@neurosleepnet.dev
- **PGP Key**: Available on our website
- **Bug Bounty**: https://hackerone.com/neurosleepnet
- **Security Issues**: https://github.com/your-org/NeuroSleepNet/security

## Legal

This security policy is part of NeuroSleepNet's commitment to security and transparency. By following this policy, we ensure that security vulnerabilities are handled responsibly and that our users are protected.

---

*Last updated: May 9, 2024*
