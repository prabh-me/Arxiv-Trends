#import urllib
import feedparser
import time
from datetime import datetime
import re

### Things we care about from an entry
### Title, Abstract, Date, Subject, URL

    # p = re.compile(r'<.*?>')
    # return p.sub('', data)

clean_expressions = None

def cleanText(text):
    ''' Clean up text formatting, merge/modify words'''
    
    if clean_expressions == None:
        clean_expresions = {"remove html tags" : [re.compile(r'<.*?>'), ''],
                            "remove newline characters" : [re.compile(r'\n'), ' '],
                            "remove extra whitespace" : [re.compile(r'\s+'), ' '],
                            "remove some punctuation" : [re.compile(r'(\S)(\.|,) '), '\\1 '],
                            }

    for (title,func) in clean_expresions.items():
        text = func[0].sub(func[1], text)

    word_pairs = [("monte", "carlo"), ("cross", "section"),
                 ("b", "quark"), ("c", "quark"), ("t", "quark"), 
                  ("b", "jet"), ("standard", "model"),
                  ]
    for (a,b) in word_pairs:
        text = re.compile(r'(%s) (%s)' %(a,b)).sub('-', text)
        text = re.compile(r'(%s) (%ss)' %(a,b)).sub('-', text)
    
    return text

def convertDate(text):
    '''Convert a text representation of the date into a datetime object'''

    return datetime(*[int(i) for i in text.replace(".","/").replace("-","/").split("/")])

def querySpider(subject = "hep-ph", start = 0, nresults = 10000):
    '''Pull articles using a query via the arxiv API'''
    
    base_url="http://export.arxiv.org/api/query?search_query="
    output = []

    opts = "cat:%s&&start=%i&max_results=%i" % (subject, start, nresults)

    feed = feedparser.parse(base_url + opts)

    for article in feed['entries']:
        output.append({"title"    : cleanText(article["title"]),
                 "abstract" : cleanText(article["summary"]),
                 "date"     : convertDate(article.updated_parsed),
                 "subject"  : subject,
                 "url"      : article["links"][0]["href"],
             })

    return output    


def rssSpider(subject="hep-ph"):
    '''Pull articles using the arxiv RSS feeds'''

    base_url="http://export.arxiv.org/rss/"
    output = []
    
    feed = feedparser.parse(base_url + subject)
    date = feed.feed.updated_parsed
    
    for article in feed['entries']:
        output.append({"title"    : cleanText(article["title"]),
                 "abstract" : cleanText(article["summary"]),
                 "date"     : convertDate(date),
                 "subject"  : subject,
                 "url"      : article["links"][0]["href"],
             })

    return output

def oaiSpider(subject="hep-ex", section="physics", start=None, end=None, sleep_time = 0):
    '''
    Pull articles using the Open Archives Initiative protocol
    
    subject    - String defining the subset of the main section
    section    - String defining the main section (typically physics or nothing)
    start      - A datetime.datetime object restricting the starting date of returned articles
    end        - A datetime.datetime object restricting the ending date of the returned articles
    sleep_time - A number specifying how many ms to wait between the record queries
    
    Examples

       oaiSpider("hep-ex", "physics")
       ==> returns all HEP experiment articles
       
       oaiSpider("cs", "", datetime(2011,06,24))
       ==> returns all computer science articles submitted after June 24th, 2011
       
       oaiSpider("hep-ph", "physics", None, datetime(2011,06, 24))
       ==> returns all HEP phenomenology articles submitted before June 24th, 2011

    Returns a list of dictionaries containing the article metadata
    '''

    from oaipmh.client import Client
    from oaipmh.metadata import MetadataRegistry, oai_dc_reader

    base_url = "http://export.arxiv.org/oai2"
    output = []

    registry = MetadataRegistry()
    registry.registerReader('oai_dc', oai_dc_reader)
    client = Client(base_url, registry)
    client.updateGranularity()

    if section == None:
        section = ""
    if len(section) > 0 and section[-1] != ":":
        section += ":"

    # sets = client.listSets()
    # for entry in sets:
    #     print entry
    
    ### OAIPMH module sucks donkey balls
    # Causes some error when I use the from_ or until keys
    records = client.listRecords(metadataPrefix='oai_dc'
                                 , set='%s%s' % (section, subject)
                                 , from_=start
                                 #, from_=datestamp
                                 , until=end
                                 )
    
    counter = 0
    
    for (header, metadata, aux) in records:
        
        print counter

        # for key in  metadata._map.keys():
        #     print key, metadata[key]

        output.append({"title"    : cleanText(metadata["title"][0]),
                       "abstract" : cleanText(metadata["description"][0]),
                       "date"     : convertDate(max(metadata["date"])),
                       "subject"  : subject,
                       "url"      : metadata["identifier"][0],
                       "authors"  : "; ".join( metadata['creator']),
                       })

        print output[-1]
        counter += 1
        
        # break
        # if counter > 15:
        #     break
        time.sleep(sleep_time)

    return output
    
def main():
    #print querySpiderr()
    r =  oaiSpider()
    return r

if __name__ == "__main__":
    r = main()
