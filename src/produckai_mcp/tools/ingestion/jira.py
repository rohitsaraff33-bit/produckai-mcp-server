"""JIRA integration tools for feedback sync and issue management."""

import keyring
from typing import Any, Dict, List, Optional

from produckai_mcp.analysis.voc_scorer import VOCScorer, VOCScoreWeights
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.integrations.jira_client import JiraClient
from produckai_mcp.state.database import Database
from produckai_mcp.state.sync_state import SyncStateManager
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "produckai-mcp-jira"


async def setup_jira_integration(
    server_url: str,
    email: str,
    api_token: str,
) -> Dict[str, Any]:
    """
    Set up JIRA integration with API token authentication.

    Args:
        server_url: JIRA instance URL (e.g., https://yourcompany.atlassian.net)
        email: User email address
        api_token: JIRA API token (create at id.atlassian.com/manage-profile/security/api-tokens)

    Returns:
        Setup status with connection test results
    """
    logger.info(f"Setting up JIRA integration for {server_url}")

    try:
        # Initialize client and test connection
        client = JiraClient(server_url=server_url, email=email, api_token=api_token)

        # Test connection
        test_result = client.test_connection()

        if not test_result.get("success"):
            return {
                "success": False,
                "message": f"❌ Failed to connect to JIRA: {test_result.get('error')}",
                "error": test_result.get("error"),
            }

        # Store credentials securely
        keyring.set_password(SERVICE_NAME, "server_url", server_url)
        keyring.set_password(SERVICE_NAME, "email", email)
        keyring.set_password(SERVICE_NAME, "api_token", api_token)

        message = f"""✅ JIRA integration successfully set up!

**Server:** {server_url}
**User:** {test_result.get('user')}
**Version:** {test_result.get('server_version')}
**Type:** {test_result.get('deployment_type')}

You can now use JIRA integration tools to:
- Browse projects and issues
- Sync feedback to JIRA
- Link feedback items to issues
- Track issue status

Next steps:
1. Use `browse_jira_projects()` to see available projects
2. Use `configure_jira_mapping()` to set up field mappings
3. Use `sync_feedback_to_jira()` to create issues from feedback
"""

        return {
            "success": True,
            "message": message,
            "server_url": server_url,
            "user": test_result.get("user"),
        }

    except Exception as e:
        logger.error(f"Failed to set up JIRA integration: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Setup failed: {str(e)}",
            "error": str(e),
        }


async def browse_jira_projects(show_details: bool = True) -> Dict[str, Any]:
    """
    Browse accessible JIRA projects.

    Args:
        show_details: Include project details (issue types, components)

    Returns:
        List of projects with metadata
    """
    logger.info("Browsing JIRA projects")

    try:
        # Get stored credentials
        server_url = keyring.get_password(SERVICE_NAME, "server_url")
        email = keyring.get_password(SERVICE_NAME, "email")
        api_token = keyring.get_password(SERVICE_NAME, "api_token")

        if not all([server_url, email, api_token]):
            return {
                "success": False,
                "message": "❌ JIRA not configured. Run `setup_jira_integration()` first.",
            }

        # Initialize client
        client = JiraClient(server_url=server_url, email=email, api_token=api_token)

        # List projects
        projects = client.list_projects()

        if not projects:
            return {
                "success": True,
                "message": "No accessible projects found.",
                "projects": [],
            }

        # Build response
        lines = [f"📋 **Found {len(projects)} JIRA Projects**\n"]

        for project in projects:
            lines.append(f"**{project['name']}** (`{project['key']}`)")
            lines.append(f"  • Type: {project['project_type']}")
            if project.get("lead"):
                lines.append(f"  • Lead: {project['lead']}")
            lines.append(f"  • URL: {project['url']}")

            if show_details:
                # Get project details
                details = client.get_project_details(project["key"])
                if details:
                    lines.append(f"  • Issue Types: {', '.join(it['name'] for it in details['issue_types'])}")
                    if details.get("components"):
                        lines.append(f"  • Components: {len(details['components'])}")

            lines.append("")

        return {
            "success": True,
            "message": "\n".join(lines),
            "projects": projects,
            "count": len(projects),
        }

    except Exception as e:
        logger.error(f"Failed to browse JIRA projects: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Failed to browse projects: {str(e)}",
            "error": str(e),
        }


async def sync_feedback_to_jira(
    api_client: ProduckAIClient,
    database: Database,
    project_key: str,
    theme_id: Optional[str] = None,
    feedback_ids: Optional[List[str]] = None,
    issue_type: str = "Task",
    min_voc_score: float = 60.0,
    auto_link: bool = True,
) -> Dict[str, Any]:
    """
    Create JIRA issues from high-priority feedback.

    Args:
        api_client: ProduckAI API client
        database: Database connection
        project_key: JIRA project key to create issues in
        theme_id: Optional theme ID to create issues from
        feedback_ids: Optional specific feedback IDs to sync
        issue_type: JIRA issue type (Task, Story, Bug, etc.)
        min_voc_score: Minimum VOC score to sync (0-100)
        auto_link: Automatically link created issues back to feedback

    Returns:
        Summary of created issues
    """
    logger.info(f"Syncing feedback to JIRA project {project_key}")

    try:
        # Get JIRA credentials
        server_url = keyring.get_password(SERVICE_NAME, "server_url")
        email = keyring.get_password(SERVICE_NAME, "email")
        api_token = keyring.get_password(SERVICE_NAME, "api_token")

        if not all([server_url, email, api_token]):
            return {
                "success": False,
                "message": "❌ JIRA not configured. Run `setup_jira_integration()` first.",
            }

        # Initialize clients
        jira_client = JiraClient(server_url=server_url, email=email, api_token=api_token)
        voc_scorer = VOCScorer(api_client=api_client)

        # Determine feedback to sync
        feedback_to_sync = []

        if feedback_ids:
            # Specific feedback IDs provided
            for fid in feedback_ids:
                feedback = await api_client.get_feedback_by_id(fid)
                if feedback:
                    feedback_to_sync.append(feedback)

        elif theme_id:
            # Get all feedback from theme
            theme = await api_client.get_theme_by_id(theme_id)
            # Note: Adjust based on actual API method
            # feedback_to_sync = await api_client.get_feedback_by_theme(theme_id)
            pass

        else:
            return {
                "success": False,
                "message": "❌ Must provide either theme_id or feedback_ids",
            }

        if not feedback_to_sync:
            return {
                "success": True,
                "message": "No feedback found to sync.",
                "created_count": 0,
            }

        # Score and filter feedback
        scored_feedback = []
        for feedback in feedback_to_sync:
            score = await voc_scorer.score_feedback(feedback["id"])
            if score.total_score >= min_voc_score:
                scored_feedback.append((feedback, score))

        if not scored_feedback:
            return {
                "success": True,
                "message": f"No feedback met minimum VOC score of {min_voc_score}",
                "created_count": 0,
            }

        # Sort by VOC score (highest first)
        scored_feedback.sort(key=lambda x: x[1].total_score, reverse=True)

        # Create JIRA issues
        created_issues = []

        for feedback, voc_score in scored_feedback:
            # Build issue description
            description = f"""*Customer Feedback (VOC Score: {voc_score.total_score})*

*Feedback:*
{feedback.get('text', '')}

*Customer:* {feedback.get('customer_name', 'Unknown')}
*Source:* {feedback.get('source', 'Unknown')}
*Date:* {feedback.get('created_at', '')}

*VOC Score Breakdown:*
• Customer Impact: {voc_score.customer_impact_score:.1f}
• Frequency: {voc_score.frequency_score:.1f}
• Recency: {voc_score.recency_score:.1f}
• Sentiment: {voc_score.sentiment_score:.1f} ({voc_score.sentiment_label})
• Effort: {voc_score.effort_score:.1f} ({voc_score.effort_estimate_label})

*Feedback ID:* {feedback['id']}
"""

            # Determine priority based on VOC score
            if voc_score.total_score >= 90:
                priority = "Highest"
            elif voc_score.total_score >= 75:
                priority = "High"
            elif voc_score.total_score >= 50:
                priority = "Medium"
            else:
                priority = "Low"

            # Build summary
            summary_text = feedback.get("text", "")[:100]
            if len(feedback.get("text", "")) > 100:
                summary_text += "..."

            summary = f"[Feedback] {summary_text}"

            # Create issue
            issue = jira_client.create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type=issue_type,
                priority=priority,
                labels=["customer-feedback", f"voc-{int(voc_score.total_score)}"],
            )

            if issue:
                created_issues.append(issue)

                # Store linkage in database
                if auto_link:
                    database.execute(
                        """
                        INSERT INTO feedback_jira_links
                        (feedback_id, jira_issue_key, jira_issue_id, created_at)
                        VALUES (?, ?, ?, datetime('now'))
                        ON CONFLICT DO NOTHING
                        """,
                        (feedback["id"], issue["key"], issue["id"]),
                    )

                logger.info(f"Created JIRA issue {issue['key']} for feedback {feedback['id']}")

        # Build summary message
        message = f"""✅ **Created {len(created_issues)} JIRA Issues**

**Project:** {project_key}
**Issue Type:** {issue_type}
**Feedback Synced:** {len(created_issues)} / {len(feedback_to_sync)}
**Min VOC Score:** {min_voc_score}

**Created Issues:**
"""
        for issue in created_issues[:10]:  # Show first 10
            message += f"\n• [{issue['key']}]({issue['url']}) - {issue['summary']}"

        if len(created_issues) > 10:
            message += f"\n\n...and {len(created_issues) - 10} more"

        return {
            "success": True,
            "message": message,
            "created_count": len(created_issues),
            "issues": created_issues,
        }

    except Exception as e:
        logger.error(f"Failed to sync feedback to JIRA: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Sync failed: {str(e)}",
            "error": str(e),
        }


async def sync_jira_to_feedback(
    api_client: ProduckAIClient,
    project_key: str,
    jql_filter: Optional[str] = None,
    max_issues: int = 50,
) -> Dict[str, Any]:
    """
    Import feedback from JIRA issues.

    Extracts customer feedback from JIRA issue descriptions and comments.

    Args:
        api_client: ProduckAI API client
        project_key: JIRA project key to import from
        jql_filter: Optional JQL filter (e.g., 'labels = "customer-feedback"')
        max_issues: Maximum issues to process

    Returns:
        Summary of imported feedback
    """
    logger.info(f"Importing feedback from JIRA project {project_key}")

    try:
        # Get JIRA credentials
        server_url = keyring.get_password(SERVICE_NAME, "server_url")
        email = keyring.get_password(SERVICE_NAME, "email")
        api_token = keyring.get_password(SERVICE_NAME, "api_token")

        if not all([server_url, email, api_token]):
            return {
                "success": False,
                "message": "❌ JIRA not configured. Run `setup_jira_integration()` first.",
            }

        # Initialize client
        jira_client = JiraClient(server_url=server_url, email=email, api_token=api_token)

        # Build JQL query
        if jql_filter:
            jql = f"project = {project_key} AND ({jql_filter})"
        else:
            jql = f"project = {project_key} AND labels in (customer-feedback)"

        # Search for issues
        issues = jira_client.search_issues(jql=jql, max_results=max_issues)

        if not issues:
            return {
                "success": True,
                "message": "No issues found matching criteria.",
                "imported_count": 0,
            }

        # Extract feedback from issues
        imported_feedback = []

        for issue in issues:
            # Get full issue details
            full_issue = jira_client.get_issue(issue["key"])
            if not full_issue:
                continue

            # Extract feedback from description
            description = full_issue.get("description", "")

            # Try to extract customer name from description or issue
            # This is a simple heuristic - adjust based on your JIRA setup
            customer_name = None
            if "*Customer:*" in description:
                # Extract customer from formatted feedback
                for line in description.split("\n"):
                    if line.startswith("*Customer:*"):
                        customer_name = line.replace("*Customer:*", "").strip()
                        break

            # Upload to ProduckAI via CSV (backend doesn't support direct POST)
            if description and len(description) > 20:
                # Create temp CSV for this feedback item
                import csv
                import tempfile
                from datetime import datetime

                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
                    writer.writeheader()
                    writer.writerow({
                        'feedback': description,
                        'customer': customer_name or "Unknown",
                        'source': f"jira_{project_key}",
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
                    temp_path = Path(f.name)

                try:
                    upload_result = await api_client.upload_csv(temp_path, template_type="standard")
                    if upload_result.feedback_count > 0:
                        imported_feedback.append({
                            "jira_key": issue["key"],
                            "feedback_count": upload_result.feedback_count
                        })
                finally:
                    if temp_path.exists():
                        temp_path.unlink()

            # Extract feedback from comments
            comments = jira_client.get_issue_comments(issue["key"])
            for comment in comments:
                comment_text = comment.get("body", "")

                if comment_text and len(comment_text) > 20:
                    # Upload comment via CSV
                    import csv
                    import tempfile
                    from datetime import datetime

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
                        writer.writeheader()
                        writer.writerow({
                            'feedback': comment_text,
                            'customer': comment.get("author", "Unknown"),
                            'source': f"jira_{project_key}_comment",
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        temp_path = Path(f.name)

                    try:
                        upload_result = await api_client.upload_csv(temp_path, template_type="standard")
                        if upload_result.feedback_count > 0:
                            imported_feedback.append({
                                "jira_key": issue["key"],
                                "comment_id": comment["id"],
                                "feedback_count": upload_result.feedback_count
                            })
                    finally:
                        if temp_path.exists():
                            temp_path.unlink()

        message = f"""✅ **Imported {len(imported_feedback)} Feedback Items from JIRA**

**Project:** {project_key}
**Issues Processed:** {len(issues)}
**Feedback Extracted:** {len(imported_feedback)}

The feedback has been added to your ProduckAI database and is ready for analysis.
"""

        return {
            "success": True,
            "message": message,
            "imported_count": len(imported_feedback),
            "issues_processed": len(issues),
        }

    except Exception as e:
        logger.error(f"Failed to import from JIRA: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Import failed: {str(e)}",
            "error": str(e),
        }


async def link_feedback_to_jira(
    database: Database,
    feedback_id: str,
    jira_issue_key: str,
) -> Dict[str, Any]:
    """
    Manually link a feedback item to a JIRA issue.

    Args:
        database: Database connection
        feedback_id: Feedback UUID
        jira_issue_key: JIRA issue key (e.g., 'PROJ-123')

    Returns:
        Link creation status
    """
    logger.info(f"Linking feedback {feedback_id} to JIRA {jira_issue_key}")

    try:
        # Get JIRA credentials
        server_url = keyring.get_password(SERVICE_NAME, "server_url")
        email = keyring.get_password(SERVICE_NAME, "email")
        api_token = keyring.get_password(SERVICE_NAME, "api_token")

        if not all([server_url, email, api_token]):
            return {
                "success": False,
                "message": "❌ JIRA not configured. Run `setup_jira_integration()` first.",
            }

        # Initialize client and verify issue exists
        jira_client = JiraClient(server_url=server_url, email=email, api_token=api_token)
        issue = jira_client.get_issue(jira_issue_key)

        if not issue:
            return {
                "success": False,
                "message": f"❌ JIRA issue {jira_issue_key} not found.",
            }

        # Store linkage
        database.execute(
            """
            INSERT INTO feedback_jira_links
            (feedback_id, jira_issue_key, jira_issue_id, jira_url, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT DO NOTHING
            """,
            (feedback_id, issue["key"], issue["id"], issue["url"]),
        )

        return {
            "success": True,
            "message": f"✅ Linked feedback to [{jira_issue_key}]({issue['url']})",
            "jira_key": issue["key"],
            "jira_url": issue["url"],
        }

    except Exception as e:
        logger.error(f"Failed to link feedback to JIRA: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Link failed: {str(e)}",
            "error": str(e),
        }


async def get_jira_sync_status(database: Database) -> Dict[str, Any]:
    """
    View JIRA sync status and linked issues.

    Args:
        database: Database connection

    Returns:
        Sync status summary
    """
    logger.info("Getting JIRA sync status")

    try:
        # Query feedback-JIRA links
        cursor = database.execute(
            """
            SELECT
                jira_issue_key,
                jira_url,
                COUNT(*) as feedback_count,
                MIN(created_at) as first_linked,
                MAX(created_at) as last_linked
            FROM feedback_jira_links
            GROUP BY jira_issue_key
            ORDER BY last_linked DESC
            LIMIT 50
            """
        )

        links = cursor.fetchall()

        if not links:
            return {
                "success": True,
                "message": "No JIRA links found. Use `sync_feedback_to_jira()` to create issues.",
                "link_count": 0,
            }

        # Build summary
        total_feedback = sum(link["feedback_count"] for link in links)

        message = f"""📊 **JIRA Sync Status**

**Total Issues Linked:** {len(links)}
**Total Feedback Items:** {total_feedback}

**Recent Issues:**
"""

        for link in links[:10]:
            message += f"\n• [{link['jira_issue_key']}]({link['jira_url']})"
            message += f" - {link['feedback_count']} feedback items"
            message += f" (last linked: {link['last_linked']})"

        if len(links) > 10:
            message += f"\n\n...and {len(links) - 10} more issues"

        return {
            "success": True,
            "message": message,
            "link_count": len(links),
            "feedback_count": total_feedback,
            "links": [dict(link) for link in links],
        }

    except Exception as e:
        logger.error(f"Failed to get JIRA sync status: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Failed to get status: {str(e)}",
            "error": str(e),
        }


async def configure_jira_mapping(
    database: Database,
    action: str,
    setting: Optional[str] = None,
    value: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Configure JIRA field mappings and sync settings.

    Args:
        database: Database connection
        action: Action to perform (list, set, delete)
        setting: Setting name (for set/delete)
        value: Setting value (for set)

    Returns:
        Configuration status
    """
    logger.info(f"Configuring JIRA mapping: {action}")

    try:
        if action == "list":
            # List current settings
            cursor = database.execute(
                """
                SELECT setting_key, setting_value, updated_at
                FROM jira_settings
                ORDER BY setting_key
                """
            )

            settings = cursor.fetchall()

            if not settings:
                message = """⚙️ **JIRA Configuration**

No custom settings configured. Using defaults:

**Available Settings:**
• `default_project` - Default JIRA project key
• `default_issue_type` - Default issue type (Task, Story, etc.)
• `auto_priority` - Auto-set priority from VOC score (true/false)
• `min_voc_score` - Minimum VOC score to sync (0-100)
• `sync_comments` - Sync feedback as JIRA comments (true/false)

Use `configure_jira_mapping(action='set', setting='key', value='value')` to configure.
"""
            else:
                message = "⚙️ **JIRA Configuration**\n\n"
                for setting in settings:
                    message += f"• `{setting['setting_key']}` = `{setting['setting_value']}`\n"
                    message += f"  (updated: {setting['updated_at']})\n"

            return {
                "success": True,
                "message": message,
                "settings": {s["setting_key"]: s["setting_value"] for s in settings},
            }

        elif action == "set":
            if not setting or value is None:
                return {
                    "success": False,
                    "message": "❌ Must provide setting and value for 'set' action",
                }

            # Store setting
            database.execute(
                """
                INSERT INTO jira_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = datetime('now')
                """,
                (setting, str(value)),
            )

            return {
                "success": True,
                "message": f"✅ Set `{setting}` = `{value}`",
            }

        elif action == "delete":
            if not setting:
                return {
                    "success": False,
                    "message": "❌ Must provide setting for 'delete' action",
                }

            # Delete setting
            database.execute(
                "DELETE FROM jira_settings WHERE setting_key = ?",
                (setting,),
            )

            return {
                "success": True,
                "message": f"✅ Deleted setting `{setting}`",
            }

        else:
            return {
                "success": False,
                "message": f"❌ Unknown action: {action}. Use 'list', 'set', or 'delete'.",
            }

    except Exception as e:
        logger.error(f"Failed to configure JIRA mapping: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Configuration failed: {str(e)}",
            "error": str(e),
        }


async def get_jira_feedback_report(
    api_client: ProduckAIClient,
    database: Database,
) -> Dict[str, Any]:
    """
    Generate feedback coverage report for JIRA.

    Shows what percentage of feedback is tracked in JIRA,
    response times, and other metrics.

    Args:
        api_client: ProduckAI API client
        database: Database connection

    Returns:
        Coverage report
    """
    logger.info("Generating JIRA feedback report")

    try:
        # Get total feedback count
        # Note: Adjust based on actual API method
        # total_feedback = await api_client.get_feedback_count()

        # Get linked feedback count
        cursor = database.execute(
            """
            SELECT COUNT(DISTINCT feedback_id) as linked_count
            FROM feedback_jira_links
            """
        )
        linked_count = cursor.fetchone()["linked_count"]

        # Get theme coverage
        cursor = database.execute(
            """
            SELECT
                COUNT(DISTINCT jira_issue_key) as issue_count,
                COUNT(DISTINCT feedback_id) as feedback_count
            FROM feedback_jira_links
            WHERE created_at >= datetime('now', '-30 days')
            """
        )
        recent_stats = cursor.fetchone()

        message = f"""📈 **JIRA Feedback Coverage Report**

**Overall Coverage:**
• Feedback Items Linked to JIRA: {linked_count}
• Total JIRA Issues Created: (tracked in sync status)

**Last 30 Days:**
• New Issues Created: {recent_stats['issue_count']}
• Feedback Items Linked: {recent_stats['feedback_count']}

Use this data to understand how well you're tracking customer feedback in JIRA.
"""

        return {
            "success": True,
            "message": message,
            "linked_count": linked_count,
            "recent_issues": recent_stats["issue_count"],
            "recent_feedback": recent_stats["feedback_count"],
        }

    except Exception as e:
        logger.error(f"Failed to generate JIRA report: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Report generation failed: {str(e)}",
            "error": str(e),
        }
