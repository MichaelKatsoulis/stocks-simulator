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
    article['timestamp'] = time.mktime(date.timetuple())
    # article['timestamp'] = datetime.datetime.timestamp(date)
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
    to_go_up_comps = []
    to_go_down_comps = []
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
            # print("The length is {}".format(len(pl_list)))
            pos = neg = stable = 0
            for index, cumsum in enumerate(pl_list):
                if index == len(pl_list) - 1:
                    break
                diff = pl_list[index + 1] - pl_list[index]
                if diff == 0:
                    stable += 1
                elif diff > 0:
                    pos += 1
                else:
                    neg += 1
            pos = pos + stable
            neg = neg + stable
            if pos / len(pl_list) > config.per_of_points_to_be_pos_or_neg:
                if pl_list[-1] > pl_list[0]:
                    per_change = (
                        pl_list[-1] - pl_list[0]) / abs(pl_list[0])
                    if abs(per_change) >= config.per_of_raise:
                        to_go_up_comps.append(company)
                        # print("We should buy from {}".format(company))
                        # print(to_pl['cumsum'][-config.number_of_daypoints:])
            else:
                if neg / len(pl_list) > config.per_of_points_to_be_pos_or_neg:
                    if pl_list[0] > pl_list[-1]:
                        per_change = (
                            pl_list[-1] - pl_list[0]) / abs(pl_list[0])
                        # print(act_decline)
                        if per_change <= -config.per_of_decline:
                            to_go_down_comps.append(company)
                            # print("We should buy from {}".format(company))
                            # print(to_pl['cumsum'][-config.number_of_daypoints:])
    date_1 = datetime.datetime.strptime(date, '%Y-%m-%d')
    start_date = (date_1 + datetime.
                  timedelta(days=1))\
        .strftime('%Y-%m-%d')
    end_date = (date_1 + datetime.
                timedelta(days=config.days_to_check_price))\
        .strftime('%Y-%m-%d')

    actual_up = []
    for comp in to_go_up_comps:
        comp_stock = yf.download(
            config.map_scrader_name_to_market[comp],
            start=start_date, end=end_date
        )
        # print(comp)
        # print(comp_stock)
        starting_price = comp_stock['Close'][0]

        for price in comp_stock['Close'].to_list()[1:]:
            perc = (float(price) - float(starting_price)) / \
                (float(starting_price))
            # print(perc)
            if perc >= config.per_of_raise:
                actual_up.append(comp)
                break
    actual_down = []
    for comp in to_go_down_comps:
        comp_stock = yf.download(
            config.map_scrader_name_to_market[comp],
            start=start_date, end=end_date
        )
        # print(comp)
        # print(comp_stock)
        starting_price = comp_stock['Close'][0]

        for price in comp_stock['Close'].to_list()[1:]:
            perc = (float(price) - float(starting_price)) / \
                (float(starting_price))
            # print(perc)
            if perc <= -config.per_of_decline:
                actual_down.append(comp)
                break

    print("In date {} we have {} companies with enough articles".format(
        date, len(companies)))
    if len(to_go_up_comps) > 0:
        print("After applying the rules we believe that {} will go up".
              format(to_go_up_comps))
        print("Actually went up {}".format(actual_up))
        print("Percentage of successfull prediction of raise is: {}%".
              format((len(actual_up) / len(to_go_up_comps)) * 100))
    if len(to_go_down_comps):
        print("{} will go down".format(to_go_down_comps))
        print("Actually went down {}".format(actual_down))
        print("Percentage of successfull prediction of reduction is: {}%".
              format((len(actual_down) / len(to_go_down_comps)) * 100))

    # break
