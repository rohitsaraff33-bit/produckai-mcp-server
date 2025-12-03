# ProduckAI MCP Server: Complete End-to-End Workflow

**Version:** 0.7.0
**Last Updated:** November 25, 2025
**From:** Raw Feedback → **To:** Strategic PRD

---

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Phase-by-Phase Guide](#phase-by-phase-guide)
3. [Complete Example](#complete-example)
4. [Decision Trees](#decision-trees)
5. [Best Practices](#best-practices)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Workflow Overview

### The Complete Feedback-to-PRD Pipeline

```
┌─────────────────┐
│  1. COLLECT     │  Slack, Google Drive, Zoom, JIRA, CSV
│   Feedback      │  → Raw feedback items in database
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. ENRICH      │  AI Classification + Customer Matching
│   & Validate    │  → Customer attribution, sentiment, metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. ANALYZE     │  Embeddings + Clustering
│   & Cluster     │  → Themes (grouped feedback) + AI Insights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. PRIORITIZE  │  VOC Scoring (6 dimensions)
│   by Impact     │  → Priority scores (0-100) per insight
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. DOCUMENT    │  AI-Powered PRD Generation
│   Strategy      │  → Executive-ready PRDs with evidence
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. EXECUTE     │  JIRA Sync + Export
│   & Track       │  → Issues created, PRDs exported, tracking
└─────────────────┘
```

**Total Time:** 5-15 minutes for 100 feedback items
**Output:** Strategic PRDs backed by customer evidence
**Cost:** ~$0.10-0.50 per complete workflow (AI API costs)

---

## Phase-by-Phase Guide

### Phase 1: Collect Feedback

**Goal:** Gather raw feedback from all sources into a centralized database.

#### 1A. Slack Integration

```python
# Initial setup (one-time)
setup_slack_integration(
    bot_token="xoxb-your-bot-token",
    user_token="xoxp-your-user-token"
)

# Discover channels
channels = list_slack_channels()
# Shows: #customer-feedback, #support, #sales-wins, etc.

# Sync specific channels
sync_slack_channels(
    channel_names=["customer-feedback", "support"],
    days_back=30,           # Initial sync: last 30 days
    auto_classify=True,     # AI extracts customer name + sentiment
    min_length=50           # Skip short messages
)

# Result: Feedback items with:
# - Original message text
# - Customer attribution (AI-detected)
# - Sentiment (positive/negative/neutral)
# - Metadata (channel, timestamp, user)
```

**Best Practice:** Start with 1-2 high-signal channels, then expand.

#### 1B. Google Drive Integration

```python
# Initial setup (one-time)
setup_google_drive_integration()
# Opens OAuth flow in browser

# Browse folders
folders = browse_drive_folders()
# Shows: Shared drives, My Drive, Team folders

# Preview before syncing
preview = preview_drive_folder(
    folder_id="abc123xyz",
    max_files=10
)
# Shows: File types, sizes, last modified

# Sync folder
sync_drive_folders(
    folder_ids=["abc123xyz"],
    recursive=True,         # Include subfolders
    file_types=["pdf", "docx", "txt"]
)

# Result: Documents processed and feedback extracted
```

**Best Practice:** Start with one "Customer Feedback" folder, then add more.

#### 1C. Zoom Integration

```python
# Initial setup (one-time)
setup_zoom_integration(
    account_id="your-account-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

# Auto-fetch recordings
sync_zoom_recordings(
    days_back=30,
    auto_classify=True,     # AI extracts feedback from transcripts
    min_duration=5          # Skip < 5 min meetings
)

# Deep-dive on specific meeting
analyze_zoom_meeting(
    meeting_id="123456789",
    include_sentiment=True,
    include_topics=True
)

# Result: Meeting transcripts processed, feedback extracted
```

**Best Practice:** Sync weekly to catch new customer calls.

#### 1D. JIRA Integration (Import Existing Feedback)

```python
# Initial setup (one-time)
setup_jira_integration(
    server_url="https://yourcompany.atlassian.net",
    email="pm@company.com",
    api_token="your-api-token"
)

# Import feedback from JIRA
sync_jira_to_feedback(
    project_key="SUPPORT",
    jql_filter="labels = customer_feedback",
    max_issues=100
)

# Result: JIRA tickets imported as feedback items
```

**Best Practice:** Import historical tickets for baseline data.

#### 1E. Manual Entry (Quick Capture)

```python
# Quick capture from conversations
capture_raw_feedback(
    text="Customer wants API to support GraphQL in addition to REST",
    customer_name="Acme Corp",
    source="pm_conversation",
    metadata={"priority": "high", "date": "2025-01-15"}
)

# Bulk upload from CSV
upload_csv_feedback(
    csv_path="/path/to/feedback.csv"
)

# Result: Feedback items added to database
```

**Best Practice:** Use for ad-hoc feedback from calls, emails, etc.

---

### Phase 2: Enrich & Validate

**Goal:** Ensure all feedback has customer attribution and is properly classified.

#### 2A. Review Sync Status

```python
# Check what's been synced
slack_status = get_slack_sync_status()
drive_status = get_drive_sync_status()
zoom_status = get_zoom_insights(days_back=30)

# Result: Summary of synced items, errors, delta sync cursors
```

#### 2B. Fix Customer Attribution

```python
# Search feedback without customer
unattributed = search_feedback(
    query="",
    limit=50
)

# Manually tag
for item in unattributed['results']:
    if not item.get('customer_name'):
        tag_slack_message_with_customer(
            feedback_id=item['id'],
            customer_name="Acme Corp"
        )
```

**Best Practice:** Fix attribution before clustering for accurate insights.

#### 2C. Configure Bot Filters (Slack)

```python
# Filter out noise
configure_bot_filters(
    action="add",
    filter_type="name",
    filter_value="zapier"
)

# Result: Automated messages excluded from future syncs
```

---

### Phase 3: Analyze & Cluster

**Goal:** Group similar feedback into themes and generate AI insights.

#### 3A. Generate Embeddings

```python
# Create vector embeddings for semantic search
generate_embeddings()

# Result: All feedback items now have embeddings
# Time: ~30 seconds for 100 items
# Cost: ~$0.01 (OpenAI embeddings)
```

**Best Practice:** Run after each major sync or weekly.

#### 3B. Run Clustering

```python
# Group feedback into themes
clustering_result = run_clustering(
    min_cluster_size=3,      # At least 3 items per theme
    max_clusters=20,         # Max 20 themes
    min_similarity=0.7       # 70% semantic similarity
)

# Result:
# - Themes created (grouped feedback)
# - Insights generated per theme (AI-powered)
# Time: ~1-2 minutes for 100 items
# Cost: ~$0.20 (Claude Haiku for insights)
```

#### 3C. Review Themes

```python
# Browse all themes
themes = get_themes(
    sort_by="feedback_count",
    limit=20
)

# Deep-dive on specific theme
theme_details = get_theme_details(theme_id="theme-xyz")
# Shows:
# - All feedback in theme
# - Customer breakdown
# - Sentiment distribution
# - Generated insight
```

**Best Practice:** Review themes manually, merge similar ones if needed.

---

### Phase 4: Prioritize by Impact

**Goal:** Score insights using VOC (Voice of Customer) methodology.

#### 4A. Calculate VOC Scores

```python
# Score all insights
calculate_voc_scores(
    target_type="feedback",  # or "theme"
    store_results=True       # Save to database
)

# Result: Each insight now has:
# - Total score (0-100)
# - Component scores (customer impact, frequency, recency, sentiment, etc.)
# Time: ~1 second for 100 items (local calculation)
```

**VOC Scoring Dimensions:**
- **Customer Impact (30%):** Tier, revenue, strategic importance
- **Frequency (20%):** How often mentioned
- **Recency (15%):** How recent
- **Sentiment (15%):** Urgency/frustration
- **Theme Alignment (10%):** Strategic fit
- **Effort (10%):** Implementation complexity (inverted)

#### 4B. Review Top Insights

```python
# Get highest-priority items
top_insights = get_top_feedback_by_voc(
    limit=10,
    min_score=75.0           # Only show VOC >= 75
)

# Result: Prioritized list of insights to work on
```

#### 4C. Customize Weights (Optional)

```python
# Adjust for your business priorities
configure_voc_weights(
    action="update",
    customer_impact=0.40,    # Increase (was 0.30)
    frequency=0.20,
    recency=0.15,
    sentiment=0.10,          # Decrease (was 0.15)
    theme_alignment=0.10,
    effort_estimate=0.05     # Decrease (was 0.10)
    # Must sum to 1.0
)
```

**Best Practice:** Start with defaults, adjust after first PRD cycle.

---

### Phase 5: Document Strategy (PRD Generation)

**Goal:** Generate executive-ready PRDs from high-priority insights.

#### 5A. Generate PRD

```python
# Get top insight
insights = search_insights(
    severity="high",
    min_priority_score=80,
    limit=1
)

insight_id = insights['insights'][0]['id']

# Generate PRD
prd = generate_prd(
    insight_id=insight_id,
    include_appendix=True,   # Customer breakdown table
    auto_save=True           # Save to database
)

# Result:
# - Full PRD in markdown format
# - Strategic alignment (ACV, evidence)
# - Solution hypothesis
# - Success metrics
# - Risk assessment
# - 3-phase roadmap
# Time: 10-15 seconds
# Cost: ~$0.05-0.10 (Claude Sonnet 4.5)
```

**Generated PRD Includes:**
- Header with severity, priority, ACV, customers
- Evidence-based problem statement
- 2-3+ direct customer quotes
- Segment concentration analysis (e.g., "75% Enterprise")
- Inferred persona (e.g., "Enterprise Integration Engineers")
- Testable hypothesis (IF-THEN-BECAUSE)
- MVP capabilities checklist
- AI safety guardrails (if applicable)
- Success metrics (business, operational, AI quality)
- Effort-based risk assessment
- 3-phase roadmap

#### 5B. Review PRD

```python
# View full PRD
full_prd = get_prd(prd_id=prd['prd_id'])

# Check metadata
print(f"ACV at Risk: ${full_prd['metadata']['total_acv']:,.0f}")
print(f"Primary Segment: {full_prd['metadata']['primary_segment']}")
print(f"Persona: {full_prd['metadata']['inferred_persona']}")
print(f"Word Count: {full_prd['prd']['word_count']}")
```

#### 5C. Update Status (Workflow Tracking)

```python
# Mark as reviewed
update_prd_status(
    prd_id=prd['prd_id'],
    status="reviewed"
)

# After stakeholder approval
update_prd_status(
    prd_id=prd['prd_id'],
    status="approved"
)
```

#### 5D. Export for Sharing

```python
# Export to markdown file
export_prd(
    prd_id=prd['prd_id'],
    output_path="~/Documents/PRDs/API_Rate_Limiting.md"
)

# Result: Markdown file saved
# Can be imported into Confluence, Notion, GitHub, etc.
```

#### 5E. Regenerate After Updates (Versioning)

```python
# If insight gets new feedback or changes
regenerate_prd(prd_id=prd['prd_id'])

# Result: New version created (v1 → v2)
# Previous version preserved in database
```

---

### Phase 6: Execute & Track

**Goal:** Create JIRA issues and track progress.

#### 6A. Sync to JIRA

```python
# Create JIRA issue from PRD
sync_feedback_to_jira(
    project_key="PROD",
    feedback_ids=[insight_id],  # Or theme_id for all related feedback
    issue_type="Epic",
    min_voc_score=75.0,         # Only sync high-priority
    auto_link=True              # Link back to feedback items
)

# Result: JIRA epic created with:
# - Summary: Insight title
# - Description: Key excerpts from PRD
# - Priority: Auto-assigned based on VOC score (90-100: Highest, 75-89: High, etc.)
# - Labels: customer_feedback, produckai
# - Links: Back to feedback items
```

#### 6B. Monitor Status

```python
# Check JIRA sync status
jira_status = get_jira_sync_status()

# Get report
report = get_jira_feedback_report()
# Shows:
# - Total feedback items
# - Linked to JIRA (%)
# - Top projects
# - Recent syncs
```

#### 6C. Track VOC Trends

```python
# Monitor how priorities change over time
trends = get_voc_trends(
    days_back=90,
    group_by="week"
)

# Result: Shows rising/falling issues
# Helps identify emerging vs declining concerns
```

---

## Complete Example

### Scenario: Weekly Feedback Triage

**Goal:** Process last week's feedback and create PRDs for top issues.

```python
# ============================================
# MONDAY: Sync All Sources
# ============================================

# Slack
sync_slack_channels(
    channel_names=["customer-feedback", "support"],
    days_back=7
)

# Zoom
sync_zoom_recordings(
    days_back=7,
    auto_classify=True
)

# Google Drive
sync_drive_folders(
    folder_ids=["feedback-folder-id"],
    recursive=True
)

print("✅ Synced all sources")


# ============================================
# TUESDAY: Process & Cluster
# ============================================

# Generate embeddings for new feedback
generate_embeddings()

# Run clustering
clustering = run_clustering(
    min_cluster_size=3,
    max_clusters=15,
    min_similarity=0.7
)

print(f"✅ Created {clustering['theme_count']} themes")
print(f"✅ Generated {clustering['insight_count']} insights")


# ============================================
# WEDNESDAY: Prioritize
# ============================================

# Calculate VOC scores
calculate_voc_scores(
    target_type="feedback",
    store_results=True
)

# Get top 10 insights
top_insights = get_top_feedback_by_voc(
    limit=10,
    min_score=70
)

print(f"✅ Top insight: {top_insights['feedback'][0]['title']}")
print(f"   VOC Score: {top_insights['feedback'][0]['total_score']:.1f}")
print(f"   ACV: ${top_insights['feedback'][0]['total_acv']:,.0f}")


# ============================================
# THURSDAY: Generate PRDs
# ============================================

prd_ids = []

# Generate PRDs for top 3 insights
for insight in top_insights['feedback'][:3]:
    prd = generate_prd(
        insight_id=insight['feedback_id'],
        include_appendix=True,
        auto_save=True
    )
    prd_ids.append(prd['prd_id'])
    print(f"✅ PRD Generated: {prd['title']}")
    print(f"   Word Count: {prd['stats']['word_count']}")
    print(f"   Pages: {prd['stats']['estimated_pages']}")

# List all PRDs
all_prds = list_prds(status="draft", limit=10)
print(f"\n✅ {all_prds['total']} PRDs ready for review")


# ============================================
# FRIDAY: Review & Sync to JIRA
# ============================================

# Review each PRD
for prd_id in prd_ids:
    full_prd = get_prd(prd_id=prd_id)

    # PM reviews → mark as reviewed
    update_prd_status(prd_id=prd_id, status="reviewed")

    # Export for stakeholders
    export_prd(prd_id=prd_id)

# After approval, sync to JIRA
for insight in top_insights['feedback'][:3]:
    sync_feedback_to_jira(
        project_key="PROD",
        feedback_ids=[insight['feedback_id']],
        issue_type="Epic",
        min_voc_score=70
    )

print("✅ Synced to JIRA")

# Monitor
status = get_jira_sync_status()
print(f"✅ {status['summary']['total_linked']} items linked to JIRA")


# ============================================
# SUMMARY
# ============================================

print("\n" + "="*50)
print("WEEKLY FEEDBACK TRIAGE COMPLETE")
print("="*50)
print(f"Feedback Synced: {feedback_count}")
print(f"Themes Created: {clustering['theme_count']}")
print(f"Insights Generated: {clustering['insight_count']}")
print(f"PRDs Created: {len(prd_ids)}")
print(f"JIRA Issues: {status['summary']['total_linked']}")
print("="*50)
```

**Total Time:** ~20-30 minutes
**Total Cost:** ~$0.50-1.00 (AI API costs)
**Output:** 3 executive-ready PRDs, synced to JIRA

---

## Decision Trees

### When to Sync?

```
Do you have new feedback from last week?
├─ Yes → Run delta sync (days_back=7)
└─ No  → Skip sync, use existing data

Is this your first time using ProduckAI?
├─ Yes → Initial sync (days_back=30-90)
└─ No  → Delta sync (days_back=7)
```

### When to Cluster?

```
Have you added >50 new feedback items?
├─ Yes → Run clustering
└─ No  → Wait for more data

Has it been >1 week since last clustering?
├─ Yes → Run clustering
└─ No  → Review existing themes
```

### When to Generate PRD?

```
Is the insight VOC score >75?
├─ Yes → Generate PRD
└─ No  → Wait for more supporting feedback

Does the insight have >5 feedback items?
├─ Yes → Generate PRD (good evidence)
└─ No  → Wait for more data

Is the severity High or Critical?
├─ Yes → Generate PRD immediately
└─ No  → Batch with other Medium insights
```

### Which Insights to Sync to JIRA?

```
Is the PRD status "approved"?
├─ Yes → Sync to JIRA
└─ No  → Complete review first

Is the VOC score >80?
├─ Yes → Sync as High/Highest priority
└─ No  → Check if it's part of roadmap theme

Is it already linked to JIRA?
├─ Yes → Skip (use link_feedback_to_jira for manual linking)
└─ No  → Sync
```

---

## Best Practices

### Data Collection

1. **Start Small, Expand Gradually**
   - Week 1: 1-2 Slack channels
   - Week 2: Add Google Drive folder
   - Week 3: Add Zoom recordings
   - Week 4: Import historical JIRA tickets

2. **Clean Data First**
   - Configure bot filters before syncing Slack
   - Review customer attribution weekly
   - Fix unattributed feedback before clustering

3. **Sync Frequency**
   - **Slack:** Daily or real-time (if webhook available)
   - **Zoom:** Weekly (after customer calls)
   - **Google Drive:** Weekly or on-demand
   - **JIRA:** One-time import + manual capture

### Clustering & Analysis

1. **Optimal Clustering Settings**
   - `min_cluster_size=3`: At least 3 feedback items per theme
   - `max_clusters=15-20`: Keeps themes manageable
   - `min_similarity=0.65-0.75`: Balance between grouping and specificity

2. **When to Re-cluster**
   - After adding >50 new feedback items
   - Weekly for active feedback channels
   - After fixing major customer attribution issues

3. **Theme Review**
   - Manually review top 10 themes weekly
   - Merge overly-specific themes
   - Flag themes for roadmap planning

### VOC Scoring

1. **Weight Customization**
   - **Enterprise SaaS:** Increase `customer_impact` to 0.35-0.40
   - **Product-Led Growth:** Increase `frequency` to 0.25-0.30
   - **Fast-Moving Startup:** Increase `recency` to 0.20
   - **Mature Product:** Increase `theme_alignment` to 0.15

2. **Score Thresholds**
   - **90-100:** Immediate action, generate PRD today
   - **75-89:** High priority, generate PRD this week
   - **60-74:** Medium priority, batch with similar items
   - **<60:** Monitor, wait for more supporting feedback

3. **Trend Monitoring**
   - Review VOC trends monthly
   - Identify rising issues (score increasing)
   - Identify declining issues (score decreasing)
   - Adjust roadmap based on trends

### PRD Generation

1. **When to Generate**
   - Insight has VOC score >75
   - Insight has >5 supporting feedback items
   - Severity is High or Critical
   - Part of approved roadmap theme

2. **Quality Checks**
   - Ensure PRD has 2-3+ direct customer quotes
   - Verify ACV calculation is correct
   - Check that persona inference makes sense
   - Review risk assessment aligns with effort

3. **Workflow**
   - Generate as "draft"
   - PM reviews → "reviewed"
   - Stakeholder approval → "approved"
   - Export for documentation
   - Sync to JIRA for execution

### JIRA Integration

1. **Sync Strategy**
   - Sync approved PRDs only
   - Use `min_voc_score=75` to filter
   - Link to existing epics when possible
   - Tag with "customer_feedback" label

2. **Priority Mapping**
   - VOC 90-100 → Highest
   - VOC 75-89 → High
   - VOC 60-74 → Medium
   - VOC <60 → Low

3. **Maintenance**
   - Review JIRA sync status weekly
   - Fix broken links manually
   - Update JIRA issues when insights change
   - Regenerate PRDs for closed issues (lessons learned)

---

## Common Patterns

### Pattern 1: Theme-Based Roadmap

**Use Case:** Plan quarterly roadmap based on clustered themes.

```python
# 1. Get all themes sorted by feedback count
themes = get_themes(sort_by="feedback_count", limit=10)

# 2. Calculate VOC scores for each theme
for theme in themes:
    calculate_voc_scores(
        target_type="theme",
        theme_id=theme['id']
    )

# 3. Get top themes by VOC
top_themes = get_top_feedback_by_voc(
    limit=5,
    min_score=70
)

# 4. Generate PRD for each theme
for theme in top_themes:
    # Get top insight from theme
    insights = search_insights(theme_id=theme['theme_id'], limit=1)

    prd = generate_prd(
        insight_id=insights['insights'][0]['id'],
        include_appendix=True
    )

    # Mark as reviewed
    update_prd_status(prd_id=prd['prd_id'], status="reviewed")

# 5. Present PRDs to stakeholders for Q1 planning
```

### Pattern 2: Customer-Specific Analysis

**Use Case:** Prepare for QBR with top customer.

```python
# 1. Get all feedback from customer
customer_feedback = get_customer_feedback(
    customer_name="Acme Corp",
    limit=50
)

# 2. Find related insights
insights = search_insights(
    query="",  # All insights
    limit=20
)

# Filter insights affecting this customer
acme_insights = [
    i for i in insights['insights']
    if "Acme Corp" in str(i.get('affected_customers', []))
]

# 3. Generate PRDs for top issues
for insight in acme_insights[:3]:
    prd = generate_prd(
        insight_id=insight['id'],
        include_appendix=True
    )

    # Export for QBR deck
    export_prd(
        prd_id=prd['prd_id'],
        output_path=f"~/QBR_Acme/{insight['title']}.md"
    )
```

### Pattern 3: Rapid Response to Critical Issue

**Use Case:** Urgent issue reported, need PRD in 10 minutes.

```python
# 1. Capture feedback immediately
capture_raw_feedback(
    text="Production outage: API rate limits causing 503 errors for 3 enterprise customers during peak hours",
    customer_name="Acme Corp, BigCo, MegaInc",
    source="pm_conversation",
    metadata={"severity": "critical", "priority": "P0"}
)

# 2. Search for related existing feedback
related = search_feedback(
    query="API rate limit",
    limit=10
)

# 3. Run quick clustering if needed
if len(related['results']) > 5:
    run_clustering(min_cluster_size=3)

# 4. Get insight
insights = search_insights(
    query="API rate limit",
    severity="critical",
    limit=1
)

# 5. Generate PRD
prd = generate_prd(
    insight_id=insights['insights'][0]['id'],
    include_appendix=True,
    auto_save=True
)

# 6. Export and share
export_prd(prd_id=prd['prd_id'])

# 7. Sync to JIRA as P0
sync_feedback_to_jira(
    project_key="PROD",
    feedback_ids=[insights['insights'][0]['id']],
    issue_type="Bug",
    min_voc_score=0  # Override, sync immediately
)

print(f"✅ PRD created and JIRA issue opened")
print(f"   PRD: ~/Downloads/{prd['title']}.md")
```

### Pattern 4: Monthly Executive Report

**Use Case:** Monthly summary for leadership.

```python
# 1. Get high-level stats
from datetime import datetime, timedelta

thirty_days_ago = datetime.now() - timedelta(days=30)

# Feedback metrics
slack_status = get_slack_sync_status()
zoom_insights = get_zoom_insights(days_back=30)

# Themes and insights
themes = get_themes(limit=50)
top_insights = get_top_feedback_by_voc(limit=10, min_score=70)

# VOC trends
trends = get_voc_trends(days_back=90, group_by="month")

# PRDs
prds = list_prds(limit=50)

# JIRA
jira_report = get_jira_feedback_report()

# 2. Generate summary report
print("="*60)
print("MONTHLY FEEDBACK SUMMARY")
print("="*60)
print(f"\n📊 COLLECTION")
print(f"   Slack Messages: {slack_status['summary']['total_messages']}")
print(f"   Zoom Meetings: {zoom_insights['summary']['total_meetings']}")
print(f"   Total Feedback Items: {len(themes) * 5}")  # Rough estimate
print(f"\n🎯 ANALYSIS")
print(f"   Themes Created: {len(themes)}")
print(f"   Top 3 Themes:")
for i, theme in enumerate(themes[:3], 1):
    print(f"      {i}. {theme['title']} ({theme['feedback_count']} items)")
print(f"\n📝 PRDs GENERATED")
print(f"   Total PRDs: {prds['total']}")
print(f"   Draft: {prds['summary']['status_breakdown'].get('draft', 0)}")
print(f"   Approved: {prds['summary']['status_breakdown'].get('approved', 0)}")
print(f"\n🎫 JIRA INTEGRATION")
print(f"   Items Linked: {jira_report['summary']['total_linked']}")
print(f"   Coverage: {jira_report['summary']['coverage_percentage']:.1f}%")
print(f"\n📈 TOP PRIORITIES (VOC)")
for i, insight in enumerate(top_insights['feedback'][:5], 1):
    print(f"   {i}. {insight['title']}")
    print(f"      Score: {insight['total_score']:.1f}, ACV: ${insight['total_acv']:,.0f}")
print("="*60)
```

---

## Troubleshooting

### Issue: Low Customer Attribution Rate

**Symptom:** Many feedback items missing `customer_name`

**Solutions:**
1. **Enable auto-classification in Slack sync:**
   ```python
   sync_slack_channels(
       channel_names=["feedback"],
       auto_classify=True  # AI extracts customer names
   )
   ```

2. **Manually tag high-value feedback:**
   ```python
   search_feedback(query="", limit=50)
   # Review and tag manually
   tag_slack_message_with_customer(
       feedback_id="abc123",
       customer_name="Acme Corp"
   )
   ```

3. **Improve Slack naming conventions:**
   - Ask team to mention customer names in messages
   - Use format: "[Customer Name] Issue description"

### Issue: Themes Too Granular or Too Broad

**Symptom:** 50+ tiny themes or 3 giant themes

**Solutions:**
1. **Adjust clustering parameters:**
   ```python
   # Too granular (50+ themes)
   run_clustering(
       min_cluster_size=5,      # Increase from 3
       max_clusters=15,         # Decrease from 20
       min_similarity=0.65      # Decrease from 0.70
   )

   # Too broad (3 themes)
   run_clustering(
       min_cluster_size=3,
       max_clusters=25,         # Increase from 15
       min_similarity=0.75      # Increase from 0.70
   )
   ```

2. **Review and merge manually:**
   - Use `get_themes()` to review
   - Identify similar themes
   - Re-run clustering with adjusted params

### Issue: PRD Content Too Generic

**Symptom:** PRD lacks specific customer quotes or context

**Solutions:**
1. **Ensure insight has supporting feedback:**
   ```python
   insight_details = get_insight_details(insight_id="abc123")
   # Check: insight_details['supporting_feedback']
   # Should have 5-10 direct quotes
   ```

2. **Add more feedback to theme before generating PRD:**
   - Sync more sources
   - Manually capture related feedback
   - Re-cluster to update insights

3. **Regenerate after adding feedback:**
   ```python
   regenerate_prd(prd_id="prd-xyz")
   ```

### Issue: VOC Scores All Similar

**Symptom:** All insights score 60-70, hard to prioritize

**Solutions:**
1. **Add customer revenue data:**
   - Ensure `affected_customers` has `acv` field
   - Customer Impact component heavily weights ACV

2. **Customize VOC weights:**
   ```python
   # Emphasize customer impact
   configure_voc_weights(
       action="update",
       customer_impact=0.40,  # Increase
       frequency=0.20,
       recency=0.10,          # Decrease
       sentiment=0.15,
       theme_alignment=0.10,
       effort_estimate=0.05   # Decrease
   )
   ```

3. **Ensure recency data is fresh:**
   - Sync feedback regularly
   - Recency component decays over time

### Issue: JIRA Sync Fails

**Symptom:** `sync_feedback_to_jira` returns error

**Solutions:**
1. **Verify JIRA credentials:**
   ```python
   setup_jira_integration(
       server_url="https://yourcompany.atlassian.net",
       email="your-email@company.com",
       api_token="your-api-token"  # Check expiration
   )
   ```

2. **Check project permissions:**
   - Ensure API token user can create issues in project
   - Verify project key is correct

3. **Review sync status:**
   ```python
   status = get_jira_sync_status()
   # Check: status['errors']
   ```

---

## Summary

**The ProduckAI Workflow in 6 Steps:**

1. **Collect** → Sync feedback from all sources (Slack, Drive, Zoom, JIRA)
2. **Enrich** → AI classification, customer attribution, sentiment
3. **Analyze** → Embeddings + clustering = Themes + Insights
4. **Prioritize** → VOC scoring = Priority scores (0-100)
5. **Document** → AI-powered PRD generation = Strategic specs
6. **Execute** → JIRA sync + Export = Issues tracked, PRDs shared

**Key Metrics:**
- **Time:** 20-30 minutes per week
- **Cost:** ~$0.50-1.00 per workflow
- **Output:** 3-5 executive-ready PRDs per week
- **Impact:** Evidence-backed product decisions

**Success Indicators:**
- ✅ 80%+ feedback has customer attribution
- ✅ 10-20 meaningful themes identified
- ✅ Top 5 insights have VOC scores >75
- ✅ 3-5 PRDs generated per week
- ✅ 80%+ PRDs approved and synced to JIRA

---

**Ready to start?** Follow the [Complete Example](#complete-example) for your first workflow!

---

*For questions or issues, see [Troubleshooting](#troubleshooting) or refer to individual phase documentation.*
