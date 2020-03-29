import config

from datetime import datetime

def remove_spaces(x):
    res = str(x).replace(" ", "_")
    return res


def companies_between_limits(datetime, my_list):
    companies_articles_map = {}
    companies = []
    for article in my_list:
        if article.get('date') <= datetime:
            name = article.get('company')
            if name not in companies_articles_map.keys():
                companies_articles_map[name] = 0

            companies_articles_map[name] += 1
    for comp, articles in companies_articles_map.items():
        if articles >= 100 and articles <= 400:
            new_tuple = (comp, articles)
            companies.append(new_tuple)
    return companies

def companies_with_articles_x_days_before_date(date, my_list, companies):
	ret = []
	date_format = "%Y-%m-%d"
	given_timestamp = datetime.strptime(date, date_format)
	for company in companies:
		name = company[0]
		for article in my_list:
			if article.get('company') == name:
				first_date =  datetime.strptime(article.get('date'), date_format)
				# print('Company {} first date is {} while given date is {}'.format(name, first_date, given_timestamp))
				delta = given_timestamp - first_date
				if delta.days >= config.days_to_have_articles:
					ret.append(name)
				break
	return ret

