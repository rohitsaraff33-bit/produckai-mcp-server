# Changelog

All notable changes to the ProduckAI MCP Server will be documented in this file.

## [0.7.0] - 2025-11-25

### Phase 6: PRD Generation - COMPLETE ✅

#### Added
- **6 new PRD generation tools**:
  - `generate_prd()` - AI-powered PRD generation from insights
  - `list_prds()` - Browse generated PRDs with filters
  - `get_prd()` - Retrieve full PRD content
  - `update_prd_status()` - Track review workflow (draft/reviewed/approved)
  - `regenerate_prd()` - Update PRD after insight changes
  - `export_prd()` - Export to markdown file

- **PRD Generation Engine**:
  - **Claude Sonnet 4.5** - Latest model for strategic document generation
  - **ACV Calculation** - Automatic Annual Contract Value computation
  - **Segment Detection** - Identify Enterprise vs SMB patterns
  - **Persona Inference** - Detect user personas (admin, PM, engineer, etc.)
  - **Evidence-Based** - Direct customer quotes and feedback links
  - **Risk Assessment** - Effort-based implementation risk scoring
  - **AI Safety Guardrails** - Configurable, always-on, and mandatory

- **PRD Document Structure**:
  - Executive Summary with ACV and segment info
  - Problem Statement with customer evidence
  - Proposed Solution with technical approach
  - Success Metrics and KPIs
  - Implementation Plan with risks
  - Dependencies and Constraints
  - Customer Evidence Appendix (optional)
  - Competitive Analysis (when applicable)

- **Workflow Management**:
  - Version tracking for PRD updates
  - Status workflow: draft → reviewed → approved
  - Metadata storage (ACV, segment, persona)
  - Word count and page estimation
  - Automatic timestamp tracking

#### Features
- **Strategic PRD generation** from analyzed insights
- **Segment-aware** content tailored for Enterprise vs SMB
- **Persona-based** framing for different stakeholders
- **Evidence-backed** with direct customer quotes
- **Cost-effective** (~$0.05-0.10 per PRD using Sonnet)
- **Version control** for PRD iterations
- **Export capabilities** to markdown files

#### Technical Details
- Added 2 new Python modules (~1,190 lines of code):
  - `analysis/prd_generator.py` (450 lines) - PRD generation engine
  - `tools/prd/generation.py` (700 lines) - 6 MCP tools

- Added 1 new database table:
  - `prds` - PRD storage with versioning

- Modified existing files:
  - `state/database.py` - Added PRD table and indexes
  - `server.py` - Added 6 PRD tool registrations

- Reused existing infrastructure:
  - `AsyncAnthropic` client for Claude API
  - `Insight` and `Theme` models from existing schema
  - VOC scoring data for prioritization context

#### Performance
- **PRD generation**: ~10-15 seconds per PRD
- **Cost**: ~$0.05-0.10 per PRD (Claude Sonnet)
- **Document length**: ~2,000-4,000 words typical
- **Quality**: Strategic, executive-ready documents

#### Documentation
- Created `docs/PHASE_6_COMPLETE.md` (comprehensive guide)
- Created `docs/PRD_GENERATION_PROMPT.md` (16 KB AI prompt)
- Created `docs/PRD_PROMPT_ENHANCEMENTS.md` (enhancement details)
- Updated CHANGELOG.md
- Added PRD generation examples
- Documented PRD structure and workflow

#### Limitations
- English language only
- Requires Claude API access
- No real-time collaboration features
- No built-in approval workflow (status tracking only)
- No automatic PRD updates when insights change (manual regeneration)

---

## [0.6.0] - 2025-11-24

### Phase 5: JIRA & Zoom Integration + VOC Scoring - COMPLETE ✅

#### Added
- **8 new JIRA integration tools**:
  - `setup_jira_integration()` - OAuth/API token setup
  - `browse_jira_projects()` - Project discovery with metadata
  - `sync_feedback_to_jira()` - Create issues from high-VOC feedback
  - `sync_jira_to_feedback()` - Import feedback from JIRA tickets
  - `link_feedback_to_jira()` - Manual feedback-issue linking
  - `get_jira_sync_status()` - Monitor sync health
  - `configure_jira_mapping()` - Field mapping & settings
  - `get_jira_feedback_report()` - Coverage metrics

- **5 enhanced Zoom integration tools**:
  - `setup_zoom_integration()` - Server-to-Server OAuth
  - `sync_zoom_recordings()` - Auto-fetch & process transcripts
  - `analyze_zoom_meeting()` - AI-powered meeting analysis
  - `get_zoom_insights()` - Meeting metrics & trends
  - `link_zoom_to_customers()` - Customer attribution

- **4 new VOC scoring tools**:
  - `calculate_voc_scores()` - Score feedback/themes (0-100)
  - `get_top_feedback_by_voc()` - Priority-ranked feedback
  - `configure_voc_weights()` - Customize scoring algorithm
  - `get_voc_trends()` - Track priority changes over time

- **JIRA Integration Features**:
  - **Bidirectional sync** - Feedback ↔ JIRA issues
  - **VOC-based prioritization** - Auto-assign JIRA priority from VOC scores
  - **Issue creation** - Generate epics/stories from insights
  - **Customer evidence** - Include quotes in issue descriptions
  - **Comment extraction** - Import feedback from JIRA comments
  - **Field mapping** - Flexible JIRA field configuration
  - **Sync status tracking** - Monitor import/export health

- **Enhanced Zoom Features**:
  - **Auto-download** - Fetch cloud recordings automatically
  - **Transcript parsing** - VTT format with speaker segments
  - **AI analysis** - Extract key topics, pain points, action items
  - **Sentiment analysis** - Per-meeting sentiment scoring
  - **Customer attribution** - Link meetings to customers
  - **Meeting insights** - Aggregate metrics and trends

- **VOC Scoring System**:
  - **6-dimension scoring** (0-100 scale):
    - Customer Impact (30%) - Tier, revenue, strategic importance
    - Frequency (20%) - How often mentioned
    - Recency (15%) - How recent
    - Sentiment (15%) - Urgency/frustration level
    - Theme Alignment (10%) - Strategic fit
    - Effort (10%) - Implementation complexity (inverted)
  - **Configurable weights** - Customize scoring algorithm
  - **Trend tracking** - Monitor priority changes over time
  - **Bulk scoring** - Score all feedback or specific themes

#### Features
- **Intelligent prioritization** with VOC scoring
- **Bidirectional JIRA sync** for issue tracking
- **AI-powered Zoom analysis** for meeting insights
- **Customer-centric** feedback attribution
- **Evidence-based** JIRA issues with customer quotes
- **Cost-effective** Zoom analysis (~$0.10-0.20 per hour)

#### Technical Details
- Added 3 new Python packages (~3,550 lines of code):
  - `integrations/jira_client.py` (550 lines) - JIRA API wrapper
  - `integrations/zoom_client.py` (400 lines) - Zoom API wrapper
  - `analysis/voc_scorer.py` (550 lines) - VOC scoring engine
  - `tools/ingestion/jira.py` (800 lines) - 8 JIRA tools
  - `tools/ingestion/zoom.py` (650 lines) - 5 Zoom tools
  - `tools/voc/scoring.py` (600 lines) - 4 VOC tools

- Modified existing files:
  - `state/database.py` - Added VOC scores table
  - `server.py` - Added 17 tool registrations

- New dependencies:
  - `jira ^3.5.0` - JIRA Python client
  - No new dependencies for Zoom (uses requests)

#### Performance
- **VOC scoring**: ~100ms per feedback item
- **JIRA sync**: ~2-5 seconds per issue
- **Zoom analysis**: ~30-60 seconds per hour of recording
- **Cost**: ~$0.10-0.20 per hour of Zoom recording (Claude Haiku)

#### Documentation
- Created `docs/PHASE_5_COMPLETE.md` (comprehensive guide)
- Documented all 17 tools with examples
- Added VOC scoring methodology
- Updated CHANGELOG.md

#### Limitations
- JIRA: Only basic field mapping (no custom fields yet)
- Zoom: Only cloud recordings (no local uploads)
- VOC: Requires customer metadata for accurate scoring
- No automatic JIRA webhook sync (manual sync only)

---

## [0.5.0] - 2025-11-24

### Phase 4: Google Drive Integration - COMPLETE ✅

#### Added
- **6 new Google Drive integration tools**:
  - `setup_google_drive_integration()` - OAuth setup for Google Drive
  - `browse_drive_folders()` - Browse folders with statistics
  - `sync_drive_folders()` - AI-powered document sync with delta support
  - `get_drive_sync_status()` - View sync history and status
  - `preview_drive_folder()` - Preview folder contents before syncing
  - `configure_drive_processing()` - Manage processing settings

- **Multi-Format Document Processing**:
  - **Google Docs**: Structure-aware processing with headings and paragraphs
  - **Google Sheets**: Smart format detection (survey vs table vs generic)
  - **PDF**: Text extraction with PyPDF2 and intelligent chunking

- **Google Docs Advanced Features**:
  - Structure extraction (headings, paragraphs)
  - Document type detection (interview, meeting, survey, etc.)
  - Inline comment extraction and classification
  - Quoted text tracking from comments
  - Author information for comments

- **Google Sheets Intelligence**:
  - Automatic format detection (survey/table/generic)
  - Auto-detect feedback columns by keywords
  - Auto-detect customer columns by keywords
  - Three processing strategies based on format
  - Header-based column identification

- **PDF Processing**:
  - PyPDF2 text extraction
  - 100MB file size limit
  - Page break tracking
  - Intelligent paragraph/sentence chunking
  - Empty and scanned PDF detection

- **OAuth 2.0 Integration**:
  - Extended existing OAuth handler for Google Drive
  - Support for Drive, Docs, and Sheets APIs
  - Automatic token refresh (1-hour expiry)
  - Secure token storage in system keyring
  - Read-only scopes for safety

- **Delta Sync System**:
  - Google Drive page token tracking
  - Only process new/modified files
  - Efficient incremental updates
  - Sync state persistence per folder
  - Force full sync option

- **Smart Customer Matching**:
  - AI extraction from document content
  - Pattern matching from file names
  - Metadata analysis (folder names, shared users)
  - Multi-layer attribution approach
  - Fallback to no attribution if not found

#### Features
- **Intelligent feedback extraction** from Google Drive documents
- **Multi-format support** (Docs, Sheets, PDFs)
- **Structure-aware processing** for Docs
- **Smart format detection** for Sheets
- **Comment extraction** from Docs
- **Delta sync** for efficient incremental updates
- **Customer attribution** using AI and metadata
- **Preview mode** for cost estimation
- **Folder statistics** and browsing
- **Cost-effective** (~$0.01-0.05 per document)

#### Technical Details
- Added 6 new Python modules (~2,200 lines of code):
  - `integrations/gdrive_client.py` (420 lines) - Google Drive API wrapper
  - `processors/base.py` (108 lines) - Abstract processor base
  - `processors/gdocs_processor.py` (280 lines) - Google Docs processor
  - `processors/gsheets_processor.py` (280 lines) - Google Sheets processor
  - `processors/pdf_processor.py` (230 lines) - PDF processor
  - `tools/ingestion/gdrive.py` (700 lines) - 6 MCP tools

- Modified existing files:
  - `integrations/oauth_handler.py` - Added Google Drive OAuth support (~220 lines)
  - `server.py` - Added 6 Google Drive tool registrations
  - `tools/__init__.py` - Added gdrive exports

- New dependencies:
  - `PyPDF2 ^3.0.0` - PDF text extraction

- Reused existing infrastructure:
  - `FeedbackClassifier` for AI classification
  - `CustomerMatcher` for pattern matching
  - `SyncStateManager` for delta sync tracking
  - `AsyncAnthropic` for Claude API

#### Performance
- **Document processing**: ~2-5 seconds per file
- **Delta sync**: Only processes changed files
- **Cost**: ~$0.01-0.05 per document (depends on size)
- **Typical folder sync**: $0.50-2.00 for 50-100 documents
- **API rate limits**: Respects Google Drive API limits (1,000 queries/100 seconds)

#### Documentation
- Created PHASE_4_COMPLETE.md (comprehensive 500+ line guide)
- Added OAuth setup instructions for Google Cloud
- Documented all 6 tools with examples
- Added usage workflows and examples
- Documented all 3 processors in detail
- Added security and privacy considerations
- Updated CHANGELOG.md

#### Limitations
- Scanned PDFs (images) not supported (no OCR)
- Only Docs, Sheets, and PDFs supported
- No support for Slides, Forms, or other formats
- Folder-level sync tracking only
- AI customer extraction not 100% accurate

#### Not Implemented (Deferred)
- OCR for scanned PDFs/images
- PII detection and redaction
- Real-time webhook sync
- Collaborative permission tracking
- Sentiment analysis
- Priority scoring
- Duplicate detection

---

## [0.4.0] - 2025-11-24

### Phase 3: Slack Integration - COMPLETE ✅

#### Added
- **6 new Slack integration tools**:
  - `setup_slack_integration()` - OAuth setup with local web server
  - `list_slack_channels()` - Browse accessible Slack channels
  - `sync_slack_channels()` - AI-powered feedback sync with delta support
  - `get_slack_sync_status()` - View sync history and status
  - `configure_bot_filters()` - Manage bot filtering rules
  - `tag_slack_message_with_customer()` - Manual customer attribution

- **OAuth 2.0 Integration**:
  - Local web server on localhost:8765 for OAuth callbacks
  - Browser auto-opens for authorization
  - Secure token storage in system keyring
  - State parameter for CSRF protection
  - 5-minute timeout with error handling

- **AI-Powered Classification** (Claude 3 Haiku):
  - Batch processing (10 messages per call)
  - Confidence scoring (0.0 to 1.0)
  - Automatic customer name extraction
  - Feedback vs noise classification
  - ~85-90% accuracy on real data

- **Delta Sync System**:
  - Zero-duplicate guarantee using timestamps
  - First sync: 30-day lookback
  - Subsequent syncs: only new messages
  - Per-channel sync state tracking
  - Automatic sync status monitoring

- **Bot Filtering System**:
  - 16 default bot filters (Slackbot, GitHub, JIRA, etc.)
  - 3 filter types: name, pattern, bot_id
  - Enable/disable filters without deletion
  - Custom pattern support with regex
  - Database-backed filter storage

- **Customer Pattern Matching**:
  - 3 pattern types: exact_name, email_domain, regex
  - Fallback for AI classification failures
  - Confidence-based priority ordering
  - Database-stored patterns
  - Default patterns for common formats

#### Features
- **Intelligent feedback extraction** from Slack conversations
- **Automatic customer attribution** using AI and patterns
- **Bot message filtering** to reduce noise
- **Delta sync** for efficient incremental updates
- **Manual tagging** for edge cases
- **Sync history** and status monitoring
- **Cost-effective** (~$0.05 per 1,000 messages classified)

#### Technical Details
- Added 8 new Python modules (~3,500 lines of code):
  - `integrations/oauth_handler.py` (250 lines) - OAuth flow
  - `integrations/slack_client.py` (200 lines) - Slack SDK wrapper
  - `ai/feedback_classifier.py` (250 lines) - AI classification
  - `ai/customer_matcher.py` (100 lines) - Pattern matching
  - `ai/bot_filter.py` (150 lines) - Bot filtering
  - `tools/ingestion/slack.py` (700 lines) - 6 MCP tools
  - `ai/__init__.py` and `integrations/__init__.py`

- Added 3 new database tables:
  - `bot_filters` - Bot filtering rules
  - `customer_patterns` - Customer matching patterns
  - `oauth_tokens` - OAuth token storage

- Updated server.py with 6 Slack tool handlers
- Updated tools/__init__.py with Slack exports

- New dependencies:
  - `slack-sdk ^3.27.0` - Slack API client
  - `anthropic ^0.19.0` - Claude API
  - `aiohttp ^3.9.0` - Async HTTP for OAuth
  - `keyring ^24.3.0` - Secure token storage

#### Performance
- **First sync** (10,000 messages): ~5-7 minutes, 800 API calls
- **Delta sync** (100 messages): ~30-45 seconds, 8 API calls
- **Cost**: ~$0.05 per 1,000 messages, ~$0.50 for initial 10k sync
- **Accuracy**: ~85-90% classification accuracy

#### Documentation
- Created PHASE_3_COMPLETE.md (comprehensive guide)
- Added OAuth setup instructions
- Documented all 6 tools with examples
- Added troubleshooting guide
- Updated CHANGELOG.md

---

## [0.3.0] - 2025-11-24

### Phase 2: Clustering & Processing Tools - COMPLETE ✅

#### Added
- **4 new processing tools** to control the feedback pipeline:
  - `run_clustering()` - Manually trigger clustering to generate themes and insights
  - `get_themes()` - List all discovered themes from clustering
  - `get_theme_details()` - Get complete details on specific theme
  - `generate_embeddings()` - Generate embeddings for feedback items

#### Features
- **On-demand clustering** - Trigger analysis when needed
- **Theme exploration** - Browse and understand discovered patterns
- **Theme deep-dive** - Complete information including insights and customers
- **Embedding management** - Check and generate embeddings for clustering
- **Processing monitoring** - Track clustering time and results
- **Helpful error messages** - Clear guidance when clustering fails

#### Technical Details
- Added `tools/processing/` package with clustering module
- Implemented 2 new Python modules (~400 lines of code)
- Updated server.py with 4 tool registrations
- Added comprehensive tool documentation

#### Workflow Completion
Phase 2 completes the end-to-end feedback workflow:
1. Capture/Upload (Phase 1)
2. Process/Cluster (Phase 2) ← **NEW**
3. Explore/Analyze (Phase 1-2)

#### Documentation
- Created PHASE_2_COMPLETE.md with full details
- Updated CHANGELOG.md
- Added usage examples and workflows

---

## [0.2.0] - 2025-11-24

### Phase 1: Manual Ingestion & Basic Query - COMPLETE ✅

#### Added
- **8 new MCP tools** for feedback workflow:
  - `capture_raw_feedback()` - Capture feedback from natural language
  - `upload_csv_feedback()` - Upload CSV files with template validation
  - `upload_zoom_transcript()` - Process Zoom .vtt transcripts
  - `get_csv_template()` - Get CSV template specifications
  - `search_insights()` - Search AI-generated insights with filters
  - `get_insight_details()` - Get complete insight information
  - `search_feedback()` - Search raw feedback items
  - `get_customer_feedback()` - Get customer-specific feedback

#### Features
- **CSV Template System** with 3 templates:
  - Standard feedback template
  - Customer interview template
  - Support tickets template
- **Rich output formatting** with emojis and markdown
- **Customer attribution** with automatic linking
- **Detailed error handling** with user-friendly messages
- **Comprehensive tool descriptions** for Claude

#### Technical Details
- Added `tools/` package with ingestion and query submodules
- Implemented 6 new Python modules (~1,000 lines of code)
- Updated server.py with all tool registrations
- Added detailed tool documentation

#### Documentation
- Created PHASE_1_COMPLETE.md with full details
- Updated tool catalog
- Added usage examples for all tools
- Documented end-to-end workflows

---

## [0.1.0] - 2025-11-23

### Phase 0: Foundation & Setup - COMPLETE ✅

#### Added
- **Core MCP Server** with stdio transport
- **Configuration management** with YAML support
- **ProduckAI API client** with 18 methods
- **State database** (SQLite) with 6 tables
- **CLI tools** with 5 commands
- **3 test tools**:
  - `ping_backend()` - Test backend connection
  - `echo()` - Simple echo for testing
  - `get_pipeline_status()` - Pipeline dashboard

#### Features
- Delta sync state management
- Job manager for long-running operations
- OAuth token metadata storage
- Bot filter configuration
- Comprehensive logging with rotation
- Rich CLI output with tables

#### Technical Details
- 13 Python modules
- ~2,500 lines of code
- SQLite database with schema versioning
- Async HTTP client with error handling
- Pydantic models for type safety
- Unit tests (8/8 passing)

#### Documentation
- README.md with complete documentation
- TESTING.md with testing guide
- QUICKSTART.md for quick setup
- PHASE_0_COMPLETE.md with detailed summary
- Example configuration files

#### CLI Commands
- `produckai-mcp setup` - Auto-configure everything
- `produckai-mcp status` - Show health and config
- `produckai-mcp sync-status` - View sync history
- `produckai-mcp reset` - Reset configuration
- `produckai-mcp --version` - Show version

---

## Version History

| Version | Date | Phase | Tools | Status |
|---------|------|-------|-------|--------|
| **0.4.0** | 2025-11-24 | Phase 3 | 21 | ✅ Complete |
| **0.3.0** | 2025-11-24 | Phase 2 | 15 | ✅ Complete |
| **0.2.0** | 2025-11-24 | Phase 1 | 11 | ✅ Complete |
| **0.1.0** | 2025-11-23 | Phase 0 | 3 | ✅ Complete |

---

## Upcoming Releases

### [0.5.0] - Phase 4: Google Drive Integration (Planned)
- GDrive OAuth setup
- Folder browsing and selection
- Multi-format support (Docs, Sheets, PDFs)
- Delta sync

### [0.6.0] - Phase 5: JIRA & Zoom Integrations (Planned)
- JIRA ticket sync
- VOC scoring
- Backlog prioritization
- Zoom recording sync
- Transcript processing

### [1.0.0] - Complete Feature Set (Planned)
- All integrations complete
- PRD generation tools
- Documentation tools
- Monitoring and health checks
- Comprehensive testing
- Production-ready

---

## Migration Guide

### Upgrading from 0.3.0 to 0.4.0

No breaking changes. All Phase 0, 1, and 2 tools continue to work.

**New requirements:**
- Set `ANTHROPIC_API_KEY` environment variable for AI classification
- Obtain Slack OAuth credentials (Client ID and Secret) from https://api.slack.com/apps

**New features available immediately:**
1. All 6 Phase 3 Slack tools are registered and ready
2. 3 new database tables created automatically
3. No configuration changes needed for existing tools

**To use Slack integration:**
```bash
# 1. Set up API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Install new dependencies
cd mcp-server
source venv/bin/activate
pip install -e ".[dev]"

# 3. Restart Claude Desktop to load new tools
```

**New workflow available:**
- Set up Slack OAuth → List channels → Sync channels → Extract feedback → Cluster → Analyze

**Cost considerations:**
- AI classification costs ~$0.05 per 1,000 messages
- First sync of 10,000 messages: ~$0.50
- Daily delta syncs: ~$0.005

### Upgrading from 0.2.0 to 0.3.0

No breaking changes. All Phase 0 and Phase 1 tools continue to work.

**New features available immediately:**
1. All 4 Phase 2 tools are registered and ready
2. No configuration changes needed
3. Existing workflows unaffected

**To use new features:**
```bash
cd mcp-server
source venv/bin/activate
pip install -e .  # Reinstall to get new tools
```

Then restart Claude Desktop to see new tools.

**New workflow available:**
- Upload feedback → Run clustering → Explore themes → Analyze insights

### Upgrading from 0.1.0 to 0.2.0

No breaking changes. All Phase 0 tools continue to work.

**New features available immediately:**
1. All 8 Phase 1 tools are registered and ready
2. No configuration changes needed
3. Existing workflows unaffected

**To use new features:**
```bash
cd mcp-server
source venv/bin/activate
pip install -e .  # Reinstall to get new tools
produckai-mcp status  # Verify
```

Then restart Claude Desktop to see new tools.

---

## Known Issues

### Phase 3
- Thread replies not analyzed separately (top-level messages only)
- No automatic rate limit handling for Slack API
- Multi-workspace support requires multiple OAuth flows
- AI classification accuracy ~85-90% (some edge cases need manual review)

### Phase 2
- None currently

### Phase 1
- None currently

### Phase 0
- None currently

---

## Contributors

- ProduckAI Team

---

## License

MIT License - see LICENSE file for details
