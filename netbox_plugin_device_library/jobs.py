"""Background jobs for the Device Library plugin."""

import tarfile
from collections import defaultdict
from pathlib import PurePosixPath
from urllib.parse import quote, urlparse

from core.events import JOB_STARTED
from django.db import transaction
from extras.models import Notification
import requests
import yaml
from netbox.jobs import JobRunner


class DeviceLibrarySyncJob(JobRunner):
    """Retrieve the configured device-library repositories for synchronization."""

    class Meta:
        name = "Synchronize device library source"

    def run(self, **kwargs):
        """Notify the initiating user, then synchronize configured repositories."""
        notification = self._create_started_notification()
        try:
            self._sync_libraries()
        finally:
            # NetBox creates the terminal job notification immediately after
            # this method returns. Remove the start notification first because
            # a user may have only one notification per job.
            if notification:
                notification.delete()

    def _sync_libraries(self):
        """Retrieve and persist the configured device-library repositories."""
        from .models import LibrarySource

        tarball_urls = {}
        processing_results = {}
        for repository in LibrarySource.objects.order_by("repository").values_list("repository", flat=True):
            try:
                repository_details = self._get_repository_details(repository)
                tarball_urls[repository] = repository_details["tarball_url"]
                processing_results[repository] = self._process_tarball(repository_details)
            except (
                KeyError,
                ValueError,
                requests.RequestException,
                tarfile.TarError,
                yaml.YAMLError,
            ) as error:
                self.logger.error("Failed to resolve %s: %s", repository, error)
                # An unhandled exception marks the job errored. NetBox then sends
                # its standard failure notification to the user who started it.
                raise

            self.logger.info("Processed tarball for %s", repository)

        saved_counts = self._save_imported_objects(processing_results)
        self.job.data = {
            "tarball_urls": tarball_urls,
            "processing_results": processing_results,
            "saved_counts": saved_counts,
        }
        self.job.save(update_fields=["data"])

        self.logger.info("Processed %d device type repositories", len(processing_results))

    def _create_started_notification(self):
        """Create NetBox's standard Job started notification for the job owner."""
        if not self.job.user:
            return None

        return Notification.objects.create(
            user=self.job.user,
            object=self.job,
            event_type=JOB_STARTED,
        )

    @staticmethod
    def _save_imported_objects(processing_results: dict):
        """Upsert parsed library objects in PostgreSQL batches."""
        from .models import DeviceType, ModuleType, RackType

        models_by_type = {
            "device": DeviceType,
            "module": ModuleType,
            "rack": RackType,
        }
        objects_by_type = defaultdict(list)
        for repository_result in processing_results.values():
            for item in repository_result["yaml_files"]:
                model = models_by_type[item["object_type"]]
                objects_by_type[item["object_type"]].append(
                    model(
                        manufacturer_name=item["manufacturer"] or "",
                        name=item["model"] or "",
                        part_number=item["part_number"] or "",
                        github_api_url=item["github_api_url"],
                    )
                )

        with transaction.atomic():
            for object_type, objects in objects_by_type.items():
                models_by_type[object_type].objects.bulk_create(
                    objects,
                    batch_size=500,
                    update_conflicts=True,
                    update_fields=["manufacturer_name", "name", "part_number"],
                    unique_fields=["github_api_url"],
                )

        return {object_type: len(objects) for object_type, objects in objects_by_type.items()}

    def _get_repository_details(self, repository: str):
        """Resolve GitHub details needed to process a repository's default branch."""
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
        return {
            "owner": owner,
            "name": name,
            "default_branch": default_branch,
            "tarball_url": tarball_response.headers["Location"],
        }

    def _process_tarball(self, repository_details: dict):
        """Parse regular YAML files in a GitHub tarball without writing to disk."""
        yaml_files = []

        with requests.get(
            repository_details["tarball_url"],
            stream=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            response.raw.decode_content = True
            with tarfile.open(fileobj=response.raw, mode="r|gz") as archive:
                for member in archive:
                    object_type, repository_path = self._get_yaml_details(member.name)
                    if (
                        not member.isfile()
                        or not member.name.endswith(".yaml")
                        or object_type is None
                    ):
                        continue

                    file_object = archive.extractfile(member)
                    if file_object is None:
                        continue

                    with file_object:
                        document = yaml.safe_load(file_object)

                    if not isinstance(document, dict):
                        continue

                    yaml_files.append(
                        {
                            "object_type": object_type,
                            "manufacturer": document.get("manufacturer"),
                            "model": document.get("model"),
                            "part_number": document.get("part_number"),
                            "github_api_url": self._get_github_content_url(
                                repository_details["owner"],
                                repository_details["name"],
                                repository_path,
                                repository_details["default_branch"],
                            ),
                        }
                    )

        return {"yaml_files": yaml_files}

    @staticmethod
    def _get_yaml_details(member_name: str):
        """Return a YAML member's type and path relative to the Git repository."""
        directory_types = {
            "device-types": "device",
            "module-types": "module",
            "rack-types": "rack",
        }
        path_parts = PurePosixPath(member_name).parts
        for index, path_part in enumerate(path_parts):
            if path_part in directory_types:
                return directory_types[path_part], "/".join(path_parts[index:])

        return None, None

    @staticmethod
    def _get_github_content_url(owner: str, name: str, path: str, ref: str):
        """Build the GitHub Contents API request URL for one YAML file."""
        encoded_path = quote(path, safe="/")
        encoded_ref = quote(ref, safe="")
        return f"https://api.github.com/repos/{owner}/{name}/contents/{encoded_path}?ref={encoded_ref}"

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
