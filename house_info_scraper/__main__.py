import requests
from bs4 import BeautifulSoup


def _get_sold_url(house_id: str):
    return f'https://bj.ke.com/chengjiao/{house_id}.html'


def _retrieve_sold_house_info():
    # TODO(yanqingwang): restore this.
    # response = requests.get(_get_sold_url('101119634361'))
    # html = response.text

    # TODO(yanqingwang): delete "example.html". That's just a cache.
    with open('example_html.txt') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    import pdb
    pdb.set_trace()


_retrieve_sold_house_info()
