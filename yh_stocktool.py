#!/usr/bin/env python3
import requests, sys, re, datetime, os, click, csv
from peewee import *
from collections import OrderedDict
from clint.textui import puts, prompt, columns


path = os.getenv('HOME', os.path.expanduser('~')) + '/.yh_stocktool'
db = SqliteDatabase(path+'/stock_data.db')


class Company(Model):
    id = CharField(primary_key=True)
    name = TextField(unique=True)

    class Meta:
        database = db


class Stock(Model):
    ask_price = CharField(null=True)
    pe_ratio = CharField(null=True)
    day_high = CharField(null=True)
    day_low = CharField(null=True)
    revenue = CharField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now())
    company = ForeignKeyField(Company, related_name='company_stock')

    class Meta:
        order_by = ('-timestamp', )
        database = db


def list_data():
    company = prompt.options('Enter corporation symbol:', get_company_options())
    if not company:
        puts('Exited')
        return
    elif company == '*':
        stocks_data = Stock.select()
    else:
        stocks_data = Stock.select().join(Company).where(Stock.company == company)
    if not stocks_data:
        puts('No stock records found')
    else:
        puts('Company :: P/E ratio :: Ask price :: Day High :: Day Low :: Revenue :: Timestamp')
        for stock in stocks_data:
            puts('{0} | {1} | {2} | {3} | {4} | {5} | {6}'.format(
                stock.company.name, stock.pe_ratio,stock.ask_price, stock.day_high,
                stock.day_low, stock.revenue, stock.timestamp
            ))


def list_companies():
    companies = Company.select()
    if not companies:
        puts('No companies found')
    else:
        for company in companies:
            puts('Company: {:s} | Symbol: {:s}'.format(company.name, company.id.upper()))


def add_company():
    sym = prompt.query('Enter corporation symbol\n>> ')
    data = get_data({
        's': sym,
        'f': 'n'
    })
    if not data[0]:
        puts('Invalid symbol')
        return
    new_company = Company.create_or_get(name=data[0], id=sym)
    if not new_company[1]:
        puts('Company already exists')
    else:
        puts("'{:s}' added to records".format(new_company[0].name))


def add_data():
    companies = Company.select().order_by(Company.id)
    if not companies:
        print('No company entries found')
    fields = ['ask_price', 'pe_ratio', 'day_high', 'day_low', 'revenue', 'company']
    for i in companies:
        data = get_data({
            's': i.id,
            'f': 'arhls6'
        })
        data.append(i.id)
        s = Stock.create(**dict(zip(fields, data)))
        puts('{:s} stock quote record added'.format(s.company.id.upper()))


def remove_company():
    sym = prompt.options('Enter corporation name/symbol:', get_company_options())
    if not sym:
        puts('Exited')
    elif sym == '*':
        Company.delete().execute()
        Stock.delete().execute()
        puts('All companies removed')
    else:
        for company in Company.select(Company, Stock).join(Stock).where(Stock.company == Company.id):
            for stock in company.company_stock:
                stock.delete_instance()
            if sym in company.id or sym in company.name:
                puts("'{:s}' deleted".format(company.name))
                company.delete_instance()


def remove_data():
    to_remove = prompt.options('Enter corporation symbol:', get_company_options())
    if not to_remove:
        puts('Exited')
    elif to_remove == '*':
        Stock.delete().execute()
        puts('All records removed')
    else:
        num_removed = 0
        records = Stock.select().join(Company).where(Stock.company == to_remove)
        for record in records:
            num_removed += record.delete_instance()
        puts('Cleared {:d} records from {:s}'.format(num_removed, to_remove))


def monitor_help():
    puts('Command :: Command Info')
    for k, v in monitor_commands.items():
        puts('[{0}] - {1}'.format(k, v[1]))


def get_company_options():
    formatted_company_list = [
        {'selector': '*', 'prompt': 'All companies', 'return': '*'},
        {'selector': 'q', 'prompt': 'Exit', 'return': None}
    ]
    for company in Company.select():
        formatted_company_list.append({
            'selector': company.id.upper(),
            'prompt': company.name,
            'return': company.id
        })
    return formatted_company_list


@click.group()
def main():
    pass


@main.command('m')
def monitor():
    ''' Toggle monitoring mode '''
    if not os.path.exists(path):
        os.makedirs(path)
    db.connect()
    db.create_tables([Stock, Company], safe=True)
    user_inp = prompt.query('Enter Commands (h for help)\n>> ')
    while user_inp != 'q':
        if user_inp not in monitor_commands.keys():
            puts('Invalid command')
        else:
            monitor_commands[user_inp][0]()
        puts()
        user_inp = prompt.query('Enter Commands (h for help)\n>> ')
    db.close()


@main.command('get')
@click.argument('option_string', type=click.STRING)
@click.argument('companies', type=click.STRING, nargs=-1, required=True)
def stock_data_process(option_string, companies):
    ''' Retrieve stock quotes on desired corporations '''
    data = get_data(process_args(option_string, companies))
    header = [options_list[i] for i in parse_options(option_string)]
    puts(' | '.join(header))
    for line in data:
        puts(' | '.join(line))


def parse_options(option_str):
    options = re.findall(r'\w\d?', option_str)
    for option in options:
        yield option.lower()


def process_args(option_str, companies):
    payload = {'f': ''}
    for option in parse_options(option_str):
        if option in dict(options_list):
            payload['f'] += option
        else:
            puts('Invalid option detected {:s}'.format(option))
            continue
    payload['s'] = '+'.join(companies)
    return payload


def format_results(data):
    payload = list()
    for item in data:
        if item == 'N/A':
            item = None
        payload.append(item)
    return payload


def get_data(options):
    base = 'http://finance.yahoo.com/d/quotes.csv'
    try:
        req = requests.get(base, params=options)
        req.raise_for_status()
    except requests.exceptions.HTTPError:
        exit_program('Error Occurred')
    if not req.text.strip():
        exit_program('Warning, No content returned. Company symbol may be invalid')
    text = csv.reader(req.text.split('\n'))
    return format_results(text)


@main.command('o')
def print_options():
    ''' Print financial data options '''
    option_w = 6
    func_w = 30
    puts(columns(['Option', option_w], ['Function', func_w]))
    for option in options_list.items():
        puts(columns([option[0], option_w], [option[1], func_w]))


def exit_program(error_msg):
    puts(error_msg)
    sys.exit(0)


monitor_commands = OrderedDict([
    ('h', [monitor_help, 'Display command information']),
    ('rd', [remove_data, 'Remove stock quote records']),
    ('rc', [remove_company, 'Remove company entries']),
    ('ad', [add_data, 'Retrieve stock quote records']),
    ('ac', [add_company, 'Add new companies']),
    ('lc', [list_companies, 'List company entries']),
    ('ld', [list_data, 'List stock quote records']),
    ('q', [None, 'Exit this program'])
])
options_list = {'a': 'Ask price',
                'b': 'Bid price',
                'e': 'EPS',
                'r': 'P/E ratio',
                'y': 'Dividend yield',
                'd': 'Dividend per share',
                'p': 'Previous close',
                'h': 'Day\'s high',
                'l': 'Day\'s low',
                'k':'Week\'s high',
                'j': 'Week\'s low',
                's6': 'Revenue',
                'n': 'Company name'
}

if __name__ == '__main__':
    main()