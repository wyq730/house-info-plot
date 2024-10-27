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

    @property
    def is_valid(self) -> bool:
        return self.unit_price != 0

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
_UNIT_PRICE_RANGE_FOR_PLOT = [0, 15]  # Fix this to avoid the dynamic adaptation of y-axis.
_FILLS = [
    [datetime(year=2016, month=1, day=1), datetime(year=2017, month=1, day=1)],
    [datetime(year=2021, month=1, day=1), datetime(year=2022, month=1, day=1)]
]
_HORIZONTAL_MARKS = [
    (6, 'rgba(0, 128, 0, 0.2)'),
    (8, 'rgba(218, 165, 32, 0.4)'),
    (10, 'rgba(255, 0, 0, 0.2)'),
]


def plot_monthly_price_fig():
    monthly_price_fig = go.Figure()
    monthly_price_fig.update_layout(
        title='小区单价图',
        xaxis_title='月份',
        yaxis_title='单价 (万/平米)',
        plot_bgcolor='rgba(100, 149, 237, 0.1)'
    )
    monthly_price_fig.update_xaxes(
        tickformat="%Y/%m", dtick='M6'
    )
    monthly_price_fig.update_yaxes(
        range=_UNIT_PRICE_RANGE_FOR_PLOT,
        dtick='0.5'
    )

    min_date = datetime(year=9999, month=1, day=1)  # Serves as infinite.
    max_date = datetime(year=1, month=1, day=1)  # Serves as negative infinite.
    min_unit_price = float('inf')
    max_unit_price = float('-inf')

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

                if not record.is_valid:
                    logger.warning(
                        f'Found invalid record: record {record_id} from "{file_full_path}".')
                    continue

                min_date = min(min_date, record.selling_month)
                max_date = max(max_date, record.selling_month)
                min_unit_price = min(min_unit_price, record.unit_price)
                max_unit_price = max(max_unit_price, record.unit_price)

                records_by_month[record.selling_month].append(record)
                record_id += 1

        plot_info_my_month = {}
        for month, records in records_by_month.items():

            all_unit_price = [r.unit_price for r in records]
            avg_unit_price = statistics.mean(all_unit_price)

            detail_text = f'{len(records)} 个成交:<br>' + '<br>'.join(
                [f'[{r.selling_date.strftime("%Y-%m-%d")}] {r.price} = {r.unit_price} &times; {r.area} (平米) [ {r.floor} ] [ {r.window_direction} ] [ {r.floor_plan} ] [ {r.furnish} ]' for r in sorted(records, key=attrgetter('selling_date'))])

            plot_info_my_month[month] = {
                'avg_price': avg_unit_price,
                'detail': detail_text
            }

        months = list(plot_info_my_month.keys())
        line = go.Scatter(mode='lines+markers', name=community,
                          x=months, y=[plot_info_my_month[month]['avg_price']
                                       for month in months],
                          customdata=[m.strftime('%Y/%m') for m in months],
                          hovertemplate='<b>%{customdata}: %{y} 万/平米</b><br><br>%{text}<extra></extra>',
                          text=[plot_info_my_month[month]['detail'] for month in months])
        monthly_price_fig.add_trace(line)

    # 给区域染色。
    for fill in _FILLS:
        monthly_price_fig.add_trace(go.Scatter(
            x=[fill[0], fill[0], fill[1], fill[1]],
            y=[_UNIT_PRICE_RANGE_FOR_PLOT[0], _UNIT_PRICE_RANGE_FOR_PLOT[1],
                _UNIT_PRICE_RANGE_FOR_PLOT[1], _UNIT_PRICE_RANGE_FOR_PLOT[0]],
            mode='lines',
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.1)',
            line=dict(color='rgba(255, 255, 255, 0)'),
            showlegend=False,
            hoverinfo='none'
        ))

    # 画横线。
    for y, color in _HORIZONTAL_MARKS:
        monthly_price_fig.add_trace(go.Scatter(
            x=[min_date, max_date],
            y=[y, y],
            mode='lines',
            line=dict(color=color, width=1.2),
            showlegend=False,
            hoverinfo='none'
        ))

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
