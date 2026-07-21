"""Background jobs for the Device Library plugin."""

from time import sleep

from netbox.jobs import JobRunner


class DeviceLibrarySyncJob(JobRunner):
    """Run a synchronization for one configured device-library source."""

    class Meta:
        name = "Synchronize device library source"

    def run(self, *, source_id: int, **kwargs):
        """Perform the source synchronization.

        The actual device-library fetch and import workflow will live here. Keeping
        it in a JobRunner means callers can enqueue the work without blocking a
        request, and NetBox records the result and log output on the Job model.
        """
        from .models import LibrarySource

        source = LibrarySource.objects.get(pk=source_id)
        self.logger.info("Starting synchronization for %s", source.repository)

        # TODO: Fetch and import the device-library definitions for ``source``.
        sleep(5)

        self.logger.info("Synchronization completed for %s", source.repository)
