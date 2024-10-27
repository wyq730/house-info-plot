import os
from os.path import join
import plotly.graph_objects as go
import sys
import csv
import pandas as pd
from datetime import datetime
from collections import defaultdict
from loguru import logger
import statistics
from operator import attrgetter

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = join(CURR_DIR, 'data')
DIST_DIR = join(CURR_DIR, 'dist')


def _assert(condition, message=''):
    if not condition:
        raise AssertionError(message)


def _get_community_from_file_name(file_full_name: str) -> str:
    file_full_name_parts = file_full_name.split('.')
    _assert(len(file_full_name_parts) == 2)
    file_name = file_full_name_parts[0]

    file_name_parts = file_name.split('_')
    _assert(len(file_name_parts) == 2)
    community_name = file_name_parts[0]

    return community_name


class Record:
    NOT_AVAILABLE = '_NOT_AVAILABLE'

    def __init__(self, csv_row_dict: dict):
        self.link = self._get_field_from_dict(csv_row_dict, '链接')
        self.floor_plan = self._get_field_from_dict(csv_row_dict, '户型')
        self.price = int(self._get_field_from_dict(csv_row_dict, '成交价格(万)'))

        self.selling_date = self._parse_date(self._get_field_from_dict(csv_row_dict, '成交日期'))

        listing_time = self._get_field_from_dict(csv_row_dict, '成交周期(天)', allow_empty=True)
        self.listing_time = int(listing_time) if listing_time is not None else None
        self.unit_price = float(self._get_field_from_dict(csv_row_dict, '单价'))
        self.area = float(self._get_field_from_dict(csv_row_dict, '面积(平米)'))
        self.window_direction = self._get_field_from_dict(csv_row_dict, '朝向')
        self.furnish = self._get_field_from_dict(csv_row_dict, '装修')
        self.floor = self._get_field_from_dict(csv_row_dict, '楼层')
        self.building_type = self._get_field_from_dict(
            csv_row_dict, '楼型', allow_empty=True, empty_value='')

    @property
    def selling_month(self) -> datetime:
        return datetime.strptime(self.selling_date.strftime('%Y-%m'), '%Y-%m')

    @staticmethod
    def _get_field_from_dict(d: dict, field_name: str, *, allow_empty: bool = False, empty_value=None) -> str:
        if not allow_empty and empty_value is not None:
            print('empty_value is set, but allow_empty=false.', file=sys.stderr)

        _assert(field_name in d, f'No field "{field_name}" in record: {d}')

        _assert(d[field_name] is not None,
                f'Field "{field_name}" is None in record: {d}')

        if allow_empty:
            return d[field_name] if d[field_name] != '' else empty_value
        else:
            _assert(d[field_name] != '',
                    f'Field "{field_name}" is empty ("") in record: {d}')
            return d[field_name]

    @staticmethod
    def _parse_date(date_str: str):
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d")
        if len(date_str) == 7:
            return datetime.strptime(date_str, "%Y-%m")
        raise ValueError(f'Invalid date string: {date_str}')


_CSV_REST_KEY = '_additional_values'


def plot_monthly_price_fig():
    monthly_price_fig = go.Figure()

    for file_full_name in os.listdir(DATA_DIR):
        file_full_path = join(DATA_DIR, file_full_name)
        community = _get_community_from_file_name(file_full_name)

        records_by_month = defaultdict(list)
        with open(file_full_path, newline='') as f:
            reader = csv.DictReader(f, restkey=_CSV_REST_KEY)

            record_id = 1
            for row in reader:
                _assert(_CSV_REST_KEY not in row,
                        f'Additional values detected from record {record_id} from "{file_full_path}".')
                try:
                    record = Record(row)
                except Exception as e:
                    raise RuntimeError(
                        f'Failed to parse record {record_id} from "{file_full_path}".') from e

                records_by_month[record.selling_month].append(record)
                record_id += 1

        avg_unit_price_by_month = {}
        for month, records in records_by_month.items():
            valid_records = sorted([r for r in records if r.unit_price != 0],
                                   key=attrgetter('selling_date'))
            if len(records) != len(valid_records):
                logger.warning(
                    f'There are {len(records) - len(valid_records)} records with 0 selling price (per unit). community: "{community}", month: "{month.strftime("%Y-%m")}"')

            if len(valid_records) == 0:
                continue

            all_unit_price = [r.unit_price for r in valid_records]
            avg_unit_price = statistics.mean(all_unit_price)
            avg_unit_price_by_month[month] = {
                'avg_price': avg_unit_price,
                'detail': f'{len(valid_records)} 个成交:<br>' + '<br>'.join([f'[{r.selling_date.strftime("%Y-%m-%d")}] {r.price} = {r.unit_price} &times; {r.area} (平米) [ {r.floor} ] [ {r.window_direction} ] [ {r.floor_plan} ] [ {r.furnish} ]' for r in valid_records])
            }

        months = list(avg_unit_price_by_month.keys())
        line = go.Scatter(mode='lines+markers', name=community,
                          x=months, y=[avg_unit_price_by_month[month]['avg_price']
                                       for month in months],
                          customdata=[m.strftime('%Y/%m') for m in months],
                          hovertemplate='<b>%{customdata}: %{y}</b><br><br>%{text}<extra></extra>',
                          text=[avg_unit_price_by_month[month]['detail'] for month in months])
        monthly_price_fig.add_trace(line)
    monthly_price_fig.write_html(join(DIST_DIR, 'monthly_price.html'))


def plot_all_fig():
    all_fig = go.Figure()
    for file_full_name in os.listdir(DATA_DIR):
        file_full_path = join(DATA_DIR, file_full_name)
        community = _get_community_from_file_name(file_full_name)

        data_frame = pd.read_csv(file_full_path)
        line = go.Scatter(x=data_frame['成交日期'], y=data_frame['单价'],
                          mode='lines+markers', name=community)
        all_fig.add_trace(line)
    all_fig.write_html(join(DIST_DIR, 'all.html'))


if __name__ == '__main__':
    plot_monthly_price_fig()
    plot_all_fig()
