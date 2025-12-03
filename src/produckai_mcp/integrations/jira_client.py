"""JIRA API client wrapper for feedback integration."""

from typing import Any, Dict, List, Optional

from jira import JIRA
from jira.exceptions import JIRAError

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class JiraClient:
    """Wrapper for JIRA API operations."""

    def __init__(
        self,
        server_url: str,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ):
        """
        Initialize JIRA client.

        Args:
            server_url: JIRA instance URL (e.g., https://yourcompany.atlassian.net)
            email: User email for API token auth
            api_token: API token for authentication
            oauth_token: OAuth token (alternative to API token)
        """
        self.server_url = server_url.rstrip("/")

        # Initialize JIRA client
        if oauth_token:
            # OAuth authentication
            self.client = JIRA(server=self.server_url, token_auth=oauth_token)
            logger.info("Initialized JIRA client with OAuth")
        elif email and api_token:
            # API token authentication (recommended for Atlassian Cloud)
            self.client = JIRA(server=self.server_url, basic_auth=(email, api_token))
            logger.info(f"Initialized JIRA client for {email}")
        else:
            raise ValueError("Either oauth_token or (email + api_token) required")

    def test_connection(self) -> Dict[str, Any]:
        """
        Test JIRA connection and get server info.

        Returns:
            Dictionary with connection status and server info
        """
        try:
            server_info = self.client.server_info()
            user = self.client.current_user()

            return {
                "success": True,
                "server_url": self.server_url,
                "server_version": server_info.get("version"),
                "deployment_type": server_info.get("deploymentType"),
                "user": user,
            }
        except JIRAError as e:
            logger.error(f"JIRA connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": e.status_code if hasattr(e, "status_code") else None,
            }

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List accessible JIRA projects.

        Returns:
            List of project dictionaries with metadata
        """
        try:
            projects = self.client.projects()

            return [
                {
                    "id": project.id,
                    "key": project.key,
                    "name": project.name,
                    "project_type": project.projectTypeKey,
                    "lead": project.lead.displayName if hasattr(project, "lead") else None,
                    "url": f"{self.server_url}/browse/{project.key}",
                }
                for project in projects
            ]
        except JIRAError as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    def get_project_details(self, project_key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a project.

        Args:
            project_key: JIRA project key (e.g., 'PROJ')

        Returns:
            Project details including issue types, workflows, custom fields
        """
        try:
            project = self.client.project(project_key)

            # Get issue types for this project
            issue_types = [
                {"id": it.id, "name": it.name, "description": it.description}
                for it in project.issueTypes
            ]

            # Get project metadata
            meta = self.client.project_components(project_key)
            components = [{"id": c.id, "name": c.name} for c in meta]

            return {
                "id": project.id,
                "key": project.key,
                "name": project.name,
                "description": getattr(project, "description", ""),
                "lead": project.lead.displayName if hasattr(project, "lead") else None,
                "issue_types": issue_types,
                "components": components,
                "url": f"{self.server_url}/browse/{project.key}",
            }
        except JIRAError as e:
            logger.error(f"Failed to get project {project_key}: {e}")
            return None

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a JIRA issue.

        Args:
            project_key: JIRA project key
            summary: Issue title
            description: Issue description (supports JIRA markdown)
            issue_type: Issue type (Task, Story, Bug, Epic, etc.)
            priority: Priority name (Highest, High, Medium, Low, Lowest)
            labels: List of labels to add
            components: List of component names
            custom_fields: Dictionary of custom field values

        Returns:
            Created issue details
        """
        try:
            # Build issue fields
            fields = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }

            # Add optional fields
            if priority:
                fields["priority"] = {"name": priority}

            if labels:
                fields["labels"] = labels

            if components:
                fields["components"] = [{"name": c} for c in components]

            # Add custom fields
            if custom_fields:
                fields.update(custom_fields)

            # Create issue
            issue = self.client.create_issue(fields=fields)

            logger.info(f"Created JIRA issue: {issue.key}")

            return {
                "key": issue.key,
                "id": issue.id,
                "url": f"{self.server_url}/browse/{issue.key}",
                "summary": summary,
                "issue_type": issue_type,
                "status": issue.fields.status.name,
            }

        except JIRAError as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get JIRA issue details.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')

        Returns:
            Issue details
        """
        try:
            issue = self.client.issue(issue_key)

            return {
                "key": issue.key,
                "id": issue.id,
                "url": f"{self.server_url}/browse/{issue.key}",
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "issue_type": issue.fields.issuetype.name,
                "assignee": (
                    issue.fields.assignee.displayName if issue.fields.assignee else None
                ),
                "reporter": (
                    issue.fields.reporter.displayName if issue.fields.reporter else None
                ),
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "labels": issue.fields.labels,
                "components": [c.name for c in issue.fields.components],
            }

        except JIRAError as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return None

    def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update a JIRA issue.

        Args:
            issue_key: Issue key to update
            summary: New summary
            description: New description
            priority: New priority
            labels: New labels (replaces existing)
            custom_fields: Custom field updates

        Returns:
            True if successful, False otherwise
        """
        try:
            issue = self.client.issue(issue_key)

            # Build update fields
            fields = {}
            if summary:
                fields["summary"] = summary
            if description:
                fields["description"] = description
            if priority:
                fields["priority"] = {"name": priority}
            if labels is not None:
                fields["labels"] = labels
            if custom_fields:
                fields.update(custom_fields)

            if fields:
                issue.update(fields=fields)
                logger.info(f"Updated JIRA issue: {issue_key}")
                return True

            return False

        except JIRAError as e:
            logger.error(f"Failed to update issue {issue_key}: {e}")
            return False

    def add_comment(self, issue_key: str, comment: str) -> bool:
        """
        Add a comment to a JIRA issue.

        Args:
            issue_key: Issue key
            comment: Comment text (supports JIRA markdown)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.add_comment(issue_key, comment)
            logger.info(f"Added comment to {issue_key}")
            return True
        except JIRAError as e:
            logger.error(f"Failed to add comment to {issue_key}: {e}")
            return False

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get all comments for a JIRA issue.

        Args:
            issue_key: Issue key

        Returns:
            List of comments
        """
        try:
            issue = self.client.issue(issue_key, expand="comments")
            comments = issue.fields.comment.comments

            return [
                {
                    "id": comment.id,
                    "author": comment.author.displayName,
                    "body": comment.body,
                    "created": str(comment.created),
                    "updated": str(comment.updated),
                }
                for comment in comments
            ]

        except JIRAError as e:
            logger.error(f"Failed to get comments for {issue_key}: {e}")
            return []

    def link_issues(self, inward_issue: str, outward_issue: str, link_type: str = "Relates") -> bool:
        """
        Create a link between two JIRA issues.

        Args:
            inward_issue: First issue key
            outward_issue: Second issue key
            link_type: Link type (Relates, Blocks, Duplicates, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.create_issue_link(
                type=link_type,
                inwardIssue=inward_issue,
                outwardIssue=outward_issue,
            )
            logger.info(f"Linked {inward_issue} to {outward_issue} ({link_type})")
            return True
        except JIRAError as e:
            logger.error(f"Failed to link issues: {e}")
            return False

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results
            fields: List of fields to return (None = all)

        Returns:
            List of matching issues
        """
        try:
            issues = self.client.search_issues(
                jql_str=jql,
                maxResults=max_results,
                fields=fields or "*all",
            )

            return [
                {
                    "key": issue.key,
                    "id": issue.id,
                    "url": f"{self.server_url}/browse/{issue.key}",
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "issue_type": issue.fields.issuetype.name,
                    "created": str(issue.fields.created),
                    "updated": str(issue.fields.updated),
                }
                for issue in issues
            ]

        except JIRAError as e:
            logger.error(f"Failed to search issues: {e}")
            return []

    def get_issue_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key

        Returns:
            List of available transitions
        """
        try:
            transitions = self.client.transitions(issue_key)

            return [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "to_status": t["to"]["name"],
                }
                for t in transitions
            ]

        except JIRAError as e:
            logger.error(f"Failed to get transitions for {issue_key}: {e}")
            return []

    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """
        Transition an issue to a new status.

        Args:
            issue_key: Issue key
            transition_name: Name of the transition (e.g., 'Done', 'In Progress')

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.transition_issue(issue_key, transition_name)
            logger.info(f"Transitioned {issue_key} to {transition_name}")
            return True
        except JIRAError as e:
            logger.error(f"Failed to transition {issue_key}: {e}")
            return False

    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Get all custom fields available in JIRA instance.

        Returns:
            List of custom field definitions
        """
        try:
            fields = self.client.fields()

            # Filter to custom fields only
            custom_fields = [f for f in fields if f["custom"]]

            return [
                {
                    "id": field["id"],
                    "name": field["name"],
                    "type": field["schema"]["type"],
                    "custom_type": field["schema"].get("custom"),
                }
                for field in custom_fields
            ]

        except JIRAError as e:
            logger.error(f"Failed to get custom fields: {e}")
            return []
