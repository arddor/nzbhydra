from itertools import groupby
import logging

from marshmallow import Schema, fields

from nzbhydra import config

from nzbhydra.config import init
from nzbhydra import providers

logger = logging.getLogger('root')

init("ResultProcessing.duplicateSizeThresholdInPercent", 0.1, float)
init("ResultProcessing.duplicateAgeThreshold", 36000, int)

categories = {'Console': {'code': [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080], 'pretty': 'Console'},
              'Movie': {'code': [2000, 2010, 2020], 'pretty': 'Movie'},
              'Movie_HD': {'code': [2040, 2050, 2060], 'pretty': 'HD'},
              'Movie_SD': {'code': [2030], 'pretty': 'SD'},
              'Audio': {'code': [3000, 3010, 3020, 3030, 3040], 'pretty': 'Audio'},
              'PC': {'code': [4000, 4010, 4020, 4030, 4040, 4050, 4060, 4070], 'pretty': 'PC'},
              'TV': {'code': [5000, 5020], 'pretty': 'TV'},
              'TV_SD': {'code': [5030], 'pretty': 'SD'},
              'TV_HD': {'code': [5040], 'pretty': 'HD'},
              'XXX': {'code': [6000, 6010, 6020, 6030, 6040, 6050], 'pretty': 'XXX'},
              'Other': {'code': [7000, 7010], 'pretty': 'Other'},
              'Ebook': {'code': [7020], 'pretty': 'Ebook'},
              'Comics': {'code': [7030], 'pretty': 'Comics'},
              }


def find_duplicates(results):
    """

    :type results: list[NzbSearchResult]
    """
    # TODO we might want to be able to specify more precisely what item we pick of a group of duplicates, for example by indexer priority 

    # Sort and group by title. We only need to check the items in each individual group against each other because we only consider items with the same title as possible duplicates
    sorted_results = sorted(results, key=lambda x: x.title.lower())
    grouped_by_title = groupby(sorted_results, key=lambda x: x.title.lower())
    grouped_by_sameness = []

    for key, group in grouped_by_title:
        seen2 = set()
        group = list(group)
        for i in range(len(group)):
            if group[i] in seen2:
                continue
            seen2.add(group[i])
            same_results = [group[i]]  # All elements in this list are duplicates of each other 
            for j in range(i + 1, len(group)):
                if group[j] in seen2:
                    continue
                seen2.add(group[j])
                if test_for_duplicate(group[i], group[j]):
                    same_results.append(group[j])
            grouped_by_sameness.append(same_results)

    return grouped_by_sameness


def test_for_duplicate(search_result_1, search_result_2):
    """

    :type search_result_1: NzbSearchResult
    :type search_result_2: NzbSearchResult
    """

    if search_result_1.title.lower() != search_result_2.title.lower():
        return False
    size_threshold = config.cfg["ResultProcessing.duplicateSizeThresholdInPercent"]
    size_difference = search_result_1.size - search_result_2.size
    size_average = (search_result_1.size + search_result_2.size) / 2
    size_difference_percent = abs(size_difference / size_average) * 100


    # TODO: Ignore age threshold if no precise date is known or account for score (if we have sth like that...) 
    age_threshold = config.cfg["ResultProcessing.duplicateAgeThreshold"]
    same_size = size_difference_percent <= size_threshold
    same_age = abs(search_result_1.epoch - search_result_2.epoch) / (1000 * 60) <= age_threshold  # epoch difference (ms) to minutes

    # If all nweznab providers would provide poster/group in their infos then this would be a lot easier and more precise
    # We could also use something to combine several values to a score, say that if a two posts have the exact size their age may differe more or combine relative and absolute size comparison
    if same_size and same_age:
        return True


class ProviderSchema(Schema):
    name = fields.String()
    module = fields.String()
    enabled = fields.Boolean()
    settings = fields.String()


class NzbSearchResultSchema(Schema):
    title = fields.String()
    link = fields.String()
    epoch = fields.Integer()
    pubdate_utc = fields.String()
    age_days = fields.Integer()
    age_precise = fields.Boolean()
    provider = fields.String()
    guid = fields.String()
    size = fields.Integer()
    category = fields.String()
    has_nfo = fields.Boolean()


class ProviderApiAccess(Schema):
    provider = fields.Nested(ProviderSchema, only="name")
    time = fields.DateTime()
    type = fields.String()
    url = fields.String()
    response_successful = fields.Boolean()
    response_time = fields.Integer()
    error = fields.String()


class ProviderSearchSchema(Schema):
    provider = fields.Nested(ProviderSchema, only="name")
    time = fields.DateTime()
    successful = fields.Boolean()
    results = fields.Integer()

    api_accesses = fields.Nested(ProviderApiAccess, many=True)


def process_for_internal_api(results):
    # results: list of dicts, <provider>:dict "providersearchdbentry":<ProviderSearch>,"results":[<NzbSearchResult>]
    nzbsearchresults = []
    providersearchdbentries = []
    for i in results.values():
        nzbsearchresults.extend(i["results"])
        providersearchdbentries.append(ProviderSearchSchema().dump(i["providersearchdbentry"]).data)

    grouped_by_sameness = find_duplicates(nzbsearchresults)


    # Will be sorted by GUI later anyway but makes debugging easier
    results = sorted(grouped_by_sameness, key=lambda x: x[0].epoch, reverse=True)
    serialized = []
    for g in results:
        serialized.append(serialize_nzb_search_result(g).data)

    # We give each group of results a unique count value by which they can be identified later even if they're "taken apart"
    for count, group in enumerate(serialized):
        for i in group:
            i["count"] = count
    return {"results": serialized, "providersearches": providersearchdbentries}


def serialize_nzb_search_result(result):
    return NzbSearchResultSchema(many=True).dump(result)


def get_nfo(provider_name, guid):
    nfo = None
    result = {}
    for p in providers.providers:
        if p.name == provider_name:
            nfo = p.get_nfo(guid)
            break
    else:
        logger.error("Did not find provider with name %s" % provider_name)
        result["error"] = "Unable to find provider"
    if nfo is None:
        logger.info("Unable to find NFO for provider %s and guid %s" % (provider_name, guid))
        result["has_nfo"] = False
    else:
        result["has_nfo"] = True
        result["nfo"] = nfo
    return result
