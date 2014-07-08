import pullFeed, textAnalysis, db
import os
import pickle
from datetime import datetime, timedelta
import sys
import matplotlib.pyplot as plt
import numpy

plt.ion()

def touch_db(target):
    '''Ensure that the database file exists, if not, create the basic
    structure'''

    if not os.path.isfile(target):
        print "%s doesn't exist, creating table" % opts.data_target
        db.create_sqlite(opts.data_target)

def get_dates(start_date, end_date, target):
    '''Work out appropriate date ranges based on user specifications
    or database content. Format appropriately.'''

    touch_db(target)

    conn = db.connect(target)
    curs = conn.cursor()

    if start_date == 'auto':
        curs.execute('select min(date) from articles')
        start_date = datetime.strptime(curs.fetchone()[0], "%Y-%m-%d %H:%M:%S")
    elif start_date == 'last':
        curs.execute('select max(date) from articles')
        start_date = datetime.strptime(curs.fetchone()[0], "%Y-%m-%d %H:%M:%S")
    else:
        start_date = datetime.strptime(start_date, '%Y/%m/%d') 

    if end_date == 'auto':
        curs.execute('select max(date) as date from articles')
        end_date = datetime.strptime(curs.fetchone()[0], "%Y-%m-%d %H:%M:%S")
    elif end_date == 'now':
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%Y/%m/%d') 
    
    return start_date, end_date
        
def update_db(update_start, update_end, field, target):
    '''Pull new data from the arxiv and store it in the local
    database.'''

    touch_db(target)

    if update_end < update_start:
        update_end = update_start
        
    data = pullFeed.oaiSpider(field[0], field[1], update_start, update_end)
    db.insert_dict(target, data)

def read_db(start_date, end_date, target):
    '''Fetch all articles from the local database.'''
    
    touch_db(target)

    conn = db.connect(target)
    curs = conn.cursor()
    
    curs.execute("select * from articles")
    data = curs.fetchall()
    
    return data

def calc_granularity(start_date, end_date, granularity):
    '''Work out the word frequency binning based on user specified
    dates, periods, or number of bins.'''

    now = datetime.now()
    if granularity == "yearly":
        return [datetime(year, 1, 1) for year in xrange(start_date.year, end_date.year + 1)]
    elif granularity == "biyearly":
        output = []
        d = timedelta(365)/2
        for year in xrange(start_date.year, end_date.year + 1):
            for i in xrange(2):
                e = datetime(year, 1, 1) + (i*d)
                output.append(e)
                if (e > now): break
        return output
    elif granularity == "quadyearly":
        output = []
        d = timedelta(365) / 4
        for year in xrange(start_date.year, end_date.year + 1):
            for i in xrange(4):
                e = datetime(year, 1, 1) + (d*i)
                output.append(e)
                if (e > now): break
        return output
    elif granularity == "monthly":
        output = []
        for year in xrange(start_date.year, end_date.year + 1):
            for month in xrange(1,13):
                e = datetime(year, month, 1)
                output.append(e)
                if (e > now): break
        return output
    elif granularity == "weekly":
        output = []
        d = timedelta(365)/52
        for year in xrange(start_date.year, end_date.year + 1):
            for i in xrange(52):
                e = datetime(year, 1, 1) + (i*d)
                output.append(e)
                if (e > now): break
        return output

    if granularity == None:
        granularity = 10

    granularity = int(granularity)
    
    granularity = numpy.linspace(0, (end_date-start_date).total_seconds(), granularity+1)
    granularity = [start_date + timedelta(0, i) for i in granularity]

    return granularity

if __name__ == "__main__":
    from optparse import OptionParser
    p = OptionParser()
    
    p.add_option('-u', '--update', dest='update', action='store_true', default=False
                 , help='Check arxiv for new articles.'
                 )
    p.add_option('--update_start', dest='update_start', default='last'
                 , help='The first date to check for updates, if'
                 ' "last" is specified, this will be the last date for'
                 ' which an article exists in the local'
                 'db. Otherwise, expected format is "yyyy/mm/dd"'
                 )

    p.add_option('--update_end', dest='update_end', default='now'
                 , help='The first date to check for updates, if'
                 ' "now" is specified, this will be today. Otherwise,'
                 ' expected format is "yyyy/mm/dd"'
                 )

    p.add_option('-d', '--data', dest='data_target', default='data.sql'
                 , help='The location of the sql file containing the'
                 ' arxiv data'
                 )

    p.add_option('-f', '--field', dest='field', default='hep-ex,physics'
                 , help='The arxiv field to search in, comma separated'
                 ' (eg. hep-ex,physics)'
                 )

    p.add_option('-s', '--start', dest='start', default='auto'
                 , help='The first date to use when analyzing the'
                 ' data. If "auto" is used, this will be the date of'
                 ' the first available article. Otherwise, expected'
                 ' format is "yyyy/mm/dd"'
                 )

    p.add_option('-e', '--end', dest='end', default='auto'
                 , help='The last date to use when analyzing the'
                 ' data. If "auto" is used, this will be the date of'
                 ' the first available article. Otherwise, expected'
                 ' format is "yyyy/mm/dd"'
                 )

    p.add_option('-g', '--granularity', dest='granularity', default='month'
                 , help='The time granularity for frequency'
                 ' analysis. Can specify the length as "monthly",'
                 ' "weekly", "yearly", "byyearly", "quadyearly" or'
                 ' the number of bins as an integer.'
                 ' (WARNING: the auto-computed granularities'
                 ' are approximate)'
                 )

    p.add_option('-p', '--pickle', dest='pickle_write', default=None
                 , help='The file to which the word frequencies will'
                 ' be written in pickle format.'
                 )

    p.add_option('-j', '--json', dest='json_write', default=None
                 , help='The file to which the word frequencies will'
                 ' be written in JSON format.'
                 )

    p.add_option('-r', '--read', dest='pickle_read', default=None
                 , help='Forget about the article DB and read the word'
                 ' frequencies from a pickle files.'
                 )

    p.add_option('-t', '--threshold', dest='threshold', default=50
                 , help='Minimum number of occurences for a word to be'
                 ' considered in the rankings.'
                 )

    p.add_option('--unique', dest='unique', default=False, action='store_true'
                 , help='Only count words once per article'
                 )

    p.add_option('--droste', dest='droste', default=False, action='store_true'
                 , help='Only count words which don\'t appear in the author list'
                 )
                 
                 

    (opts, args) = p.parse_args()

    print opts.field

    if opts.update:
        update_start, update_end = get_dates(opts.update_start, opts.update_end, opts.data_target)

        update_db(update_start, update_end, opts.field.split(","), opts.data_target)
        

    if opts.pickle_read == None:

        start_date, end_date = get_dates(opts.start, opts.end, opts.data_target)

        data = read_db(start_date, end_date, opts.data_target)

        print "Calculate Word Frequency"
        word_history = textAnalysis.wordHistory(data, start_date, end_date, opts)
        submission_history = textAnalysis.submissionHistory(data, start_date, end_date)
    else:
        submission_history, word_history = pickle.load(open(opts.pickle_read))

    if opts.pickle_write != None:
        print "Exporting pickle format"
        pickle.Pickler(open(opts.pickle_write, 'w')).dump((submission_history, word_history))
    if opts.json_write != None:
        print "Exporting JSON format"
        import json
        output = []
        for key, word in word_history.iteritems():
            output.append([key, [i.isoformat() for i in word.occurences]])
        open(opts.json_write, "w").write(json.dumps(output))


    start_date = submission_history[0]
    end_date   = min(submission_history[-1], datetime.now())
    granularity = calc_granularity(start_date, end_date, opts.granularity)

    print "Start       = %s" % start_date
    print "End         = %s" % end_date
    print "Granularity = %s" % opts.granularity

    history = textAnalysis.histogramHistory(submission_history, granularity, start_date, end_date)
    edges = textAnalysis.edges(submission_history, granularity, start_date, end_date)
    print "Number of edges = %d" % len(edges)
 
    #-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    def show_hist():
        plt.figure(num=None, figsize=(19.97,6.1))
        plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)
        plt.plot(edges, history, label = 'submission history')
        plt.legend(loc='upper left')

    # show_hist()
    #-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    def rank_words(method, words = word_history):
        if method == "n":
            rankedWords = sorted(
                [(w.word, len(w.occurences)) for w in words.itervalues()]
                , key = lambda x: x[1]
                )
        elif method == "rms":
            rankedWords = sorted(
                [(w.word, w.rms(granularity, start_date, end_date, history)) for w in words.itervalues()]
                , key = lambda x: x[1]
                )            
        elif method == "freq":
            rankedWords = sorted(
                [(w.word, w.frequency(granularity, start_date, end_date, history, True)[-2]) for w in words.itervalues() if len(words[w.word].occurences) > opts.threshold]
                , key = lambda x: abs(x[1])
                )
        elif method == "max":
            rankedWords = sorted(
                [(w.word, max(abs(w.frequency(granularity, start_date, end_date, history, True)))) for w in words.itervalues() if len(words[w.word].occurences) > opts.threshold]
                , key = lambda x: abs(x[1])
                )
        return rankedWords

    def dump_words(words, n = 20):
        plt.figure(num=None, figsize=(19.97,6.1))
        plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)
        for i in range(-n, 0):
            print words[i]
            p = word_history[words[i]].graph(granularity, start_date, end_date, history, True)
        plt.legend(loc='upper left', ncol=4)        

    def new_words(cutoff = datetime.now() - timedelta(30), min_counts = -1, max_counts = -1):
        return [w.word for w in word_history.itervalues() if w.occurences[-1] > cutoff and len(w.occurences) >= min_counts and (max_counts < 0 or len(w.occurences) < max_counts)]

    #rankedWords = rank_words("n")
    #dump_words(rankedWords, 20)
    tmp_new_words = new_words(min_counts = 2, max_counts = 10, cutoff = datetime.now() - timedelta(15))
    #dump_words(tmp_new_words, 10)
    print "There are %d new words" % len(tmp_new_words)

    #-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    def show_expts():
      plt.figure(num=None, figsize=(19.97,6.1))
      plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)
      
      if (opts.granularity == "weekly"):
          time_unit = "Week"
      elif (opts.granularity == "monthly"):
          time_unit = "Month"
      elif (opts.granularity == "quadyearly"):
          time_unit = "Three Months"
      elif (opts.granularity == "biyearly"):
          time_unit = "Six Months"
      elif (opts.granularity == "yearly"):
          time_unit = "Year"
      else:
          time_unit = "Bin"
  
      experiments = sorted(['aleph', 'atlas', 'babar', 'brahms', 'cms', 'd0', 'h1', 'l3', 'opal', 
                            'phobos', 'star', 'zeus', 'alice', 'auger', 'belle', 'cdf', 'compass',
                            'delphi', 'hermes', 'lhcb', 'phenix', 'sdss', 'wmap'])
      
      markers = ['-o', '-^', '-D', '-*', '-+']
      for i, expt in enumerate(experiments):
          try:
              word_history[expt].graph(granularity, start_date, end_date, marker=markers[i%len(markers)])
          except KeyError:
              pass
  
      plt.legend(loc='upper left', ncol=4)
      plt.ylabel("Word Counts / %s" % time_unit)
  
      plt.figure(num=None, figsize=(19.97,6.1))
      plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)
  
      experiments = sorted(['atlas', 'cms', 'babar', 'cdf', 'lhcb', 'd0', 'belle'])
      for i, expt in enumerate(experiments):
          word_history[expt].graph(granularity, start_date, end_date)
  
      plt.legend(loc='upper left', ncol=2)
      plt.ylabel("Word Counts / %s" % time_unit)

    #show_expts()
    #-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    def show_neutrinos():
        plt.figure(num="RMS", figsize=(19.97, 6.1))
        word_history['neutrino'].graph(granularity, start_date, end_date, history, True)
        plt.figure(num="Normalized", figsize=(19.97, 6.1))
        word_history['neutrino'].graph(granularity, start_date, end_date, history)

    #-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    
    print "Quick Demo: "
    print "show_hist()"
    print "dump_words(tmp_new_words, 10)"
    print "show_expts()"
    print "show_neutrinos()"
