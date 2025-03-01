#
# Copyright 2022 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""HCS daily report builder"""
import logging

from api.common import log_json
from hcs.database.report_db_accessor import HCSReportDBAccessor
from hcs.exceptions import HCSTableNotFoundError
from masu.external.date_accessor import DateAccessor
from masu.util.common import date_range

LOG = logging.getLogger(__name__)


class ReportHCS:
    """Class to write HCS daily report summary data."""

    def __init__(self, schema_name, provider, provider_uuid, tracing_id):
        """Establish parquet summary processor."""
        self._schema_name = schema_name
        self._provider = provider
        self._provider_uuid = provider_uuid
        self._date_accessor = DateAccessor()
        self._tracing_id = tracing_id

    def generate_report(self, start_date, end_date, finalize=False):
        """Generate HCS daily report
        :param start_date (str) The date to start populating the table
        :param end_date   (str) The date to end on
        :param finalize   (bool) Set to True when report is final(default=False)

        returns (none)
        """
        sql_file = f"sql/reporting_{self._provider.lower()}_hcs_daily_summary.sql"

        with HCSReportDBAccessor(self._schema_name) as accessor:
            try:
                for date in date_range(start_date, end_date, step=1):
                    accessor.get_hcs_daily_summary(
                        date, self._provider, self._provider_uuid, sql_file, self._tracing_id, finalize
                    )

            except HCSTableNotFoundError as tnfe:
                LOG.info(log_json(self._tracing_id, f"{tnfe}, skipping..."))

            except Exception as e:
                LOG.error(log_json(self._tracing_id, e))
