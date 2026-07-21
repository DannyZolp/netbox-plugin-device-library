"""Background jobs for the Device Library plugin."""

from urllib.parse import urlparse

import requests
from netbox.jobs import JobRunner


class DeviceLibrarySyncJob(JobRunner):
    """Retrieve the configured device-library repositories for synchronization."""

    class Meta:
        name = "Synchronize device library source"

    def run(self, **kwargs):
        """Retrieve the configured device-library repositories."""
        from .models import LibrarySource

        tarball_urls = {}
        for repository in LibrarySource.objects.order_by("repository").values_list("repository", flat=True):
            try:
                tarball_urls[repository] = self._get_tarball_url(repository)
            except (KeyError, ValueError, requests.RequestException) as error:
                self.logger.error("Failed to resolve %s: %s", repository, error)
                # An unhandled exception marks the job errored. NetBox then sends
                # its standard failure notification to the user who started it.
                raise

            self.logger.info("Retrieved tarball URL for %s", repository)

        self.job.data = {"tarball_urls": tarball_urls}
        self.job.save(update_fields=["data"])

        self.logger.info("Retrieved tarball URLs for %d device type repositories", len(tarball_urls))

    def _get_tarball_url(self, repository: str):
        """Resolve the default branch's tarball redirect URL through GitHub's API."""
        owner, name = self._get_github_repository_name(repository)
        repository_data = requests.get(
            f"https://api.github.com/repos/{owner}/{name}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        repository_data.raise_for_status()

        default_branch = repository_data.json()["default_branch"]
        tarball_response = requests.get(
            f"https://api.github.com/repos/{owner}/{name}/tarball/{default_branch}",
            headers={"Accept": "application/vnd.github+json"},
            allow_redirects=False,
            timeout=30,
        )
        tarball_response.raise_for_status()
        return tarball_response.headers["Location"]

    @staticmethod
    def _get_github_repository_name(repository: str):
        """Return the GitHub owner and repository name from a repository URL."""
        parsed_url = urlparse(repository)
        if parsed_url.hostname not in {"github.com", "www.github.com"}:
            raise ValueError(f"Unsupported GitHub repository URL: {repository}")

        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) != 2:
            raise ValueError(f"Unsupported GitHub repository URL: {repository}")

        owner, name = path_parts
        return owner, name.removesuffix(".git")
