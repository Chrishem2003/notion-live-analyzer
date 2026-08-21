
"""
Native Git/Repository Integration  connects to GitHub repositories,
enables data version control, script pushing, and collaborative analysis.
"""
from typing import Dict, List, Any, Optional, Tuple
import os
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Graceful Imports Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
try:
    import git
    HAS_GITPYTHON = True
except ImportError:
    HAS_GITPYTHON = False
    git = None

try:
    from github import Github, GithubIntegration
    HAS_PYGITHUB = True
except ImportError:
    HAS_PYGITHUB = False
    Github = None


class GitIntegration:
    """
    Full GitHub integration for data science workflows:
    - Connect to GitHub repos
    - Pull raw datasets
    - Commit & push cleaned data / analysis scripts
    - Track version history of data cleaning steps
    """

    def __init__(self):
        self.repo = None
        self.github_client = None
        self.local_path = None
        self.connected = False

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Connection Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def connect_github(self, token: str, repo_url: str) -> Tuple[bool, str]:
        """Connect to a GitHub repository using a personal access token."""
        if not HAS_PYGITHUB:
            return False, "PyGithub is not installed. Run: pip install PyGithub"
        if not HAS_GITPYTHON:
            return False, "GitPython is not installed. Run: pip install GitPython"

        try:
            # Authenticate with GitHub
            self.github_client = Github(token)

            # Parse repo URL
            # Supports: https://github.com/owner/repo.git, https://github.com/owner/repo
            repo_name = repo_url.rstrip(".git")
            if "github.com/" in repo_name:
                repo_name = repo_name.split("github.com/")[-1]
            elif "github.com:" in repo_name:
                repo_name = repo_name.split("github.com:")[-1]

            # Get the repo
            try:
                self.repo = self.github_client.get_repo(repo_name)
            except Exception:
                return False, f"Ã¢ÂÅ’ Repository '{repo_name}}' not found. Check the URL and your access token."

            # Create local temp directory for cloning
            self.local_path = tempfile.mkdtemp(prefix="chrishem_git_")

            # Clone the repo
            clone_url = f"https://x-access-token:{token}}@github.com/{repo_name}}.git"
            try:
                git.Repo.clone_from(clone_url, self.local_path)
                self.local_repo = git.Repo(self.local_path)
            except Exception as e:
                return False, f"Ã¢ÂÅ’ Failed to clone repository: {str(e)}}"

            self.connected = True
            return True, f"âœ… Connected to {repo_name}}"

        except Exception as e:
            return False, f"Ã¢ÂÅ’ Connection failed: {str(e)}}"

    def disconnect(self):
        """Disconnect from GitHub and clean up."""
        self.repo = None
        self.github_client = None
        self.local_repo = None
        self.connected = False
        if self.local_path and os.path.exists(self.local_path):
            import shutil
            shutil.rmtree(self.local_path, ignore_errors=True)
            self.local_path = None

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Repository Operations Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def list_repo_files(self, path: str = "") -> List[Dict[str, Any]]:
        """List files in the repository at a given path."""
        if not self.connected or not self.repo:
            return []

        try:
            contents = self.repo.get_contents(path)
            files = []
            for content in contents:
                files.append({
                    "name": content.name,
                    "path": content.path,
                    "type": content.type,  # "file" or "dir"
                    "size": content.size,
                    "download_url": content.download_url,
                })
            return files
        except Exception as e:
            st.warning(f"Failed to list files: {str(e)}}")
            return []

    def pull_dataset(self, file_path: str) -> Optional[pd.DataFrame]:
        """Pull a CSV/Excel/JSON dataset from the repository and load as DataFrame."""
        if not self.connected or not self.repo:
            st.error("Not connected to any GitHub repository.")
            return None

        try:
            content = self.repo.get_contents(file_path)
            file_ext = Path(file_path).suffix.lower()

            # Download to temp file
            import requests
            response = requests.get(content.download_url)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            # Parse based on extension
            try:
                if file_ext == ".csv":
                    df = pd.read_csv(tmp_path)
                elif file_ext in (".xlsx", ".xls"):
                    df = pd.read_excel(tmp_path)
                elif file_ext == ".json":
                    df = pd.read_json(tmp_path)
                elif file_ext == ".parquet":
                    df = pd.read_parquet(tmp_path)
                elif file_ext == ".feather":
                    df = pd.read_feather(tmp_path)
                elif file_ext == ".pkl":
                    df = pd.read_pickle(tmp_path)
                else:
                    st.warning(f"Unsupported file format: {file_ext}}")
                    os.unlink(tmp_path)
                    return None

                os.unlink(tmp_path)
                return df

            except Exception as e:
                os.unlink(tmp_path)
                st.error(f"Failed to parse dataset: {str(e)}}")
                return None

        except Exception as e:
            st.error(f"Failed to pull dataset: {str(e)}}")
            return None

    def commit_and_push(self, file_path: str, message: str, branch: str = "main") -> Tuple[bool, str]:
        """
        Commit a file change and push to GitHub.
        file_path: local path to file to commit
        message: commit message
        branch: target branch
        """
        if not self.connected or not self.local_repo:
            return False, "Not connected to a repository"

        try:
            # Copy file to local repo
            dest_path = os.path.join(self.local_path, os.path.basename(file_path))
            import shutil
            shutil.copy2(file_path, dest_path)

            # Git operations
            self.local_repo.index.add([os.path.basename(file_path)])
            self.local_repo.index.commit(message)

            # Push
            origin = self.local_repo.remotes.origin
            origin.push(refspec=f"HEAD:refs/heads/{branch}}")

            return True, f"âœ… Committed and pushed to {branch}}"

        except Exception as e:
            return False, f"Ã¢ÂÅ’ Commit/push failed: {str(e)}}"

    def push_analysis_script(self, df: pd.DataFrame, analysis_type: str,
                              branch: str = "main") -> Tuple[bool, str]:
        """Auto-generate a Python analysis script and push to GitHub."""
        if not self.connected:
            return False, "Not connected to a repository"

        try:
            # Generate script content
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            script_content = self._generate_analysis_script(df, analysis_type)
            script_name = f"analysis_{analysis_type}}_{timestamp}}.py"

            # Write to temp file
            script_path = os.path.join(tempfile.gettempdir(), script_name)
            with open(script_path, "w") as f:
                f.write(script_content)

            # Commit and push
            return self.commit_and_push(script_path, f"Auto-generated {analysis_type}} analysis ({timestamp}})", branch)

        except Exception as e:
            return False, f"Ã¢ÂÅ’ Script generation failed: {str(e)}}"

    def push_cleaned_dataset(self, df: pd.DataFrame, dataset_name: str = None,
                              format: str = "csv", branch: str = "main") -> Tuple[bool, str]:
        """Export cleaned dataset and push to GitHub."""
        if not self.connected:
            return False, "Not connected to a repository"

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = dataset_name or f"cleaned_data_{timestamp}}"
            file_name = f"{name}}.{format}}"
            file_path = os.path.join(tempfile.gettempdir(), file_name)

            # Export
            if format == "csv":
                df.to_csv(file_path, index=False)
            elif format == "xlsx":
                df.to_excel(file_path, index=False)
            elif format == "json":
                df.to_json(file_path, orient="records", indent=2)
            else:
                return False, f"Unsupported format: {format}}"

            # Commit to data/ directory
            dest_in_repo = f"data/{file_name}}"
            dest_local = os.path.join(self.local_path, "data")
            os.makedirs(dest_local, exist_ok=True)
            import shutil
            shutil.copy2(file_path, os.path.join(dest_local, file_name))

            self.local_repo.index.add([f"data/{file_name}}"])
            self.local_repo.index.commit(f"Add cleaned dataset: {file_name}}")
            origin = self.local_repo.remotes.origin
            origin.push(refspec=f"HEAD:refs/heads/{branch}}")

            return True, f"âœ… Pushed {file_name}} to {branch}}"

        except Exception as e:
            return False, f"Ã¢ÂÅ’ Failed to push dataset: {str(e)}}"

    def list_commits(self, path: str = None, max_count: int = 20) -> List[Dict[str, Any]]:
        """List commit history for the repo, optionally filtered by file path."""
        if not self.connected or not self.repo:
            return []

        try:
            commits = []
            for commit in self.repo.get_commits(path=path)[:max_count]:
                commits.append({
                    "sha": commit.sha[:8],
                    "message": commit.commit.message.strip(),
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.strftime("%Y-%m-%d %H:%M"),
                    "url": commit.html_url,
                })
            return commits
        except Exception as e:
            st.warning(f"Failed to list commits: {str(e)}}")
            return []

    def _generate_analysis_script(self, df: pd.DataFrame, analysis_type: str) -> str:
        """Generate a Python analysis script based on the analysis type."""
        cols = df.columns.tolist()
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        scripts = {
            "descriptive": f'''"""
Auto-generated Descriptive Analysis Script
Generated by CHRISHEM Executive Analysis Engine
"""
import pandas as pd
import numpy as np

# Load data
# df = pd.read_csv("your_data.csv")

df = None  # Replace with your data loading

cols = {cols}
numeric_cols = {numeric_cols}

# Descriptive statistics
desc = df[numeric_cols].describe().round(4)
print(desc)

# Save results
desc.to_csv("descriptive_statistics.csv")
print("âœ… Descriptive analysis complete.")
''',
            "correlation": f'''"""
Auto-generated Correlation Analysis Script
"""
import pandas as pd
import numpy as np

numeric_cols = {numeric_cols}

corr_matrix = df[numeric_cols].corr(method="pearson").round(4)
print("Correlation Matrix:")
print(corr_matrix)

# Find strong correlations
strong = []
for i in range(len(numeric_cols)):
    for j in range(i1, len(numeric_cols)):
        r = corr_matrix.iloc[i, j]
        if abs(r) > 0.5:
            strong.append({{"var1": numeric_cols[i], "var2": numeric_cols[j], "r": r}})

print(f"\\nFound {{len(strong)}} strong correlations (|r| > 0.5)")
corr_matrix.to_csv("correlation_matrix.csv")
''',
            "regression": f'''"""
Auto-generated Regression Analysis Script
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error

target = "{numeric_cols[0] if numeric_cols else 'target'}"
features = {numeric_cols[1:5] if len(numeric_cols) > 1 else []}

if features:
    X = df[features].dropna()
    y = df[target].dropna()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(f"RÃ‚Â² = {{r2_score(y_test, y_pred):.4f}}")
    print(f"RMSE = {{np.sqrt(mean_squared_error(y_test, y_pred)):.4f}}")
''',
        }

        return scripts.get(analysis_type, f'''"""
Auto-generated Data Analysis Script
"""
import pandas as pd
import numpy as np

print("Analysis script generated by CHRISHEM")
print(f"Dataset shape: {df.shape}}")
print(f"Columns: {cols}}")
''')

    @property
    def status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "connected": self.connected,
            "repo": self.repo.full_name if self.repo and self.connected else None,
            "local_path": self.local_path,
        }


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ UI Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def render_git_integration_ui():
    """Render the Git integration UI."""
    st.markdown("## Ã°Å¸â€â€” Git Repository Integration")
    st.markdown("*Connect your GitHub repository for data version control, script pushing, and collaboration*")

    if "git_engine" not in st.session_state:
        st.session_state["git_engine"] = GitIntegration()

    engine = st.session_state["git_engine"]

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Connection Panel Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    if not engine.connected:
        st.markdown("### Ã°Å¸â€Å’ Connect to GitHub")

        with st.form("git_connect_form"):
            repo_url = st.text_input(
                "Repository URL",
                placeholder="https://github.com/username/repository",
                help="Full URL to your GitHub repository",
            )
            github_token = st.text_input(
                "GitHub Personal Access Token",
                type="password",
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
                help="Create at: GitHub Settings Ã¢â€ â€™ Developer Settings Ã¢â€ â€™ Personal Access Tokens Ã¢â€ â€™ Fine-grained tokens",
            )

            col1, col2 = st.columns(2)
            with col1:
                default_branch = st.text_input("Default branch", value="main")
            with col2:
                st.markdown("##### ")
                st.markdown("Ã°Å¸â€â€™ Token stored in session only")

            submitted = st.form_submit_button("Ã°Å¸â€â€” Connect to GitHub", type="primary", use_container_width=True)

            if submitted:
                if not repo_url or not github_token:
                    st.error("Please provide both Repository URL and Access Token")
                else:
                    with st.spinner("Connecting to GitHub..."):
                        success, message = engine.connect_github(github_token, repo_url)
                    if success:
                        st.success(message)
                        st.session_state["git_connected"] = True
                        st.session_state["git_repo_url"] = repo_url
                        st.session_state["git_token"] = github_token
                        st.session_state["git_branch"] = default_branch
                        st.rerun()
                    else:
                        st.error(message)

        st.markdown("""
        ---
        ### Ã°Å¸â€â€˜ How to Get a GitHub Token
        1. Go to [GitHub Settings Ã¢â€ â€™ Developer Settings](https://github.com/settings/tokens)
        2. Click **Generate new token (fine-grained)**
        3. Select repo access: **Contents** (read/write), **Commits** (read)
        4. Copy the token and paste it above
        """)
        return

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Connected View Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    status = engine.status
    st.success(f"âœ… Connected to **{status.get('repo', 'Unknown')}}**")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Ã°Å¸â€â€ž Refresh Connection", use_container_width=True):
            st.rerun()
    with col2:
        branch = st.text_input("Branch", value=st.session_state.get("git_branch", "main"), key="git_branch_input")
        st.session_state["git_branch"] = branch
    with col3:
        if st.button("Ã°Å¸â€Å’ Disconnect", use_container_width=True, type="secondary"):
            engine.disconnect()
            st.session_state["git_connected"] = False
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Ã°Å¸â€œâ€š Browse Repo", "ðŸ“¥ Pull Dataset", "Ã°Å¸â€œÂ¤ Push Data/Scripts", "ðŸ“‹ Commit History"
    ])

    with tab1:
        st.subheader("Ã°Å¸â€œâ€š Repository Files")
        repo_path = st.text_input("Path (leave empty for root)", value="", key="repo_path")
        files = engine.list_repo_files(repo_path)

        if files:
            for f in files:
                icon = "Ã°Å¸â€œÂ" if f["type"] == "dir" else "Ã°Å¸â€œâ€ž"
                size_str = f" ({f['size'] / 1024:.1f}} KB)" if f["type"] == "file" else ""
                st.markdown(f"{icon}} **{f['name']}}**{size_str}}  `{f['path']}}`")
        else:
            st.info("No files found at this path")

    with tab2:
        st.subheader("ðŸ“¥ Pull Dataset from Repository")
        st.caption("Load a CSV, Excel, or JSON file directly from GitHub into the analyzer.")

        if files:
            data_files = [f for f in files if f["type"] == "file" and f["name"].endswith((".csv", ".xlsx", ".xls", ".json", ".parquet"))]
            if data_files:
                file_to_pull = st.selectbox(
                    "Select a dataset to pull",
                    options=data_files,
                    format_func=lambda f: f["name"],
                )

                if st.button("ðŸ“¥ Pull & Load Dataset", type="primary", use_container_width=True):
                    with st.spinner(f"Pulling {file_to_pull['name']}}..."):
                        pulled_df = engine.pull_dataset(file_to_pull["path"])
                    if pulled_df is not None:
                        st.session_state["uploaded_df"] = pulled_df
                        st.session_state["active_df"] = pulled_df
                        st.session_state["data_source"] = "github"
                        st.success(f"âœ… Loaded '{file_to_pull['name']}}'  {len(pulled_df)}} rows Ãƒâ€” {len(pulled_df.columns)}} columns")
                        st.dataframe(pulled_df.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("No supported data files found in the current directory. Navigate to a different path.")
        else:
            st.info("Browse to a directory containing data files first.")

    with tab3:
        st.subheader("Ã°Å¸â€œÂ¤ Push Data & Scripts to GitHub")
        st.caption("Version-control your cleaned datasets and analysis scripts.")

        active_df = st.session_state.get("active_df")
        if active_df is not None and not active_df.empty:
            st.info(f" Current active dataset: {len(active_df)}} rows Ãƒâ€” {len(active_df.columns)}} columns")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Ã°Å¸â€œÂ¤ Push Cleaned Dataset (CSV)", use_container_width=True):
                    with st.spinner("Pushing dataset to GitHub..."):
                        success, msg = engine.push_cleaned_dataset(
                            active_df, "cleaned_data", "csv",
                            st.session_state.get("git_branch", "main")
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            with col2:
                if st.button("Ã°Å¸â€œÂ¤ Push Analysis Script", use_container_width=True):
                    analysis_type = st.selectbox(
                        "Script type",
                        options=["descriptive", "correlation", "regression"],
                        key="script_type",
                        label_visibility="collapsed",
                    )
                    with st.spinner("Generating and pushing script..."):
                        success, msg = engine.push_analysis_script(
                            active_df, analysis_type,
                            st.session_state.get("git_branch", "main")
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.warning("No active dataset to push. Load data first.")

        # Dataset name
        dataset_name = st.text_input("Dataset filename (optional)", placeholder="my_cleaned_data")
        push_format = st.selectbox("Format", options=["csv", "xlsx", "json"])

        if st.button("Ã°Å¸â€œÂ¤ Push Named Dataset", use_container_width=True):
            if active_df is not None:
                with st.spinner("Pushing..."):
                    success, msg = engine.push_cleaned_dataset(
                        active_df, dataset_name or None, push_format,
                        st.session_state.get("git_branch", "main")
                    )
                st.success(msg) if success else st.error(msg)

    with tab4:
        st.subheader("ðŸ“‹ Commit History")
        st.caption("Track version history of data cleaning and analysis steps.")

        commits = engine.list_commits(max_count=30)
        if commits:
            for c in commits:
                st.markdown(f"""
                <div style="padding:0.5rem;margin:0.3rem 0;border-radius:8px;
                            border-left:3px solid #1d4ed8;background:rgba(0,0,0,0.02);">
                    <span style="font-weight:600;">{c['message'][:80]}</span><br>
                    <span style="font-size:0.8rem;color:#64748b;">
                        {c['sha']}  {c['author']}  {c['date']}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No commit history available.")


