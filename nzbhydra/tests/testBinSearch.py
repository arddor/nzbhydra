import unittest
from freezegun import freeze_time

from furl import furl

from nzbhydra.database import Provider
from nzbhydra.searchmodules.binsearch import Binsearch
from nzbhydra.tests.db_prepare import set_and_drop


class MyTestCase(unittest.TestCase):
    def setUp(self):
        set_and_drop()
        self.binsearch = Provider(module="binsearch", name="Binsearch", query_url="http://127.0.0.1:5001/binsearch", base_url="http://127.0.0.1:5001/binsearch", settings={}, search_types=["general"], search_ids=[])
        self.binsearch.save()

    def testUrlGeneration(self):
        w = Binsearch(self.binsearch)
        urls = w.get_showsearch_urls(generated_query="a showtitle", season=1, episode=2)
        self.assertEqual(2, len(urls))
        self.assertEqual('a showtitle s01e02', furl(urls[0]).args["q"])
        self.assertEqual('a showtitle 1x02', furl(urls[1]).args["q"])

        urls = w.get_showsearch_urls(generated_query="a showtitle", season=1)
        self.assertEqual(2, len(urls))
        self.assertEqual('a showtitle s01', furl(urls[0]).args["q"])
        self.assertEqual('a showtitle "season 1"', furl(urls[1]).args["q"])

    @freeze_time("2015-09-30 14:00:00", tz_offset=-4)
    def testProcess_results(self):
        w = Binsearch(self.binsearch)
        with open("mock/binsearch--q-avengers.html", encoding="latin-1") as f:
            body = f.read()
            entries = w.process_query_result(body, "aquery")["entries"]
            self.assertEqual('MARVELS.AVENGERS.AGE.OF.ULTRON. 3D.TOPBOT.TrueFrench.1080p.X264.AC3.5.1-JKF.mkv', entries[0].title)
            self.assertEqual("https://www.binsearch.info/fcgi/nzb.fcgi?q=176073735", entries[0].link)
            self.assertEqual(13110387671, entries[0].size)
            self.assertEqual("176073735", entries[0].guid)
            self.assertEqual(1440720000, entries[0].epoch)
            self.assertEqual("2015-08-28T00:00:00+00:00", entries[0].pubdate_utc)
            self.assertEqual(33, entries[0].age_days)
            self.assertFalse(entries[0].age_precise)
            self.assertEqual("Ramer@marmer.com <Clown_nez>", entries[0].poster)