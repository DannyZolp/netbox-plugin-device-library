"""Background jobs for the Device Library plugin."""

import tarfile
from collections import defaultdict
from pathlib import PurePosixPath
from time import monotonic
from urllib.parse import quote, unquote, urlparse

from core.events import JOB_STARTED
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from extras.models import Notification
import requests
import yaml
from netbox.jobs import JobRunner

IMAGE_EXTENSIONS = {"bmp", "gif", "jpg", "png", "tiff", "webp"}


class DeviceLibrarySyncJob(JobRunner):
    """Retrieve the configured device-library repositories for synchronization."""

    class Meta:
        name = "Synchronize device library source"
        job_timeout = 60 * 60

    @classmethod
    def enqueue(cls, *args, **kwargs):
        """Queue the job with enough time to process large library archives."""
        kwargs.setdefault("job_timeout", cls.Meta.job_timeout)
        return super().enqueue(*args, **kwargs)

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
                self.logger.info(f"Downloading device-library repository {repository}")
                repository_details = self._get_repository_details(repository)
                tarball_urls[repository] = repository_details["tarball_url"]
                processing_results[repository] = self._process_tarball(repository, repository_details)
            except (
                KeyError,
                ValueError,
                requests.RequestException,
                tarfile.TarError,
                yaml.YAMLError,
            ) as error:
                self.logger.error(f"Failed to resolve {repository}: {error}")
                # An unhandled exception marks the job errored. NetBox then sends
                # its standard failure notification to the user who started it.
                raise

            self.logger.info(f"Processed tarball for {repository}")

        saved_counts = self._save_imported_objects(processing_results)
        saved_counts["images"] = self._save_images(processing_results)
        self.job.data = {
            "tarball_urls": tarball_urls,
            "processing_results": processing_results,
            "saved_counts": saved_counts,
        }
        self.job.save(update_fields=["data"])

        self.logger.info(f"Processed {len(processing_results)} device type repositories")

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

    @staticmethod
    def _save_images(processing_results: dict):
        """Upsert image metadata discovered while streaming library tarballs."""
        from .models import Image

        images = [
            Image(slug=image["slug"], face=image["face"], uri=image["uri"])
            for repository_result in processing_results.values()
            for image in repository_result["images"]
        ]
        if images:
            Image.objects.bulk_create(
                images,
                batch_size=500,
                update_conflicts=True,
                update_fields=["slug", "face"],
                unique_fields=["uri"],
            )

        return len(images)

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

    def _process_tarball(self, repository: str, repository_details: dict):
        """Parse YAML files and collect image metadata from a GitHub tarball."""
        yaml_files = []
        images = []
        last_progress_log = monotonic()

        with requests.get(
            repository_details["tarball_url"],
            stream=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            response.raw.decode_content = True
            with tarfile.open(fileobj=response.raw, mode="r|gz") as archive:
                for member in archive:
                    if not member.isfile():
                        continue

                    image = self._get_image_details(member.name, repository_details)
                    if image:
                        images.append(image)
                        continue

                    object_type, repository_path = self._get_yaml_details(member.name)
                    if not member.name.endswith(".yaml") or object_type is None:
                        continue

                    file_object = archive.extractfile(member)
                    if file_object is None:
                        continue

                    with file_object:
                        document = yaml.safe_load(file_object)

                    if isinstance(document, dict):
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

                    now = monotonic()
                    if now - last_progress_log >= 10:
                        self.logger.info(
                            f"Found {len(yaml_files)} library objects in {repository}"
                        )
                        last_progress_log = now

        return {"yaml_files": yaml_files, "images": images}

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
    def _get_image_details(member_name: str, repository_details: dict):
        """Return image metadata derived from a device-library archive member."""
        filename_parts = PurePosixPath(member_name).name.rsplit(".", 2)
        if len(filename_parts) != 3:
            return None

        slug, face, extension = filename_parts
        if not slug or not face or extension.lower() not in IMAGE_EXTENSIONS:
            return None

        repository_path = DeviceLibrarySyncJob._get_repository_path(member_name)
        if repository_path is None:
            return None

        return {
            "slug": slug,
            "face": face,
            "uri": DeviceLibrarySyncJob._get_github_content_url(
                repository_details["owner"],
                repository_details["name"],
                repository_path,
                repository_details["default_branch"],
            ),
        }

    @staticmethod
    def _get_repository_path(member_name: str):
        """Strip the tarball's generated root directory from a repository path."""
        repository_directories = {
            "device-types",
            "module-types",
            "rack-types",
            "elevation-images",
        }
        path_parts = PurePosixPath(member_name).parts
        for index, path_part in enumerate(path_parts):
            if path_part in repository_directories:
                return "/".join(path_parts[index:])

        return None

    @staticmethod
    def _get_github_content_url(owner: str, name: str, path: str, ref: str):
        """Build the GitHub Contents API request URL for one repository file."""
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


class LibraryObjectImportJob(JobRunner):
    """Receive one selected library record for the next import stage."""

    class Meta:
        name = "Import device library object"

    def run(self, *, record: dict, **kwargs):
        """Download, parse, and import one selected device-library object."""
        response = requests.get(
            record["github_api_url"],
            headers={"Accept": "application/vnd.github.raw+json"},
            timeout=30,
        )
        response.raise_for_status()
        document = yaml.safe_load(response.content)
        if not isinstance(document, dict):
            raise ValueError("The GitHub YAML document must contain a mapping.")

        image_urls = {}
        if document.get("front_image") is True:
            image_urls["front"] = self._get_image_uri(document, "front")

        if document.get("rear_image") is True:
            image_urls["rear"] = self._get_image_uri(document, "rear")

        imported_object, created = self._import_netbox_object(record["object_type"], document)
        images = {
            face: self._set_object_image(imported_object, face, uri)
            for face, uri in image_urls.items()
        }
        self.job.data = {
            "record": record,
            "imported_object": {
                "type": record["object_type"],
                "id": imported_object.pk,
                "created": created,
            },
            "image_urls": image_urls,
            "images": images,
        }
        self.job.save(update_fields=["data"])
        self.logger.info(
            f"Imported {record['object_type']} {document['manufacturer']} {document['model']}"
        )

    def _set_object_image(self, imported_object, face: str, uri: str):
        """Download a library image into the matching NetBox image field."""
        field_name = f"{face}_image"
        if not hasattr(imported_object, field_name):
            self.logger.warning(
                f"{imported_object._meta.verbose_name} does not support {field_name}; skipping image upload"
            )
            return None

        response = requests.get(
            uri,
            headers={"Accept": "application/vnd.github.raw+json"},
            timeout=30,
        )
        response.raise_for_status()

        filename = unquote(urlparse(uri).path.rsplit("/", 1)[-1])
        setattr(imported_object, field_name, ContentFile(response.content, name=filename))
        imported_object.save(update_fields=[field_name])

        self.logger.info(f"Uploaded {face} image for {imported_object}")
        return {"field": field_name, "uri": uri}

    def _get_image_uri(self, document: dict, face: str):
        """Look up an imported image by the YAML object's slug and face."""
        from .models import Image

        slug = document.get("slug")
        if not slug:
            raise ValueError(f"Cannot resolve a {face} image without a YAML slug.")

        image = Image.objects.get(slug=slug, face=face)
        self.logger.info(f"Resolved {face} image for {slug}")
        return image.uri

    @staticmethod
    def _import_netbox_object(object_type: str, document: dict):
        """Create or update the matching NetBox DCIM type through its ORM API."""
        from dcim.models import DeviceType, Manufacturer, ModuleType, RackType

        if object_type not in {"device", "module", "rack"}:
            raise ValueError(f"Unsupported library object type: {object_type}")

        with transaction.atomic():
            manufacturer_name = document["manufacturer"]
            manufacturer, _ = Manufacturer.objects.get_or_create(
                name=manufacturer_name,
                defaults={"slug": manufacturer_name.lower().replace(" ", "-")},
            )
            model = document["model"]
            part_number = document.get("part_number", "")

            if object_type == "device":
                return DeviceType.objects.update_or_create(
                    manufacturer=manufacturer,
                    model=model,
                    defaults={
                        "slug": document.get("slug") or slugify(model),
                        "part_number": part_number,
                    },
                )

            if object_type == "module":
                return ModuleType.objects.update_or_create(
                    manufacturer=manufacturer,
                    model=model,
                    defaults={"part_number": part_number},
                )

            if object_type == "rack":
                return RackType.objects.update_or_create(
                    manufacturer=manufacturer,
                    model=model,
                    defaults={
                        "slug": document.get("slug") or slugify(model),
                        "form_factor": document["form_factor"],
                    },
                )
