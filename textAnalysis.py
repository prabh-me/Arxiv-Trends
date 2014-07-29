### Dump useless words: the, we, a, etc...

from blacklist import isBlacklisted, isNotBlacklisted
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import numpy 
import re

### Need to define a graph class here, list of nodes (words), list of edges (pairs of words)

expressions = None
word_pairs  = None

def frequency(data, granularity = 10, start_date = None, end_date = None, norm = None, sigma = False):
    '''Bins a list of dates'''

    
    if type(granularity) == type([]) or type(granularity) == type(numpy.array([])):
        data2 = [(o - start_date).total_seconds() for o in data]
        gran2 = [(o - start_date).total_seconds() for o in granularity]
        data = numpy.array(data)
        output, edges = numpy.histogram(data2, gran2)

    else:
        data = sorted(data)
        if start_date == None:
            start_date = data[0]
        
        if end_date == None:
            end_date = data[-1]
        
        delta = (end_date - start_date + timedelta(1)).total_seconds() / float(granularity)
        if delta == 0:
            delta = 1

        #Old style of histograming
        #output = [0]*granularity
        output = numpy.zeros(granularity)
        for o in data:
            if o > end_date: continue
            if o < start_date: continue
            
            
            output[int((o - start_date).total_seconds() / delta)] += 1

    if type(norm) == type([]):
        norm = numpy.array(norm)

    if str(type(norm)) == "<type 'numpy.ndarray'>":
        if len(norm) != len(output):
            raise ValueError("norm must be the granularity length")
        #output = [float(output[i]) / norm[i] for i in range(len(output))]
        #print norm
        #output = output / norm
        output = numpy.array([float(output[i]) / norm[i] if norm[i] != 0 else 0 for i in xrange(len(output))])

    elif norm != None:
        if norm == 0:
            norm = numpy.mean(output)
        output = output / norm

    mean = sum(output) / len(output)
    rms  = numpy.sqrt(numpy.var(output))
    if sigma:
        output = (output - mean) / rms
        

    return output

def edges(data, granularity = 10, start_date = None, end_date = None):
    if type(granularity) == type([]) or type(granularity) == type(numpy.array([])):
        return [granularity[i] + (granularity[i+1] - granularity[i])/2 for i in xrange(len(granularity)-1)]

    data = sorted(data)
    if start_date == None:
        start_date = data[0]
        
    if end_date == None:
        end_date = data[-1]

    delta = (end_date - start_date + timedelta(1)) / (granularity)

    #return [int((start_date + (delta * (i))).strftime("%s")) for i in range(granularity)]
    output = numpy.array([start_date + (delta * i) for i in range(granularity)])
    return output

class WordHistory:
    def __init__(self, word):
        self.word = word
        self.occurences = []

    def add(self, date):
        self.occurences.append(date)

    def frequency(self, granularity = 10, start_date = None, end_date = None, norm = None, sigma = True):
        return frequency(self.occurences, granularity, start_date, end_date, norm, sigma)

    def edges(self, granularity = 10, start_date = None, end_date = None):
        return edges(self.occurences, granularity, start_date = None, end_date = None)

    def rms(self, granularity = 10, start_date = None, end_date = None, norm = None):
        f = self.frequency(granularity, start_date, end_date, norm)
        return numpy.sqrt(numpy.var(f))

    def first(self):
        self.occurences = sorted(self.occurences)
        return self.occurences[0]

    def last(self):
        self.occurences = sorted(self.occurences)
        return self.occurences[-1]

    def graph(self, granularity = 10, start_date = None, end_date = None, norm = None, sigma = False, marker = None):
        self.occurences = sorted(self.occurences)
        y = self.frequency(granularity, start_date, end_date, norm, sigma)
        x = self.edges(granularity, start_date, end_date)

        #print self.word
        if sigma:
            print "3 Sigma deviations: ", 
            print [x[i] for i, val in enumerate(y) if abs(val) > 3]

        if marker == None:
            plt.plot(x, y, label="word: %s" % self.word, linewidth=2.0)
        else:
            plt.plot(x, y, marker, label="word: %s" % self.word, linewidth=2.0)

    def hist(self, granularity = 10, start_date = None, end_date = None, norm = None, sigma = False):
        self.occurences = sorted(self.occurences)
        if start_date == None:
            start_date = self.occurences[0]
        if end_date == None:
            end_date = self.occurences[-1]

        print self.word
        if sigma:
            print [x[i] for i, val in enumerate(y) if abs(val) > 3]

            
        plt.subplot(211)
        # n, bins, patches = plt.hist([time.mktime(o.timetuple()) for o in self.occurences if o <= end_date and o >= start_date]
        #                             , bins = granularity
        #                             , label = "word counts: %s" % self.word
        #                             )
        n, bins, patches = plt.hist([o for o in self.occurences if o <= end_date and o >= start_date]
                                    , bins = granularity
                                    , label = "word counts: %s" % self.word
                                    )
        print n, bins
        print len(n), len(bins)

        if type(norm) == type([]) and len(norm) > 0:
            print "Draw norm"
            #norm_n, bins, patches = plt.hist([time.mktime(o.timetuple()) for o in norm], bins = granularity, range=(bins[0], bins[-1]))
            #norm_n, bins = numpy.histogram([time.mktime(o.timetuple()) for o in norm], bins = granularity, range=(bins[0], bins[-1]))
            norm_n, bins = numpy.histogram(norm, bins = granularity, range=(bins[0], bins[-1]))
            plt.subplot(212)
            print len(norm_n), len(bins)
            plt.bar([(bins[i+1] + bins[i])/2. for i in xrange(len(bins)-1)]
                    , numpy.array(n, dtype=float) / norm_n
                    , label="word deviations: %s" % self.word
                    , width = bins[1] - bins[0]
                    )
            

def cleanText(text):
    ''' Clean up text formatting, merge/modify words'''

    global expressions
    global word_pairs

    if expressions == None:
        print "MAKE EXPRESSIONS"
        expressions = {
            "remove html tags" : [re.compile(r'<.*?>'), ''],
            "remove tildes" : [re.compile(r'~'), ' '],
            "remove newline characters" : [re.compile(r'\n'), ' '],
            "remove extra whitespace"   : [re.compile(r'\s+'), ' '],
            "remove some punctuation1"  : [re.compile(r'(\.|,|\?|;|!|:|"|\') '), ' '],
            "remove some punctuation2"  : [re.compile(r' (\.|,|\?|;|!|:|"|\')'), ' '],
            "consolidate d0 variants1"  : [re.compile(r' d[^a-zA-Z]*\\\\o[^a-zA-Z]* '), ' d0 '],
            "consolidate d0 variants2"  : [re.compile(r' [^a-zA-Z]*dzero[^a-zA-Z]* '), ' d0 '],
            "remove parenthese1"        : [re.compile(r'\(([a-zA-Z]*)\)'), '\\1'],
            "remove parenthese2"        : [re.compile(r'\(([a-zA-Z]*) '), '\\1 '],
            "remove parenthese3"        : [re.compile(r' ([a-zA-Z]*)\)'), ' \\1'],
            "remove quotes"             : [re.compile(r'"'), ''],
            "remove ownership"          : [re.compile(r'(\w*)\'s'), '\\1'],
            # "remove some punctuation" : [re.compile(r'[a-zA-Z]\. '), ' '],
            }

    if word_pairs == None:
        print "MAKE WORD_PAIRS"

        word_pairs = []
        pairings = [("monte", "carlo"), ("cross", "section"),
                      ("b", "quark"), ("c", "quark"), ("t", "quark"), 
                      ("b", "jet"), ("standard", "model"),
                      ]
        for (a,b) in pairings:
            word_pairs.append( (re.compile(r'(%s) (%s)' % (a,b)), '%s-%s' % (a,b)) )
            word_pairs.append( (re.compile(r'(%s) (%ss)' % (a,b)), '%s-%s' % (a,b)) )
            

    text = text.lower()

    for (title,func) in expressions.items():
        text = func[0].sub(func[1], text)
        
    ## Some of these are sensitive to others, run it twice
    # for (title,func) in expressions.items():
    #     text = func[0].sub(func[1], text)

    for func in word_pairs:
        text = func[0].sub(func[1], text)
    
    return text

def wordHistory(data, start_date = None, end_date = None, opts = None):
    data = sorted(data, key = lambda x: x['date'])
    
    if start_date == None:
        start_date = data[0]['date']
        
    if end_date == None:
        end_date = data[-1]['date']

    word_freq = {}
    for entry in data:
        if entry['date'] >= end_date: continue
        if entry['date'] < start_date: continue

        text = ""
        for key in ('title', 'abstract'):
            text += " " + cleanText(entry[key].lower())

        words = text.split(" ")
        if opts and opts.unique:
            words = set(words)
        #words = filter(isNotBlacklisted, words)
        if opts and opts.droste:
            authors = entry['authors'].lower().replace(" ", ";",).replace(",", ";").split(';')

        for word in words:
            if isBlacklisted(word): continue

            if opts and opts.droste:
                if word in authors:
                    continue

            if not word in ['atlas', 'cms']:
                if word + "s" in word_freq: word += "s"
                elif word[-1] == "s" and word[:-1] in word_freq: word = word[:-1]

            if word not in word_freq: word_freq[word] = WordHistory(word)

            word_freq[word].add(entry['date'])

    return word_freq
        

def wordByArticle(data, target):
    target = target.lower()
    output = {}
    for entry in data:
        url = entry['url']
        output[url] = len(
            [1 for w in entry['title'].split(" ") + entry['abstract'].split(" ")
             if w.lower() == target]
            )
    
    return output

def submissionHistory(data, start_date = None, end_date = None):
    data = sorted(data, key = lambda x: x['date'])
    
    if start_date == None:
        start_date = data[0]['date']
        
    if end_date == None:
        end_date = data[-1]['date']

    history = sorted([entry['date'] for entry in data if entry['date'] < end_date and entry['date'] >= start_date])

    return history

def histogramHistory(history, granularity = 10, start_date = None, end_date = None):
    if type(granularity) == type([]) or type(granularity) == type(numpy.array([])):
        data2 = [(o - start_date).total_seconds() for o in history]
        gran2 = [(o - start_date).total_seconds() for o in granularity]
        #data = numpy.array(data)
        #print "EAS: granularity is a list: ", type(granularity), granularity
        #print "Compare to", data[0:4]
        #print type(granularity[0]) , "vs", type(data[0])
        #output, edges = numpy.histogram([o - start_date for o in data], granularity)
        #output, edges = numpy.histogram(data, granularity)
        output, edges = numpy.histogram(data2, gran2)
        # print len(output), len(edges)

    else:
        if start_date == None:
            start_date = history[0]
        
        if end_date == None:
            end_date = history[-1]
    
        delta = (end_date - start_date + timedelta(1)).total_seconds() / (granularity)
                
        output = numpy.zeros(granularity)
        
        for o in history:
            if o > end_date:
                continue
            if o < start_date:
                continue
            
            output[int((o - start_date).total_seconds() / delta)] += 1
            
    return output

def dumpWords(rankedWords):
    output = ""
    for word, num in rankedWords:
        output += ("%s "% word) * num

    return output

def showDiffPlot(word, freq, granularity = 200):
    plt.figure()
    plt.subplot(111)
    freq[word].graph(granularity / 10, norm = submissionHistory(data, granularity/10), t = True)
    freq[word].graph(granularity, norm = submissionHistory(data, granularity), t = True)
    plt.title(word)

if __name__ == "__main__":
    # import pickle
    # import sys
    
    # freq = pickle.Unpickler(open(sys.argv[1], 'r')).load()
    # data = pickle.Unpickler(open(sys.argv[2], 'r')).load()

    # #rankedWords = sorted([(w.word, len(w.occurences)) for w in freq.values()], key = lambda x: x[1])
    # #rankedWords = sorted([(w.word, rms(w.occurences, 220)) for w in freq.values()], key = lambda x: x[1])
    # history = submissionHistory(data, 220)

    # rankedWords = []
    # for w in freq.values():
    #     f = frequency(w.occurences, 220)
    #     f = [float(f[i]) / history[i] for i in range(len(f))]
    #     rankedWords.append( (w.word, rms(f)) )

    # print rankedWords[-50:]
    
    # showDiffPlot('decays')
    # showDiffPlot('neutrino')
    # showDiffPlot('cross')

#    for w in rankedWords[-20:]:
#        if isBlacklisted(w[0]): continue
#        print w
#        showDiffPlot(w[0])

#    plt.show()

    text = 'The $e^+ e^-\\to K^+ K^- \\pi^+\\pi^-$, $K^+ K^- \\pi^0\\pi^0$ and $K^+ K^- K^+ K^-$ Cross Sections Measured with Initial-State Radiation and this" and "that'
    print text
    print cleanText(text)
