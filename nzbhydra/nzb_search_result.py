class NzbSearchResult:
    def __init__(self, title=None, link=None, provider=None, guid=None, size=None, category="N/A", attributes=[], epoch=None, pubdate_utc=None, age_days=None, poster=None, has_nfo=True):
        self.title = title
        self.link = link
        self.epoch = epoch
        self.pubdate_utc = pubdate_utc
        self.age_days = age_days
        self.age_precise = True #Set to false if the age is not received from a pubdate but from an age. That might influence duplicity check
        self.provider = provider
        self.guid = guid
        self.size = size
        self.category = category
        self.description = None
        self.comments = None
        self.attributes = attributes
        self.search_types = [] #"general", "tv", "movie"
        self.supports_queries = True #Providers might only provide a feed of the latest releases, e.g. womble
        self.search_ids = [] #"tvdbid", "rid", "imdbid"
        self.poster = poster
        self.has_nfo = has_nfo #False if we know there isn't one, True if there might be one!
        
        
        

    def __repr__(self):
        return "Title: {}. PubDate: {}. Size: {}. Provider: {}".format(self.title, self.pubdate_utc, self.size, self.provider)
    
    def __eq__(self, other_nzb_search_result):
        return self.title == other_nzb_search_result.title and self.link == other_nzb_search_result.link and self.provider == other_nzb_search_result.provider and self.guid == other_nzb_search_result.guid
    
    def __hash__(self):
        return hash(self.title) ^ hash(self.provider) ^ hash(self.guid)