import os
from os.path import join
import plotly.graph_objects as go
import sys
import csv
import pandas as pd
from datetime import datetime

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = join(CURR_DIR, 'data')
RESULT_DIR = join(CURR_DIR, 'result')


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
        self.selling_price = int(self._get_field_from_dict(csv_row_dict, '成交价格(万)'))

        self.selling_date = self._parse_date(self._get_field_from_dict(csv_row_dict, '成交日期'))

        listing_time = self._get_field_from_dict(csv_row_dict, '成交周期(天)', allow_empty=True)
        self.listing_time = int(listing_time) if listing_time is not None else None
        self.selling_price_per_unit = float(self._get_field_from_dict(csv_row_dict, '单价'))
        self.area = float(self._get_field_from_dict(csv_row_dict, '面积(平米)'))
        self.window_direction = self._get_field_from_dict(csv_row_dict, '朝向')
        self.furnish = self._get_field_from_dict(csv_row_dict, '装修')
        self.floor = self._get_field_from_dict(csv_row_dict, '楼层')
        self.building_type = self._get_field_from_dict(
            csv_row_dict, '楼型', allow_empty=True, empty_value='')

    @property
    def selling_month(self) -> str:
        return self.selling_date.strftime('%Y-%m')

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


def main():
    fig = go.Figure()
    for file_full_name in os.listdir(DATA_DIR):
        file_full_path = join(DATA_DIR, file_full_name)
        community = _get_community_from_file_name(file_full_name)

        records = []
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

                records.append(record)

                record_id += 1

        # data_frame = pd.read_csv(join(DATA_DIR, file_full_name))
        # line = go.Scatter(x=data_frame['成交日期'], y=data_frame['单价'], mode='lines+markers', name=community)
        # fig.add_trace(line)

        # import pdb; pdb.set_trace()

    fig.write_html(join(RESULT_DIR, 'result.html'))


if __name__ == '__main__':
    main()
