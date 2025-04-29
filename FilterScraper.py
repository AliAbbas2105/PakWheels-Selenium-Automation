import sqlite3
from bs4 import BeautifulSoup, NavigableString
import re
import requests
import time


class PakWheelsFilterScraper:
    def __init__(self, db_path='filters.db'):
        self.db_path = db_path
        self.base_url = 'https://www.pakwheels.com'
        self.main_url = f'{self.base_url}/used-cars/search/-/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS filter_enum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filter_name TEXT,
            value TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS filter_range (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filter_name TEXT,
            min INTEGER,
            max INTEGER,
            step INTEGER
        )''')  
        conn.commit()
        conn.close()

    def fetch_and_parse_live_filters(self):
        resp = requests.get(self.main_url, headers=self.headers)
        resp.raise_for_status()
        time.sleep(2)
        soup = BeautifulSoup(resp.text, 'html.parser')
        filters = {}
        for group in soup.select('.accordion-group'):
            heading = group.select_one('.accordion-heading .accordion-toggle')
            if not heading:
                continue
            filter_name = heading.get_text(strip=True)
            if group.select_one('.range-filter'):
                range_inputs = group.select('.range-filter input[type="text"]')
                if range_inputs and 'data-hintify' in range_inputs[0].attrs:
                    hint = range_inputs[0]['data-hintify']
                    min_val = re.search(r'"min":(\d+)', hint)
                    max_val = re.search(r'"max":(\d+)', hint)
                    step_val = re.search(r'"step":(\d+)', hint)
                    filters[filter_name] = {
                        'type': 'range',
                        'min': int(min_val.group(1)) if min_val else None,
                        'max': int(max_val.group(1)) if max_val else None,
                        'step': int(step_val.group(1)) if step_val else None
                    }
                continue
            options = []
            for li in group.select('ul.list-unstyled li'):
                label = li.select_one('label')
                if label:
                    a = label.select_one('a')
                    label_source = a if a else label
                    option_texts = []
                    for child in label_source.children:
                        if isinstance(child, NavigableString):
                            text = child.strip()
                            if text:
                                option_texts.append(text)
                        elif hasattr(child, 'name'):
                            if child.name == 'p':
                                text = child.get_text(strip=True)
                                if text:
                                    option_texts.append(text)
                    option_text = ' '.join(option_texts)
                    option_text = re.sub(
                        r'\s*\d{1,3}(,\d{3})*$', '', option_text)
                    if option_text:
                        options.append(option_text)

            more_choice = group.select_one('.more-choice')
            popup_options = []
            if more_choice and 'onclick' in more_choice.attrs:
                onclick = more_choice['onclick']
                ajax_url = re.search(r"load\('([^']+)'", onclick)
                if ajax_url:
                    ajax_full_url = self.base_url + ajax_url.group(1)
                    try:
                        ajax_resp = requests.get(
                            ajax_full_url, headers=self.headers)
                        ajax_resp.raise_for_status()
                        ajax_soup = BeautifulSoup(
                            ajax_resp.text, 'html.parser')
                        for li in ajax_soup.select('ul.list-unstyled li'):
                            label = li.select_one('label')
                            if label:
                                a = label.select_one('a')
                                label_source = a if a else label
                                option_texts = []
                                for child in label_source.children:
                                    if isinstance(child, NavigableString):
                                        text = child.strip()
                                        if text:
                                            option_texts.append(text)
                                    elif hasattr(child, 'name'):
                                        if child.name == 'p':
                                            text = child.get_text(strip=True)
                                            if text:
                                                option_texts.append(text)
                                option_text = ' '.join(option_texts)
                                option_text = re.sub(
                                    r'\s*\d{1,3}(,\d{3})*$', '', option_text)
                                if option_text:
                                    popup_options.append(option_text)
                        time.sleep(0.5)
                    except Exception as e:
                        print(
                            f"Failed to fetch expanded options for {filter_name}: {e}")
            all_options = list(dict.fromkeys(options + popup_options))
            if all_options:
                if filter_name in filters and filters[filter_name]['type'] == 'enum':
                    filters[filter_name]['options'] = list(dict.fromkeys(
                        filters[filter_name]['options'] + all_options))
                else:
                    filters[filter_name] = {
                        'type': 'enum',
                        'options': all_options
                    }
        return filters

    def update_all_filters_in_db(self, filters):
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute('DELETE FROM filter_enum')
                conn.execute('DELETE FROM filter_range')
                for filter_name, filter_info in filters.items():
                    if filter_info['type'] == 'enum':
                        for value in filter_info['options']:
                            conn.execute(
                                'INSERT INTO filter_enum (filter_name, value) VALUES (?, ?)', (filter_name, value))
                    elif filter_info['type'] == 'range':
                        conn.execute('INSERT INTO filter_range (filter_name, min, max, step) VALUES (?, ?, ?, ?)',
                                     (filter_name, filter_info.get('min'), filter_info.get('max'), filter_info.get('step')))
        finally:
            conn.close()

    def get_enum_options(self, filter_name):
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                'SELECT value FROM filter_enum WHERE filter_name = ?', (filter_name,))
            return [row[0] for row in c.fetchall()]
        finally:
            conn.close()

    def get_range_filter(self, filter_name):
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                'SELECT min, max, step FROM filter_range WHERE filter_name = ?', (filter_name,))
            row = c.fetchone()
            if row:
                return {'min': row[0], 'max': row[1], 'step': row[2]}
            return None
        finally:
            conn.close()


if __name__ == '__main__':
    scraper = PakWheelsFilterScraper()
    scraper.init_db()
    print('\n--- Fetching live filter data from PakWheels ---')
    filters = scraper.fetch_and_parse_live_filters()
    scraper.update_all_filters_in_db(filters)
    print('All filter options updated in database.')
