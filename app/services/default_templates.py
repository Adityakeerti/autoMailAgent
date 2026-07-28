DEFAULT_TEMPLATES = [
    {
        "category": "Recruiter / HR Outreach",
        "subject_template": "Inquiry regarding {{ROLE_TITLE}} position at {{COMPANY}} - {{USER_NAME}}",
        "body_template": """Hi {{RECIPIENT_NAME}},

I noticed {{COMPANY}} is looking for a {{ROLE_TITLE}}. {{PERSONAL_HOOK}}

{{RELEVANT_PROJECT_LINE}}

I would love to learn more about upcoming opportunities on your team. Portfolio: {{PORTFOLIO_URL}} | GitHub: {{GITHUB_URL}}

Best regards,
{{USER_NAME}}"""
    },
    {
        "category": "Referral Ask",
        "subject_template": "Quick question regarding {{ROLE_TITLE}} at {{COMPANY}}",
        "body_template": """Hi {{RECIPIENT_NAME}},

I came across your profile and saw your work at {{COMPANY}}. {{PERSONAL_HOOK}}

I'm applying for the {{ROLE_TITLE}} position and wanted to reach out. {{RELEVANT_PROJECT_LINE}}

Would you be open to sharing any advice or referring my application if it seems like a fit?

Thanks so much,
{{USER_NAME}}"""
    },
    {
        "category": "Direct Tech Lead Pitch",
        "subject_template": "Building {{PROJECT_TOPIC}} / {{ROLE_TITLE}} inquiry",
        "body_template": """Hi {{RECIPIENT_NAME}},

I saw your recent work at {{COMPANY}}. {{PERSONAL_HOOK}}

{{RELEVANT_PROJECT_LINE}}

I'm interested in contributing to engineering projects at {{COMPANY}}. Here is a link to my work: {{PORTFOLIO_URL}}.

Best,
{{USER_NAME}}"""
    },
    {
        "category": "Follow-up",
        "subject_template": "Re: {{ROLE_TITLE}} role at {{COMPANY}}",
        "body_template": """Hi {{RECIPIENT_NAME}},

Following up on my previous message regarding the {{ROLE_TITLE}} role. {{PERSONAL_HOOK}}

I remains very interested in {{COMPANY}} and would welcome a brief conversation.

Best regards,
{{USER_NAME}}"""
    },
    {
        "category": "Cold Apply Direct",
        "subject_template": "{{USER_NAME}} - Application for {{ROLE_TITLE}}",
        "body_template": """Hi {{RECIPIENT_NAME}},

I am reaching out directly to apply for the {{ROLE_TITLE}} opportunity at {{COMPANY}}.

{{PERSONAL_HOOK}}

{{RELEVANT_PROJECT_LINE}}

Resume & Projects: {{PORTFOLIO_URL}}

Thanks,
{{USER_NAME}}"""
    },
    {
        "category": "Generic Company Outreach",
        "subject_template": "Engineering opportunities at {{COMPANY}}",
        "body_template": """Hi team,

I noticed {{COMPANY}} is hiring for a {{ROLE_TITLE}} position. I wanted to reach out and express my interest in joining your engineering organization.

I have hands-on experience building scalable applications and working with modern web and backend technologies. You can view my portfolio at {{PORTFOLIO_URL}} and find my project repositories at {{GITHUB_URL}}.

If you have any open slots or would be open to a brief chat, please let me know.

Best regards,
{{USER_NAME}}"""
    }
]
