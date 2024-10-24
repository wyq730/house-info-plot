import os
from os.path import join
import plotly.graph_objects as go
import csv
import pandas as pd

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = join(CURR_DIR, 'data')
RESULT_DIR = join(CURR_DIR, 'result')

def _get_community_from_file_name(file_full_name: str) -> str:
    file_full_name_parts = file_full_name.split('.')
    assert len(file_full_name_parts) == 2
    file_name = file_full_name_parts[0]

    file_name_parts = file_name.split('_')
    assert len(file_name_parts) == 2
    community_name = file_name_parts[0]

    return community_name

def main():
    fig = go.Figure()
    for file_full_name in os.listdir(DATA_DIR):
        community = _get_community_from_file_name(file_full_name)

        data_frame = pd.read_csv(join(DATA_DIR, file_full_name))
        line = go.Scatter(x=data_frame['成交日期'], y=data_frame['单价'], mode='lines+markers', name=community)
        fig.add_trace(line)

    fig.write_html(join(RESULT_DIR, 'result.html'))



if __name__ == '__main__':
    main()
