"""
Questionnaire prompt assets for ideation flows.
"""

QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "category": "PERSONAL",
        "type": "multi",
        "question": "What industries or domains excite you most?",
        "options": [
            "Technology/SaaS", "Healthcare/Biotech", "Education/EdTech", "Finance/FinTech",
            "E-commerce/Retail", "Media/Entertainment", "Real Estate/PropTech", "Food/Agriculture",
            "Energy/CleanTech", "Social Impact/Non-profit"
        ],
    },
    {
        "id": 2,
        "category": "PERSONAL",
        "type": "multi",
        "question": "What are your strongest skills?",
        "options": [
            "Software development", "Design/UX", "Marketing/Sales", "Data/Analytics",
            "Operations/Management", "Finance/Accounting", "Content/Writing", "Research/Strategy"
        ],
    },
    {
        "id": 3,
        "category": "PERSONAL",
        "type": "multi",
        "question": "How much time can you dedicate weekly?",
        "options": [
            "< 10 hours (side project)", "10-20 hours (serious side hustle)",
            "20-40 hours (part-time focus)", "40+ hours (full-time)", "Flexible/Variable"
        ],
    },
    {
        "id": 4,
        "category": "PROBLEM",
        "type": "text",
        "question": "What problems frustrate you most in daily life or work?",
    },
    {
        "id": 5,
        "category": "PROBLEM",
        "type": "rating",
        "question": "Rate your frustration with current solutions in your area of interest",
    },
    {
        "id": 6,
        "category": "PROBLEM",
        "type": "multi",
        "question": "Who would benefit most from your ideal product?",
        "options": [
            "Individual consumers", "Small businesses", "Enterprise companies", "Developers/Technical users",
            "Students/Educators", "Healthcare professionals", "Government/Public sector", "Creative professionals"
        ],
    },
    {
        "id": 7,
        "category": "BUSINESS",
        "type": "multi",
        "question": "Which business model appeals to you?",
        "options": [
            "B2B SaaS (recurring revenue)", "B2C Subscription", "Marketplace (take rate)", "E-commerce",
            "Freemium", "Advertising", "One-time purchase", "Usage-based pricing", "Transaction fees",
            "Licensing/Royalties", "Consulting/Services", "Affiliate/Referral", "Hybrid model"
        ],
    },
    {
        "id": 8,
        "category": "BUSINESS",
        "type": "multi",
        "question": "What scale are you targeting?",
        "options": [
            "Lifestyle business ($100K-$1M/year)", "Small startup ($1M-$10M/year)",
            "High-growth ($10M-$100M/year)", "Unicorn potential ($100M+/year)",
            "Niche/Micro-SaaS ($10K-$100K/year)", "Open to any profitable model"
        ],
    },
    {
        "id": 9,
        "category": "BUSINESS",
        "type": "multi",
        "question": "How do you plan to fund this?",
        "options": [
            "Bootstrapped (self-funded)", "Angel/Seed funding", "VC funding",
            "Revenue-funded (profitable from day 1)", "Crowdfunding", "Grants/Accelerators",
            "Friends & Family", "Pre-sales/Customers", "Strategic investors", "Open to any option"
        ],
    },
    {
        "id": 10,
        "category": "TECHNICAL",
        "type": "rating",
        "question": "Rate your technical capability",
    },
    {
        "id": 11,
        "category": "TECHNICAL",
        "type": "multi",
        "question": "For your MVP, would you prefer to:",
        "options": [
            "Build everything from scratch", "Use no-code/low-code tools", "Hire developers",
            "Mix of building and no-code", "Use AI code generators", "Outsource development",
            "Find technical co-founder", "Use existing platforms/APIs", "Open source solutions"
        ],
    },
    {
        "id": 12,
        "category": "MARKET",
        "type": "multi",
        "question": "Which emerging trends excite you?",
        "options": [
            "AI/Generative AI", "Blockchain/Web3", "Climate Tech", "Remote Work", "Creator Economy",
            "Health Tech", "EdTech", "FinTech", "Quantum Computing", "AR/VR/Metaverse",
            "IoT/Smart Devices", "Autonomous Vehicles", "5G/Edge Computing", "Biotechnology",
            "Space Tech", "Robotics/Automation"
        ],
    },
    {
        "id": 13,
        "category": "MARKET",
        "type": "multi",
        "question": "How do you feel about competition?",
        "options": [
            "Prefer blue ocean (no competition)", "Validated market with room to innovate",
            "Ready to disrupt established players", "Niche focus within competitive market",
            "Better execution of existing ideas", "Open to any competitive landscape"
        ],
    },
    {
        "id": 14,
        "category": "MARKET",
        "type": "multi",
        "question": "Geographic focus?",
        "options": [
            "Global from day 1", "Start in US, expand later", "Focus on emerging markets",
            "Specific region/country", "Europe first", "Asia-Pacific", "Latin America",
            "Remote-first (location agnostic)"
        ],
    },
    {
        "id": 15,
        "category": "VISION",
        "type": "text",
        "question": "In one sentence, what impact do you want your product to have?",
    },
]

QUESTIONNAIRE_IDEA_PROMPT = """You are a world-class startup advisor. The user has answered a detailed questionnaire about their interests, skills, and preferences. Generate exactly 3 unique, personalized startup ideas based on their profile.

Each idea should be:
- Highly specific and immediately actionable
- Aligned with their stated skills and interests
- Feasible given their time commitment and technical level
- In a market they expressed interest in

Respond with ONLY valid JSON:
{
    \"ideas\": [
        {
            \"name\": \"Product Name\",
            \"description\": \"2-3 sentence description\",
            \"target_market\": \"specific target audience\",
            \"tam\": \"estimated TAM range with rationale\",
            \"revenue_model\": \"how it makes money\",
            \"monthly_revenue_potential\": \"$X/mo estimate\",
            \"yearly_revenue_potential\": \"$X/year estimate\",
            \"how_it_works\": \"1-2 sentences on the core mechanism\",
            \"why_now\": \"why this is timely\",
            \"go_to_market\": \"initial distribution strategy\",
            \"pricing_model\": \"pricing approach\",
            \"strategic_moat\": \"defensibility angle\",
            \"launch_plan_90_days\": \"high-level 90-day launch plan\",
            \"score\": 80
        }
    ]
}"""
