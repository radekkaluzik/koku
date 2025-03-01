#
# Copyright 2021 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Report manifest database accessor for cost usage reports."""
import logging

from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import F
from django.db.models import Func
from django.db.models import Max
from django.db.models import Value
from django.db.models.expressions import Window
from django.db.models.functions import Cast
from django.db.models.functions import RowNumber
from tenant_schemas.utils import schema_context

from masu.database.koku_database_access import KokuDBAccess
from masu.external.date_accessor import DateAccessor
from reporting_common.models import CostUsageReportManifest
from reporting_common.models import CostUsageReportStatus

LOG = logging.getLogger(__name__)


class ReportManifestDBAccessor(KokuDBAccess):
    """Class to interact with the koku database for CUR processing statistics."""

    def __init__(self):
        """Access the AWS report manifest database table."""
        self._schema = "public"
        super().__init__(self._schema)
        self._table = CostUsageReportManifest
        self.date_accessor = DateAccessor()

    def get_manifest(self, assembly_id, provider_uuid):
        """Get the manifest associated with the provided provider and id."""
        query = self._get_db_obj_query()
        return query.filter(provider_id=provider_uuid).filter(assembly_id=assembly_id).first()

    def get_manifest_by_id(self, manifest_id):
        """Get the manifest by id."""
        with schema_context(self._schema):
            query = self._get_db_obj_query()
            return query.filter(id=manifest_id).first()

    def mark_manifest_as_updated(self, manifest):
        """Update the updated timestamp."""
        if manifest:
            updated_datetime = self.date_accessor.today_with_timezone("UTC")
            msg = (
                f"Marking manifest {manifest.id} "
                f"\nassembly_id {manifest.assembly_id} "
                f"\nfor provider {manifest.provider_id} "
                f"\nmanifest_updated_datetime: {updated_datetime}."
            )
            LOG.info(msg)
            manifest.manifest_updated_datetime = updated_datetime
            manifest.save()

    def mark_manifests_as_completed(self, manifest_list):
        """Update the updated timestamp."""
        completed_datetime = self.date_accessor.today_with_timezone("UTC")
        if manifest_list:
            bulk_manifest_query = self._get_db_obj_query().filter(id__in=manifest_list)
            for manifest in bulk_manifest_query:
                msg = (
                    f"Marking manifest {manifest.id} "
                    f"\nassembly_id {manifest.assembly_id} "
                    f"\nfor provider {manifest.provider_id} "
                    f"\nmanifest_completed_datetime: {completed_datetime}."
                )
                LOG.info(msg)
                manifest.manifest_completed_datetime = completed_datetime
                manifest.save()

    def update_number_of_files_for_manifest(self, manifest):
        """Update the number of files for manifest."""
        set_num_of_files = CostUsageReportStatus.objects.filter(manifest_id=manifest.id).count()
        if manifest:
            manifest.num_total_files = set_num_of_files
            manifest.save()

    def add(self, **kwargs):
        """
        Add a new row to the CUR stats database.

        Args:
            kwargs (dict): Fields containing CUR Manifest attributes.
                Valid keys are: assembly_id,
                                billing_period_start_datetime,
                                num_total_files,
                                provider_uuid,
        Returns:
            None

        """
        if "manifest_creation_datetime" not in kwargs:
            kwargs["manifest_creation_datetime"] = self.date_accessor.today_with_timezone("UTC")

        # The Django model insists on calling this field provider_id
        if "provider_uuid" in kwargs:
            uuid = kwargs.pop("provider_uuid")
            kwargs["provider_id"] = uuid

        return super().add(**kwargs)

    def manifest_ready_for_summary(self, manifest_id):
        """Determine if the manifest is ready to summarize."""
        return not self.is_last_completed_datetime_null(manifest_id)

    def number_of_files_processed(self, manifest_id):
        """Return the number of files processed in a manifest."""
        return CostUsageReportStatus.objects.filter(
            manifest_id=manifest_id, last_completed_datetime__isnull=False
        ).count()

    def is_last_completed_datetime_null(self, manifest_id):
        """Determine if nulls exist in last_completed_datetime for manifest_id.

        If the record does not exist, that is equivalent to a null completed datetime.
        Return True if record either doesn't exist or if null `last_completed_datetime`.
        Return False otherwise.

        """
        record = CostUsageReportStatus.objects.filter(manifest_id=manifest_id)
        if record:
            return record.filter(last_completed_datetime__isnull=True).exists()
        return True

    def get_manifest_list_for_provider_and_bill_date(self, provider_uuid, bill_date):
        """Return all manifests for a provider and bill date."""
        filters = {"provider_id": provider_uuid, "billing_period_start_datetime__date": bill_date}
        return CostUsageReportManifest.objects.filter(**filters).all()

    def get_last_manifest_upload_datetime(self, provider_uuid=None):
        """Return all ocp manifests with lastest upload datetime."""
        if provider_uuid:
            return (
                CostUsageReportManifest.objects.filter(provider_id=provider_uuid)
                .values("provider_id")
                .annotate(most_recent_manifest=Max("manifest_creation_datetime"))
            )
        else:
            return CostUsageReportManifest.objects.values("provider_id").annotate(
                most_recent_manifest=Max("manifest_creation_datetime")
            )

    def get_last_seen_manifest_ids(self, bill_date):
        """Return a tuple containing the assembly_id of the last seen manifest and a boolean

        The boolean will state whether or not that manifest has been processed."""
        assembly_ids = []
        # The following query uses a window function to rank the manifests for all the providers,
        # and then just pulls out the top ranked (most recent) manifests
        manifests = (
            CostUsageReportManifest.objects.filter(billing_period_start_datetime=bill_date)
            .annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=F("provider_id"),
                    order_by=F("manifest_creation_datetime").desc(),
                )
            )
            .order_by("row_number")
        )
        for manifest in [manifest for manifest in manifests if manifest.row_number == 1]:
            # loop through the manifests and decide if they have finished processing
            processed = self.manifest_ready_for_summary(manifest.id)
            # if all of the files for the manifest have been processed we don't want to add it
            # to assembly_ids because it is safe to delete
            if not processed:
                assembly_ids.append(manifest.assembly_id)
        return assembly_ids

    def purge_expired_report_manifest(self, provider_type, expired_date):
        """
        Deletes Cost usage Report Manifests older than expired_date.

        Args:
            provider_type   (String) the provider type to delete associated manifests
            expired_date (datetime.datetime) delete all manifests older than this date, exclusive.
        """
        delete_count = CostUsageReportManifest.objects.filter(
            provider__type=provider_type, billing_period_start_datetime__lt=expired_date
        ).delete()[0]
        LOG.info(
            "Removed %s CostUsageReportManifest(s) for provider type %s that had a billing period start date before %s",
            delete_count,
            provider_type,
            expired_date,
        )

    def purge_expired_report_manifest_provider_uuid(self, provider_uuid, expired_date):
        """
        Delete cost usage reports older than expired_date and provider_uuid.

        Args:
            provider_uuid (uuid) The provider uuid to use to delete associated manifests
            expired_date (datetime.datetime) delete all manifests older than this date, exclusive.
        """
        delete_count = CostUsageReportManifest.objects.filter(
            provider_id=provider_uuid, billing_period_start_datetime__lt=expired_date
        ).delete()
        LOG.info(
            "Removed %s CostUsageReportManifest(s) for provider_uuid %s that had a billing period start date before %s",
            delete_count,
            provider_uuid,
            expired_date,
        )

    def get_s3_csv_cleared(self, manifest):
        """Return whether we have cleared CSV files from S3 for this manifest."""
        s3_csv_cleared = False
        if manifest:
            s3_csv_cleared = manifest.s3_csv_cleared
        return s3_csv_cleared

    def mark_s3_csv_cleared(self, manifest):
        """Return whether we have cleared CSV files from S3 for this manifest."""
        if manifest:
            manifest.s3_csv_cleared = True
            manifest.save()

    def get_s3_parquet_cleared(self, manifest):
        """Return whether we have cleared CSV files from S3 for this manifest."""
        s3_parquet_cleared = False
        if manifest:
            s3_parquet_cleared = manifest.s3_parquet_cleared
        return s3_parquet_cleared

    def mark_s3_parquet_cleared(self, manifest):
        """Return whether we have cleared CSV files from S3 for this manifest."""
        if manifest:
            manifest.s3_parquet_cleared = True
            manifest.save()

    def get_manifest_list_for_provider_and_date_range(self, provider_uuid, start_date, end_date):
        """Return a list of GCP manifests for a date range."""
        manifests = (
            CostUsageReportManifest.objects.filter(provider_id=provider_uuid)
            .annotate(
                partition_date=Cast(
                    Func(F("assembly_id"), Value("|"), Value(1), function="split_part", output_field=DateField()),
                    output_field=DateField(),
                ),
                previous_export_time=Cast(
                    Func(F("assembly_id"), Value("|"), Value(2), function="split_part", output_field=DateTimeField()),
                    output_field=DateTimeField(),
                ),
            )
            .filter(partition_date__gte=start_date, partition_date__lte=end_date)
        )
        return manifests

    def bulk_delete_manifests(self, provider_uuid, manifest_id_list):
        """
        Deletes a specific manifest given manifest_id & provider_uuid
        Args:
            provider_uuid (uuid): The provider uuid to use to delete associated manifests
            manifest_id_list (list): list of manifest ids to delete.
        """
        if not manifest_id_list:
            return
        msg = f"""
        Attempting to delete the following manifests:
           manifest_list: {manifest_id_list}
           manifest_count: {len(manifest_id_list)}
        """
        LOG.info(msg)
        delete_count = CostUsageReportManifest.objects.filter(
            provider_id=provider_uuid, id__in=manifest_id_list
        ).delete()
        LOG.info(
            "Removed %s manifests for provider_uuid %s",
            delete_count,
            provider_uuid,
        )
