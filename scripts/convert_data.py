"""
Convert Maven CRM Sales data to Deal Forensics JSON format.
"""
import csv
import json
import random
from datetime import datetime, timedelta
from collections import defaultdict

def load_csv(path):
    rows = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def generate_timeline(engage_date_str, close_date_str, deal_stage):
    """Generate realistic timeline events based on deal dates."""
    engage = datetime.strptime(engage_date_str, "%Y-%m-%d")
    close = datetime.strptime(close_date_str, "%Y-%m-%d") if close_date_str else engage + timedelta(days=30)
    
    days_diff = (close - engage).days
    if days_diff < 1:
        days_diff = random.randint(30, 90)
        close = engage + timedelta(days=days_diff)
    
    timeline = []
    
    timeline.append({
        "day": 0,
        "event": "Initial Contact",
        "details": f"First outreach to prospect via email and LinkedIn"
    })
    
    mid = days_diff // 2
    
    events_pool = [
        "Discovery Call",
        "Demo Presentation",
        "Proposal Sent",
        "Pricing Discussion",
        "Technical Evaluation",
        "Contract Review",
        "Stakeholder Meeting",
        "Pilot Discussion",
        "Renewal Talk",
        "Upsell Discussion"
    ]
    
    stages = ["Engaging", "Prospecting", "Won", "Lost"]
    if deal_stage == "Won":
        key_events = ["Initial Contact", "Discovery Call", "Demo Presentation", "Proposal Sent", "Negotiation", "Closed Won"]
    elif deal_stage == "Lost":
        key_events = ["Initial Contact", "Discovery Call", "Demo Presentation", "Proposal Sent", "Lost - Competitor", "Lost - Price"]
    else:
        key_events = ["Initial Contact", "Discovery Call", "Demo", "Proposal"]
    
    timeline.append({
        "day": random.randint(3, 10),
        "event": "Discovery Call",
        "details": "Attended by decision makers from both sides"
    })
    
    timeline.append({
        "day": random.randint(10, 20),
        "event": "Demo Presentation",
        "details": "Product walkthrough with Q&A session"
    })
    
    timeline.append({
        "day": random.randint(20, 40),
        "event": "Proposal Sent",
        "details": "Detailed pricing and implementation plan shared"
    })
    
    if deal_stage == "Won":
        if days_diff > 45:
            timeline.append({
                "day": random.randint(40, days_diff - 5),
                "event": "Negotiation",
                "details": "Terms finalized and contract approved"
            })
        timeline.append({
            "day": days_diff,
            "event": "Closed Won",
            "details": "Deal signed and customer onboarded"
        })
    elif deal_stage == "Lost":
        loss_reasons = [
            "Lost to competitor - inferior feature set",
            "Price too high for budget",
            "Lost to competitor - better pricing",
            "No decision - deferring to next quarter",
            "Missing executive sponsorship",
            "Timeline didn't align with their needs"
        ]
        loss_day = min(random.randint(35, max(40, days_diff - 1)), days_diff - 1)
        timeline.append({
            "day": loss_day,
            "event": random.choice(loss_reasons),
            "details": "Prospect decided to go with competitor or cancel project"
        })
    
    return timeline

def convert():
    pipeline = load_csv("/tmp/crm_data/sales_pipeline.csv")
    accounts = load_csv("/tmp/crm_data/accounts.csv")
    products = load_csv("/tmp/crm_data/products.csv")
    teams = load_csv("/tmp/crm_data/sales_teams.csv")
    
    account_map = {a["account"]: a for a in accounts}
    product_map = {p["product"]: p for p in products}
    team_map = {t["sales_agent"]: t for t in teams}
    
    # Product-based pricing (realistic deal values)
    product_prices = {
        "GTX Basic": (800, 2500),
        "GTX Plus Basic": (2500, 8000),
        "GTXPro": (5000, 15000),
        "MG Special": (1500, 5000),
    }
    
    competitors_list = ["Competitor A", "Competitor B", "Competitor C", "Competitor D", "Competitor E"]
    loss_reasons_list = [
        "price_too_high",
        "lost_to_competitor",
        "no_budget",
        "no_decision",
        "timeline_mismatch",
        "feature_gap",
        "vendor_lock_in",
        "poor_fit"
    ]
    
    won_deals = []
    lost_deals = []
    
    for i, deal in enumerate(pipeline):
        stage = deal.get("deal_stage", "").strip()
        
        if stage not in ["Won", "Lost"]:
            continue
        
        account = account_map.get(deal["account"], {})
        product = product_map.get(deal["product"], {})
        product_name = deal.get("product", "GTX Basic")
        
        # Get value - use actual value or generate based on product
        actual_value = deal.get("close_value", "")
        if actual_value and float(actual_value) > 0:
            value = float(actual_value)
        else:
            # Generate realistic value based on product
            price_range = product_prices.get(product_name, (1000, 5000))
            value = random.randint(price_range[0], price_range[1])
        
        deal_id = f"WD-{i+1:04d}" if stage == "Won" else f"LD-{i+1:04d}"
        
        deal_record = {
            "deal_id": deal_id,
            "company": deal["account"],
            "industry": account.get("sector", "Technology").title() if account else "Technology",
            "value": value,
            "sales_rep": deal["sales_agent"],
            "region": account.get("office_location", "United States") if account else "United States",
            "product": deal.get("product", ""),
            "competitors": random.sample(competitors_list, k=random.randint(1, 3)),
            "timeline": generate_timeline(
                deal.get("engage_date", "2024-01-01"),
                deal.get("close_date", "2024-03-01"),
                stage
            )
        }
        
        if stage == "Won":
            deal_record["win_reason"] = random.choice([
                "Best value proposition",
                "Superior product features",
                "Strong relationship",
                "Fast implementation",
                "Industry expertise"
            ])
            won_deals.append(deal_record)
        else:
            deal_record["loss_reason"] = random.choice(loss_reasons_list)
            lost_deals.append(deal_record)
    
    # Limit to manageable numbers for demo (200 each)
    won_deals = won_deals[:200]
    lost_deals = lost_deals[:200]
    
    output = {
        "won_deals": won_deals,
        "lost_deals": lost_deals
    }
    
    with open("data/sample_deals.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Converted {len(won_deals)} won deals and {len(lost_deals)} lost deals")
    print(f"   Total: {len(won_deals) + len(lost_deals)} deals")

if __name__ == "__main__":
    convert()