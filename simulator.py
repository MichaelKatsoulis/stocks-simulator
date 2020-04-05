import yfinance as yf
import pandas as pd
import json
import config
import utils
import datetime
import time
# from scipy.stats import pearsonr

all_dates = []
scrapings = []
for line in open(r'articles.json', 'r'):
    scrapings.append(json.loads(line))

# print(len(scrapings))

# data = pd.DataFrame(scrapings)
# data.company = data.company.apply(utils.remove_spaces)
for article in scrapings:
    date = datetime.datetime.strptime(article.get('subtitle'), '%m/%d/%Y')
    # article['timestamp'] = datetime.datetime.timestamp(date)
    article['timestamp'] = time.mktime(date.timetuple())
    article['date'] = datetime.datetime.strptime(
        article.get('subtitle'), '%m/%d/%Y').strftime('%Y-%m-%d')
    article['subtitle'] = pd.Timestamp(article['subtitle'])
    article['company'] = utils.remove_spaces(article.get('company'))

date_sorted_scrapings = sorted(scrapings, key=lambda k: k['timestamp'])
dataframe_scrapings = pd.DataFrame(date_sorted_scrapings)
dataframe_scrapings.set_index('subtitle', inplace=True)

for article in date_sorted_scrapings:
    if article.get('date') not in all_dates:
        all_dates.append(article.get('date'))

# print(utils.companies_between_limits('2019-02-28', date_sorted_scrapings))
# print(len(all_dates))
# all_dates = ['2019-02-28']
for date in all_dates[50::10]:
    to_buy_comps = []
    companies = utils.companies_between_limits(date, date_sorted_scrapings)
    companies = utils.companies_with_articles_x_days_before_date(
        date, date_sorted_scrapings, companies)
    # day_to_trade = pd.Timestamp(date)
    # print("In date {} we have {} companies".format(date, len(companies)))
    if len(companies) > 0:
        for company in companies:
            if config.map_scrader_name_to_market.get(company) is None:
                # print('You should map {} to its market value also'.format(company))
                continue

            to_pl = pd.DataFrame(dataframe_scrapings.loc[dataframe_scrapings.company == company]).\
                direction.replace('POS', 0.4).replace(
                    'NEG', -1).reset_index().groupby('subtitle')['direction'].mean().reset_index()

            to_pl['cumsum'] = to_pl.direction.cumsum()
            to_pl.set_index('subtitle', inplace=True)

            # print(to_pl.index.min())
            # print(date)
            # print(to_pl.to_dict("index"))

            new_index = pd.date_range(
                start=to_pl.index.min(), end=date)
            to_pl = to_pl.reindex(new_index)
            # print(to_pl)

            nan = 0
            for i in range(config.number_of_daypoints, 0, -1):
                if str(to_pl['cumsum'][-i]) == 'nan':
                    nan += 1
            if nan / config.number_of_daypoints > config.nan_accepted:
                continue

            to_pl = to_pl.interpolate(method='linear')

            stock = yf.download(
                config.map_scrader_name_to_market[company],
                start=to_pl.index.min(), end=date
            )
            # print("Company {}".format(company))
            # print(stock.Close)
            # print(to_pl['cumsum'])
            # print("Company {} has {} corellation".format(company, corr))
            stock['scrader'] = to_pl['cumsum'].shift(3)
            corr_df = stock[['Close', 'scrader']].corr(method='pearson')
            correlation = corr_df.to_dict().get('Close').get('scrader')
            # print("Company {} has {} corellation".format(company, correlation))
            if correlation < config.accepted_pearson_corr:
                continue

            pl_list = to_pl['cumsum'].to_list(
            )[-config.number_of_daypoints:]

            pos = 0
            for index, cumsum in enumerate(pl_list):
                if index == len(pl_list) - 1:
                    break
                if pl_list[index + 1] - pl_list[index] > 0:
                    pos += 1
            if pos / len(pl_list) > config.per_of_points_to_be_pos:
                if pl_list[-1] > pl_list[0]:
                    act_raise = pl_list[-1] / pl_list[0] - 1
                    # print(act_raise)
                    if act_raise > config.per_of_raise:
                        to_buy_comps.append(company)
                        # print("We should buy from {}".format(company))
                        # print(to_pl['cumsum'][-config.number_of_daypoints:])
                        # print(act_raise)
    print("In date {} we have {} companies with enough articles".format(
        date, len(companies)))
    print("After applying the rules you can only buy from {}".format(to_buy_comps))
    # break
